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

    def __init__(self, max_size: int = 100) -> None:
        self._values: deque = deque(maxlen=max_size)

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
        self.batch_throughput = MetricWindow()
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

class FlowTuner:
    """
    Observes pipeline metrics and adjusts tuning parameters to
    optimize throughput while maintaining quality constraints.
    """

    def __init__(self) -> None:
        self.metrics = PipelineMetrics()
        self.params = TuningParams()
        self._last_tune_at: float = 0.0
        self._tune_interval_sec: float = 60.0
        self._tuning_history: List[Dict[str, Any]] = []

    def tune(self) -> Dict[str, Any]:
        """
        Run a tuning cycle. Analyzes recent metrics and adjusts
        parameters to improve throughput.
        """
        now = time.time()
        if now - self._last_tune_at < self._tune_interval_sec:
            return {"action": "skipped", "reason": "too_soon"}

        self._last_tune_at = now
        adjustments: List[str] = []

        # Batch size tuning
        throughput_trend = self.metrics.batch_throughput.trend()
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
            "params": self.params.as_dict(),
            "recent_tuning": self._tuning_history[-5:] if self._tuning_history else [],
        }


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------

flow_tuner = FlowTuner()
