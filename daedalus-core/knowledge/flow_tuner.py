# knowledge/flow_tuner.py

"""
Flow Tuner

Self-tuning system for data storage efficiency and processing speed.
Monitors pipeline performance metrics and adjusts internal parameters
to optimize throughput without compromising quality.

Tracks:
- Ingestion throughput (items/sec)
- Verification latency (ms per item)
- Graph update latency
- Self-model recomputation time
- Knowledge retrieval latency
- Storage I/O overhead

Tunes:
- Batch sizes for ingestion and evolution
- Verification parallelism hints
- Graph rebuild vs incremental threshold
- Self-model update frequency
- Retrieval cache parameters
- Storage compaction scheduling

Integration:
- Consumed by adaptive_pacer for batch sizing
- Consumed by meta_reasoner for cycle frequency
- Consumed by batch_ingestion for I/O scheduling
- Exposes a dashboard-ready summary for the cockpit
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from collections import deque


# ------------------------------------------------------------
# METRIC WINDOWS
# ------------------------------------------------------------

class MetricWindow:
    """Fixed-size sliding window for numeric metrics."""

    def __init__(self, max_size: int = 100, higher_is_better: bool = False) -> None:
        self._values: deque = deque(maxlen=max_size)
        self._higher_is_better = higher_is_better

    def record(self, value: float) -> None:
        self._values.append((time.time(), value))

    def mean(self) -> float:
        if not self._values:
            return 0.0
        return sum(v for _, v in self._values) / len(self._values)

    def p95(self) -> float:
        if not self._values:
            return 0.0
        sorted_vals = sorted(v for _, v in self._values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def rate(self) -> float:
        """Items per second over the window."""
        if len(self._values) < 2:
            return 0.0
        first_t = self._values[0][0]
        last_t = self._values[-1][0]
        elapsed = last_t - first_t
        if elapsed <= 0:
            return 0.0
        return len(self._values) / elapsed

    def count(self) -> int:
        return len(self._values)

    def last(self) -> float:
        if not self._values:
            return 0.0
        return self._values[-1][1]

    def trend(self) -> str:
        """Recent trend: improving, degrading, or stable."""
        if len(self._values) < 10:
            return "insufficient_data"
        recent = [v for _, v in list(self._values)[-10:]]
        older = [v for _, v in list(self._values)[-20:-10]]
        if not older:
            return "insufficient_data"
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        delta = recent_avg - older_avg
        threshold = max(older_avg * 0.05, 0.001)
        if abs(delta) < threshold:
            return "stable"
        if self._higher_is_better:
            return "improving" if delta > 0 else "degrading"
        return "improving" if delta < 0 else "degrading"


# ------------------------------------------------------------
# PIPELINE METRICS
# ------------------------------------------------------------

class PipelineMetrics:
    """Tracks performance metrics across the knowledge pipeline."""

    def __init__(self) -> None:
        self.ingestion_latency = MetricWindow()
        self.verification_latency = MetricWindow()
        self.graph_update_latency = MetricWindow()
        self.self_model_latency = MetricWindow()
        self.retrieval_latency = MetricWindow()
        self.evolution_latency = MetricWindow()
        self.batch_throughput = MetricWindow(higher_is_better=True)
        self.storage_io_latency = MetricWindow()

    def record_ingestion(self, latency_ms: float) -> None:
        self.ingestion_latency.record(latency_ms)

    def record_verification(self, latency_ms: float) -> None:
        self.verification_latency.record(latency_ms)

    def record_graph_update(self, latency_ms: float) -> None:
        self.graph_update_latency.record(latency_ms)

    def record_self_model(self, latency_ms: float) -> None:
        self.self_model_latency.record(latency_ms)

    def record_retrieval(self, latency_ms: float) -> None:
        self.retrieval_latency.record(latency_ms)

    def record_evolution(self, latency_ms: float) -> None:
        self.evolution_latency.record(latency_ms)

    def record_batch(self, items: int, total_ms: float) -> None:
        if items > 0 and total_ms > 0:
            self.batch_throughput.record(items / (total_ms / 1000.0))

    def record_storage_io(self, latency_ms: float) -> None:
        self.storage_io_latency.record(latency_ms)

    def summary(self) -> Dict[str, Any]:
        return {
            "ingestion": _window_summary(self.ingestion_latency),
            "verification": _window_summary(self.verification_latency),
            "graph_update": _window_summary(self.graph_update_latency),
            "self_model": _window_summary(self.self_model_latency),
            "retrieval": _window_summary(self.retrieval_latency),
            "evolution": _window_summary(self.evolution_latency),
            "batch_throughput": _window_summary(self.batch_throughput),
            "storage_io": _window_summary(self.storage_io_latency),
        }


def _window_summary(w: MetricWindow) -> Dict[str, Any]:
    return {
        "mean": round(w.mean(), 2),
        "p95": round(w.p95(), 2),
        "count": w.count(),
        "trend": w.trend(),
        "last": round(w.last(), 2),
    }


# ------------------------------------------------------------
# TUNING PARAMETERS
# ------------------------------------------------------------

class TuningParams:
    """Adjustable parameters that control pipeline behavior."""

    def __init__(self) -> None:
        self.batch_size: int = 10
        self.verification_parallelism: int = 1
        self.graph_rebuild_threshold: int = 500
        self.self_model_update_interval_sec: float = 30.0
        self.retrieval_cache_size: int = 200
        self.evolution_batch_cap: int = 10
        self.storage_compaction_interval_sec: float = 300.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "verification_parallelism": self.verification_parallelism,
            "graph_rebuild_threshold": self.graph_rebuild_threshold,
            "self_model_update_interval_sec": self.self_model_update_interval_sec,
            "retrieval_cache_size": self.retrieval_cache_size,
            "evolution_batch_cap": self.evolution_batch_cap,
            "storage_compaction_interval_sec": self.storage_compaction_interval_sec,
        }


# ------------------------------------------------------------
# FLOW TUNER
# ------------------------------------------------------------

class QualitySignals:
    """
    Tracks quality-side metrics that the flow tuner uses to make
    bidirectional decisions: decelerate when quality degrades,
    not just when throughput degrades.
    """

    def __init__(self) -> None:
        self.consistency = MetricWindow(max_size=200, higher_is_better=True)
        self.coherence = MetricWindow(max_size=200, higher_is_better=True)
        self.knowledge_quality = MetricWindow(max_size=200, higher_is_better=True)

    def record(self, consistency: float, coherence: float, quality: float) -> None:
        self.consistency.record(consistency)
        self.coherence.record(coherence)
        self.knowledge_quality.record(quality)

    def summary(self) -> Dict[str, Any]:
        return {
            "consistency": _window_summary(self.consistency),
            "coherence": _window_summary(self.coherence),
            "knowledge_quality": _window_summary(self.knowledge_quality),
        }

    def any_degrading(self) -> bool:
        return any(
            w.trend() == "degrading"
            for w in (self.consistency, self.coherence, self.knowledge_quality)
        )

    def worst_trend(self) -> str:
        trends = [
            self.consistency.trend(),
            self.coherence.trend(),
            self.knowledge_quality.trend(),
        ]
        if "degrading" in trends:
            return "degrading"
        if "improving" in trends:
            return "improving"
        return "stable"


class FlowTuner:
    """
    Observes pipeline metrics AND quality signals, then adjusts
    tuning parameters bidirectionally: accelerate when both throughput
    and quality are healthy; decelerate when either degrades.

    Sim-fix C3: Recovery mode with hysteresis. After braking,
    batch size recovers gradually once quality stabilizes for
    N consecutive tune cycles.
    """

    RECOVERY_STABLE_CYCLES = 5  # stable quality cycles before recovery
    RECOVERY_BATCH_INCREMENT = 2  # batch size increase per recovery step
    RECOVERY_MAX_BATCH = 30  # cap during recovery (not full 50)
    RECOVERY_IMMUNITY_CYCLES = 10  # T2: ignore quality brakes for N cycles after recovery starts

    def __init__(self) -> None:
        self.metrics = PipelineMetrics()
        self.quality = QualitySignals()
        self.params = TuningParams()
        self._last_tune_at: float = 0.0
        self._tune_interval_sec: float = 60.0
        self._tuning_history: List[Dict[str, Any]] = []
        self._defensive_mode: bool = False
        self._stable_cycles: int = 0
        self._in_recovery: bool = False
        self._pre_brake_batch_size: int = 10
        self._recovery_immunity_remaining: int = 0  # T2

    def record_quality(self, consistency: float, coherence: float, quality: float) -> None:
        """Called after each meta-cycle or batch to feed quality signals."""
        self.quality.record(consistency, coherence, quality)

    def set_defensive_mode(self, active: bool) -> None:
        """When active, tuner biases toward deceleration and deeper verification."""
        self._defensive_mode = active

    def tune(self) -> Dict[str, Any]:
        """
        Bidirectional tuning cycle: considers both throughput metrics
        and quality signals before making parameter adjustments.
        """
        now = time.time()
        if now - self._last_tune_at < self._tune_interval_sec:
            return {"action": "skipped", "reason": "too_soon"}

        self._last_tune_at = now
        adjustments: List[str] = []

        throughput_trend = self.metrics.batch_throughput.trend()
        quality_trend = self.quality.worst_trend()
        quality_degrading = quality_trend == "degrading"

        # --- Quality-first gating ---
        # T2: During recovery immunity, only brake for true emergencies (defensive_mode),
        # not transient quality fluctuations from increased throughput
        should_brake = quality_degrading or self._defensive_mode
        if self._in_recovery and self._recovery_immunity_remaining > 0:
            self._recovery_immunity_remaining -= 1
            if not self._defensive_mode:
                should_brake = False
                adjustments.append(f"recovery_immunity ({self._recovery_immunity_remaining} remaining)")

        if should_brake:
            if self.params.batch_size > 5:
                self._pre_brake_batch_size = max(self._pre_brake_batch_size, self.params.batch_size)
                self.params.batch_size = max(5, int(self.params.batch_size * 0.6))
                adjustments.append(f"batch_size -> {self.params.batch_size} (quality brake)")

            if self.params.verification_parallelism < 4:
                self.params.verification_parallelism = min(
                    4, self.params.verification_parallelism + 1
                )
                adjustments.append(
                    f"verification_parallelism -> {self.params.verification_parallelism} (quality brake)"
                )

            if self.params.evolution_batch_cap > 3:
                self.params.evolution_batch_cap = max(3, self.params.evolution_batch_cap - 2)
                adjustments.append(
                    f"evolution_batch_cap -> {self.params.evolution_batch_cap} (quality brake)"
                )

            self._stable_cycles = 0
            self._in_recovery = False
            self._recovery_immunity_remaining = 0
        else:
            # C3: Recovery mode with hysteresis
            self._stable_cycles += 1

            if self._stable_cycles >= self.RECOVERY_STABLE_CYCLES:
                target = min(self._pre_brake_batch_size, self.RECOVERY_MAX_BATCH)
                if self.params.batch_size < target:
                    if not self._in_recovery:
                        self._recovery_immunity_remaining = self.RECOVERY_IMMUNITY_CYCLES
                    self._in_recovery = True
                    self.params.batch_size = min(
                        target,
                        self.params.batch_size + self.RECOVERY_BATCH_INCREMENT,
                    )
                    adjustments.append(f"batch_size -> {self.params.batch_size} (recovery, immune={self._recovery_immunity_remaining})")
                elif self._in_recovery:
                    self._in_recovery = False
                    adjustments.append("recovery_complete")
            elif not self._in_recovery:
                # Normal throughput-driven tuning
                if throughput_trend == "improving" and self.params.batch_size < 50:
                    self.params.batch_size = min(50, int(self.params.batch_size * 1.3))
                    adjustments.append(f"batch_size -> {self.params.batch_size}")
                elif throughput_trend == "degrading" and self.params.batch_size > 5:
                    self.params.batch_size = max(5, int(self.params.batch_size * 0.7))
                    adjustments.append(f"batch_size -> {self.params.batch_size}")

        # Verification latency tuning
        ver_p95 = self.metrics.verification_latency.p95()
        if ver_p95 > 500 and self.params.verification_parallelism < 4:
            self.params.verification_parallelism += 1
            adjustments.append(
                f"verification_parallelism -> {self.params.verification_parallelism}"
            )

        # Graph rebuild threshold
        graph_trend = self.metrics.graph_update_latency.trend()
        if graph_trend == "degrading":
            self.params.graph_rebuild_threshold = max(
                100, int(self.params.graph_rebuild_threshold * 0.8)
            )
            adjustments.append(
                f"graph_rebuild_threshold -> {self.params.graph_rebuild_threshold}"
            )

        # Self-model update frequency
        sm_p95 = self.metrics.self_model_latency.p95()
        if sm_p95 > 2000 and self.params.self_model_update_interval_sec < 120:
            self.params.self_model_update_interval_sec = min(
                120, self.params.self_model_update_interval_sec * 1.5
            )
            adjustments.append(
                f"self_model_interval -> {self.params.self_model_update_interval_sec:.0f}s"
            )
        elif sm_p95 < 500 and self.params.self_model_update_interval_sec > 15:
            self.params.self_model_update_interval_sec = max(
                15, self.params.self_model_update_interval_sec * 0.8
            )
            adjustments.append(
                f"self_model_interval -> {self.params.self_model_update_interval_sec:.0f}s"
            )

        # Storage I/O tuning
        io_trend = self.metrics.storage_io_latency.trend()
        if io_trend == "degrading":
            self.params.storage_compaction_interval_sec = max(
                60, self.params.storage_compaction_interval_sec * 0.7
            )
            adjustments.append("storage_compaction more frequent")

        result = {
            "action": "tuned" if adjustments else "no_change",
            "adjustments": adjustments,
            "params": self.params.as_dict(),
            "metrics_summary": self.metrics.summary(),
            "quality_summary": self.quality.summary(),
            "quality_trend": quality_trend,
            "defensive_mode": self._defensive_mode,
            "timestamp": now,
        }

        self._tuning_history.append(result)
        if len(self._tuning_history) > 50:
            self._tuning_history = self._tuning_history[-50:]

        return result

    def get_recommended_batch_size(self) -> int:
        return self.params.batch_size

    def get_recommended_self_model_interval(self) -> float:
        return self.params.self_model_update_interval_sec

    def dashboard(self) -> Dict[str, Any]:
        """Cockpit-ready summary of pipeline health and tuning state."""
        return {
            "metrics": self.metrics.summary(),
            "quality": self.quality.summary(),
            "params": self.params.as_dict(),
            "defensive_mode": self._defensive_mode,
            "recent_tuning": self._tuning_history[-5:] if self._tuning_history else [],
        }


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------

flow_tuner = FlowTuner()
