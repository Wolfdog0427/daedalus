# knowledge/meta_reasoner.py

"""
Meta Reasoner

This module performs meta-cognition:
- reads the self-model
- evaluates subsystem health
- detects when maintenance is needed
- triggers safe, governed actions
- escalates to the user when human approval is required
- coordinates long-term stability

It does NOT modify knowledge directly.
It orchestrates other modules safely.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
from collections import deque

from knowledge.self_model import update_self_model, get_self_model
from knowledge.reasoning_engine import reason_about_claim
from knowledge.curiosity_engine import get_executable_goals

try:
    from knowledge.provider_discovery import (
        run_discovery_cycle,
        provider_registry,
    )
    _DISCOVERY_AVAILABLE = True
except ImportError:
    _DISCOVERY_AVAILABLE = False

try:
    from knowledge.flow_tuner import flow_tuner as _flow_tuner
    _FLOW_TUNER_AVAILABLE = True
except ImportError:
    _FLOW_TUNER_AVAILABLE = False

try:
    from knowledge.adaptive_pacer import get_circuit_breaker, get_long_term_trends
    _PACER_AVAILABLE = True
except ImportError:
    _PACER_AVAILABLE = False

try:
    from knowledge.source_integrity import (
        get_unswept_attack_windows,
        sweep_attack_window,
        record_attack_event,
        run_delayed_poison_audit,
    )
    _INTEGRITY_AVAILABLE = True
except ImportError:
    _INTEGRITY_AVAILABLE = False


# ------------------------------------------------------------
# QUALITY REGRESSION DETECTOR (F2)
# ------------------------------------------------------------

class QualityRegressionDetector:
    """
    Detects significant quality drops (>10 points) across cycles
    and triggers a defensive posture when regression is detected.
    """

    REGRESSION_THRESHOLD = 0.10  # 10-point drop

    def __init__(self, history_size: int = 50) -> None:
        self._history: deque = deque(maxlen=history_size)
        self.defensive_active: bool = False
        self.defensive_activated_at: float = 0.0
        self.defensive_reason: str = ""
        self._regression_count: int = 0

    def record_snapshot(self, sm: Dict[str, Any]) -> None:
        self._history.append({
            "timestamp": time.time(),
            "quality": sm["confidence"]["knowledge_quality"],
            "consistency": sm["confidence"]["consistency"],
            "coherence": sm["confidence"]["graph_coherence"],
        })

    def check_regression(self) -> Dict[str, Any]:
        """
        Compare most recent snapshot against previous snapshots.
        If any metric dropped by more than REGRESSION_THRESHOLD,
        activate defensive posture.
        """
        if len(self._history) < 3:
            return {"regression_detected": False}

        current = self._history[-1]
        previous = self._history[-3]  # compare against 3 cycles ago

        regressions = []
        for metric in ("quality", "consistency", "coherence"):
            drop = previous[metric] - current[metric]
            if drop >= self.REGRESSION_THRESHOLD:
                regressions.append({
                    "metric": metric,
                    "previous": round(previous[metric], 4),
                    "current": round(current[metric], 4),
                    "drop": round(drop, 4),
                })

        if regressions:
            self.defensive_active = True
            self.defensive_activated_at = time.time()
            self.defensive_reason = f"regression in {', '.join(r['metric'] for r in regressions)}"
            self._regression_count += 1

            if _FLOW_TUNER_AVAILABLE:
                _flow_tuner.set_defensive_mode(True)

            return {
                "regression_detected": True,
                "regressions": regressions,
                "defensive_posture": "activated",
            }

        # Clear defensive mode if quality has recovered
        if self.defensive_active:
            recovered = all(
                current[m] >= previous[m] - 0.02
                for m in ("quality", "consistency", "coherence")
            )
            if recovered:
                self.defensive_active = False
                self.defensive_reason = ""
                if _FLOW_TUNER_AVAILABLE:
                    _flow_tuner.set_defensive_mode(False)

        return {"regression_detected": False}

    def status(self) -> Dict[str, Any]:
        return {
            "defensive_active": self.defensive_active,
            "defensive_reason": self.defensive_reason,
            "regression_count": self._regression_count,
            "history_size": len(self._history),
        }


# ------------------------------------------------------------
# LONG-HORIZON STABILITY TRACKER (F10)
# ------------------------------------------------------------

class StabilityTrendTracker:
    """
    Tracks system stability across many meta-cycles and detects
    slow, chronic degradation that individual cycles miss.

    Sim-fix H3: structural reviews trigger every 10th detection
    (was 100th). Review intensity scales with decline magnitude.
    """

    REVIEW_INTERVAL = 10  # trigger review every N detections

    def __init__(self, window_size: int = 200) -> None:
        self._snapshots: deque = deque(maxlen=window_size)
        self._decline_count: int = 0
        self._review_count: int = 0

    def record(self, sm: Dict[str, Any]) -> None:
        composite = (
            sm["confidence"]["knowledge_quality"] * 0.3
            + sm["confidence"]["consistency"] * 0.4
            + sm["confidence"]["graph_coherence"] * 0.3
        )
        self._snapshots.append({
            "timestamp": time.time(),
            "composite": composite,
            "quality": sm["confidence"]["knowledge_quality"],
            "consistency": sm["confidence"]["consistency"],
            "coherence": sm["confidence"]["graph_coherence"],
        })

    def detect_long_decline(self) -> Dict[str, Any]:
        """
        Compare oldest quarter vs newest quarter. If composite
        dropped by >15%, flag a long-horizon decline. Reviews
        trigger every 10 detections, proportional to magnitude.
        """
        n = len(self._snapshots)
        if n < 20:
            return {"decline_detected": False, "reason": "insufficient_data"}

        quarter = max(5, n // 4)
        old_avg = sum(s["composite"] for s in list(self._snapshots)[:quarter]) / quarter
        new_avg = sum(s["composite"] for s in list(self._snapshots)[-quarter:]) / quarter

        if old_avg <= 0:
            return {"decline_detected": False}

        decline_pct = (old_avg - new_avg) / old_avg

        if decline_pct >= 0.15:
            self._decline_count += 1
            needs_review = (self._decline_count % self.REVIEW_INTERVAL) == 1
            if needs_review:
                self._review_count += 1
            return {
                "decline_detected": True,
                "old_average": round(old_avg, 4),
                "new_average": round(new_avg, 4),
                "decline_pct": round(decline_pct * 100, 1),
                "decline_magnitude": "severe" if decline_pct >= 0.30 else "moderate" if decline_pct >= 0.20 else "mild",
                "needs_review": needs_review,
                "decline_count": self._decline_count,
                "review_count": self._review_count,
                "recommendation": "structural_review" if needs_review else "monitor",
            }
        return {"decline_detected": False, "decline_pct": round(decline_pct * 100, 1)}

    def status(self) -> Dict[str, Any]:
        if not self._snapshots:
            return {"samples": 0}
        return {
            "samples": len(self._snapshots),
            "latest_composite": round(self._snapshots[-1]["composite"], 4),
            "decline_count": self._decline_count,
            "review_count": self._review_count,
        }


# ------------------------------------------------------------
# SEVERITY CONTEXT (F8 + F12)
# ------------------------------------------------------------

class SeverityContext:
    """
    Tracks environmental severity for governance scaling and
    predictive hardening. External callers or the scheduler
    set the severity; the meta-reasoner consults it.
    """

    LEVELS = ("nominal", "elevated", "stressed", "severe", "catastrophic")

    def __init__(self) -> None:
        self.current_level: str = "nominal"
        self.updated_at: float = time.time()
        self._history: deque = deque(maxlen=100)

    def set_level(self, level: str) -> None:
        if level in self.LEVELS:
            self.current_level = level
            self.updated_at = time.time()
            self._history.append({"level": level, "at": self.updated_at})

    def severity_score(self) -> float:
        """0.0 (nominal) to 1.0 (catastrophic)."""
        idx = self.LEVELS.index(self.current_level) if self.current_level in self.LEVELS else 0
        return idx / (len(self.LEVELS) - 1)

    def is_stressed(self) -> bool:
        return self.current_level in ("stressed", "severe", "catastrophic")

    def status(self) -> Dict[str, Any]:
        return {
            "level": self.current_level,
            "score": self.severity_score(),
            "updated_at": self.updated_at,
        }


# ------------------------------------------------------------
# DEFENSIVE COORDINATION LAYER (Sim-fix C2 + M3)
# ------------------------------------------------------------

class DefensiveCoordinator:
    """
    Single arbitrator for all defensive systems. Prevents stacking
    of circuit breaker, regression detector, quality brakes, trend
    deceleration, and severity governance simultaneously.

    Each cycle, the coordinator collects signals from all defensive
    systems and selects the MINIMUM SUFFICIENT response:
    - Level 0 (nominal): no defensive action
    - Level 1 (cautious): one system engaged (e.g. trend deceleration)
    - Level 2 (defensive): two systems engaged (e.g. regression + brakes)
    - Level 3 (emergency): circuit breaker or catastrophic severity

    Only level 3 permits all defenses to stack. At levels 1-2, the
    coordinator suppresses redundant activations.
    """

    def __init__(self) -> None:
        self.current_level: int = 0
        self.active_defenses: list = []
        self.suppressed_defenses: list = []
        self._history_size: int = 0

    def evaluate(
        self,
        circuit_breaker_open: bool,
        regression_active: bool,
        quality_degrading: bool,
        trend_declining: bool,
        severity_stressed: bool,
    ) -> Dict[str, Any]:
        """
        Evaluate all defensive signals and select the minimum
        sufficient response. Returns which defenses should be active.
        """
        signals = {
            "circuit_breaker": circuit_breaker_open,
            "regression": regression_active,
            "quality_brake": quality_degrading,
            "trend_decel": trend_declining,
            "severity_gate": severity_stressed,
        }
        active_count = sum(1 for v in signals.values() if v)

        self.active_defenses = []
        self.suppressed_defenses = []

        # Level 3: emergency — allow all
        if circuit_breaker_open or (severity_stressed and active_count >= 3):
            self.current_level = 3
            self.active_defenses = [k for k, v in signals.items() if v]
            return self._result(signals)

        # Level 2: at most 2 defenses active
        # T7: Adaptive priority — severity_gate promoted to top during crisis
        if active_count >= 2:
            self.current_level = 2
            if severity_stressed:
                priority_order = ["severity_gate", "regression", "quality_brake", "trend_decel"]
            else:
                priority_order = ["regression", "quality_brake", "trend_decel", "severity_gate"]
            for defense in priority_order:
                if signals.get(defense) and len(self.active_defenses) < 2:
                    self.active_defenses.append(defense)
                elif signals.get(defense):
                    self.suppressed_defenses.append(defense)
            return self._result(signals)

        # Level 1: single defense
        if active_count == 1:
            self.current_level = 1
            self.active_defenses = [k for k, v in signals.items() if v]
            return self._result(signals)

        # Level 0: nominal
        self.current_level = 0
        return self._result(signals)

    def _result(self, signals: Dict[str, bool]) -> Dict[str, Any]:
        return {
            "level": self.current_level,
            "active": self.active_defenses,
            "suppressed": self.suppressed_defenses,
            "signals": signals,
        }

    def should_suppress_ingestion(self) -> bool:
        return self.current_level >= 3

    def should_suppress_expansion(self) -> bool:
        return self.current_level >= 2

    def should_throttle(self) -> bool:
        return self.current_level >= 1

    def status(self) -> Dict[str, Any]:
        return {
            "level": self.current_level,
            "active_defenses": self.active_defenses,
            "suppressed_defenses": self.suppressed_defenses,
        }


# ------------------------------------------------------------
# GLOBAL INSTANCES
# ------------------------------------------------------------

_regression_detector = QualityRegressionDetector()
_stability_tracker = StabilityTrendTracker()
_severity_context = SeverityContext()
_defensive_coordinator = DefensiveCoordinator()


def get_regression_detector() -> QualityRegressionDetector:
    return _regression_detector


def get_stability_tracker() -> StabilityTrendTracker:
    return _stability_tracker


def get_severity_context() -> SeverityContext:
    return _severity_context


def get_defensive_coordinator() -> DefensiveCoordinator:
    return _defensive_coordinator


# ------------------------------------------------------------
# DECISION RULES
# ------------------------------------------------------------

def _needs_concept_evolution(self_model: Dict[str, Any]) -> bool:
    coherence = self_model["confidence"]["graph_coherence"]
    clusters = self_model["coverage"]["topic_clusters"]
    return coherence < 0.45 or clusters > 50


def _needs_consistency_repair(self_model: Dict[str, Any]) -> bool:
    consistency = self_model["confidence"]["consistency"]
    return consistency < 0.5


def _needs_storage_maintenance(self_model: Dict[str, Any]) -> bool:
    storage = self_model["storage"]
    return storage.get("ratio", 0) > 0.85


def _needs_verification(claim: str) -> bool:
    try:
        from knowledge.integration_layer import do_reasoning
        result = do_reasoning(claim)
        reasoning = result.get("result", result)
        return reasoning.get("status") in ("uncertain", "contradicted", "unknown")
    except Exception:
        return True


def _needs_knowledge_expansion(self_model: Dict[str, Any]) -> bool:
    if _defensive_coordinator.should_suppress_expansion():
        return False
    if _regression_detector.defensive_active:
        return False

    blind_spots = self_model.get("blind_spots", [])
    coverage_gaps = self_model.get("coverage_gaps", [])
    frontier_domains = self_model.get("frontier_domains", [])
    coherence = self_model["confidence"]["graph_coherence"]

    has_blind_spots = len(blind_spots) > 5
    has_coverage_gaps = len(coverage_gaps) > 0
    has_frontiers = len(frontier_domains) > 0
    low_coherence = coherence < 0.5

    return has_blind_spots or has_coverage_gaps or has_frontiers or low_coherence


def _needs_deferred_verification(self_model: Dict[str, Any]) -> bool:
    consistency = self_model["confidence"]["consistency"]
    coherence = self_model["confidence"]["graph_coherence"]
    return consistency > 0.5 and coherence > 0.4


def _needs_provider_discovery(self_model: Dict[str, Any]) -> bool:
    if not _DISCOVERY_AVAILABLE:
        return False
    active = provider_registry.get_active_count()
    if active == 0:
        return True
    has_expansion_need = _needs_knowledge_expansion(self_model)
    return has_expansion_need


def _needs_flow_tuning() -> bool:
    if not _FLOW_TUNER_AVAILABLE:
        return False
    return _flow_tuner.metrics.batch_throughput.count() >= 5


def _needs_goal_execution() -> bool:
    """Check if there are approved goals with pending phases to execute."""
    if _defensive_coordinator.should_suppress_expansion():
        return False
    if _regression_detector.defensive_active:
        return False
    try:
        return len(get_executable_goals()) > 0
    except Exception:
        return False


def _needs_attack_sweep() -> bool:
    """Check if there are unswept attack windows needing retroactive verification."""
    if not _INTEGRITY_AVAILABLE:
        return False
    try:
        return len(get_unswept_attack_windows()) > 0
    except Exception:
        return False


# ------------------------------------------------------------
# META-REASONING ACTIONS
# ------------------------------------------------------------

def run_meta_cycle(claim: str | None = None) -> Dict[str, Any]:
    """
    Enhanced meta-reasoning cycle with:
    - Quality regression detection (F2)
    - Long-horizon stability tracking (F10)
    - Severity-aware gating (F8)
    - Goal execution (F3)
    - Post-attack sweep (F9)
    - Quality signal feedback to flow tuner (F5)
    """
    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "actions": [],
        "claim_verification": None,
        "self_model_before": None,
        "self_model_after": None,
        "regression_check": None,
        "stability_trend": None,
        "severity": _severity_context.status(),
    }

    # --------------------------------------------------------
    # 1. Update self-model (throttled by flow tuner interval)
    # --------------------------------------------------------
    _sm_interval = 30.0
    if _FLOW_TUNER_AVAILABLE:
        _sm_interval = _flow_tuner.get_recommended_self_model_interval()
    last_model = get_self_model()
    last_updated = last_model.get("last_updated", 0)
    if time.time() - last_updated >= _sm_interval:
        before = update_self_model()
    else:
        before = last_model
    report["self_model_before"] = before

    # --------------------------------------------------------
    # 1b. Trust natural decay (H1) — governed
    # --------------------------------------------------------
    try:
        from knowledge.integration_layer import do_trust_decay
        do_trust_decay()
    except (ImportError, Exception):
        pass

    # --------------------------------------------------------
    # 1c-prev. Feed trackers (F2, F5, F10)
    # --------------------------------------------------------
    _regression_detector.record_snapshot(before)
    _stability_tracker.record(before)

    if _FLOW_TUNER_AVAILABLE:
        _flow_tuner.record_quality(
            consistency=before["confidence"]["consistency"],
            coherence=before["confidence"]["graph_coherence"],
            quality=before["confidence"]["knowledge_quality"],
        )

    # --------------------------------------------------------
    # 1c. Quality regression check (F2)
    # --------------------------------------------------------
    regression_result = _regression_detector.check_regression()
    report["regression_check"] = regression_result
    if regression_result.get("regression_detected"):
        report["actions"].append({
            "type": "quality_regression_detected",
            "result": regression_result,
        })

    # --------------------------------------------------------
    # 1d. Long-horizon stability check (H3: more frequent reviews)
    # --------------------------------------------------------
    stability_result = _stability_tracker.detect_long_decline()
    report["stability_trend"] = stability_result
    if stability_result.get("decline_detected"):
        report["actions"].append({
            "type": "long_horizon_decline_detected",
            "result": stability_result,
        })

    # --------------------------------------------------------
    # 1e. Defensive coordination (C2 + M3)
    # --------------------------------------------------------
    cb_open = False
    quality_declining = False
    trend_declining = False
    if _PACER_AVAILABLE:
        cb_open = get_circuit_breaker().is_open
        trends = get_long_term_trends()
        trend_declining = (
            trends.get("consistency", {}).get("trend") == "declining"
            or trends.get("coherence", {}).get("trend") == "declining"
        )
    if _FLOW_TUNER_AVAILABLE:
        quality_declining = _flow_tuner.quality.any_degrading()

    coord_result = _defensive_coordinator.evaluate(
        circuit_breaker_open=cb_open,
        regression_active=_regression_detector.defensive_active,
        quality_degrading=quality_declining,
        trend_declining=trend_declining,
        severity_stressed=_severity_context.is_stressed(),
    )
    report["defensive_coordination"] = coord_result

    # --------------------------------------------------------
    # 2. Decide actions based on self-model
    # --------------------------------------------------------

    # All mutations below are routed through integration_layer (F1 fix).
    from knowledge import integration_layer as _il

    # Storage maintenance
    if _needs_storage_maintenance(before):
        result = _il.do_storage_maintenance()
        report["actions"].append({"type": "storage_maintenance", "result": result})

    # Consistency repair (always runs if needed, even during defensive)
    if _needs_consistency_repair(before):
        result = _il.do_consistency_scan()
        report["actions"].append({"type": "consistency_repair", "result": result})

    # Active consolidation (C1, C3-v3: ceiling 0.92)
    current_consistency = before["confidence"]["consistency"]
    if current_consistency < 0.92:
        result = _il.do_active_consolidation()
        report["actions"].append({"type": "active_consolidation", "result": result})

    # Concept evolution (C4: proportional intensity)
    if _needs_concept_evolution(before):
        result = _il.do_concept_evolution()
        report["actions"].append({"type": "concept_evolution", "result": result})

    # Knowledge expansion (suppressed during defensive posture)
    if _needs_knowledge_expansion(before):
        result = _il.do_curiosity_cycle()
        report["actions"].append({"type": "knowledge_expansion", "result": result})

    # Goal execution (F3): execute pending phases of approved goals
    if _needs_goal_execution():
        try:
            executable = get_executable_goals()
            for goal in executable[:2]:
                result = _il.do_execute_knowledge_goal(goal.id)
                report["actions"].append({"type": "goal_phase_execution", "result": result})
        except Exception as e:
            report["actions"].append({"type": "goal_phase_execution", "result": {"error": str(e)}})

    # Deferred verification
    if _needs_deferred_verification(before):
        result = _il.do_deferred_verification(limit=10)
        report["actions"].append({"type": "deferred_verification", "result": result})

    # P4: Quarantine review
    try:
        q_status = _il.do_quarantine_status()
        if q_status.get("result", {}).get("pending", 0) > 0:
            result = _il.do_quarantine_review()
            report["actions"].append({"type": "quarantine_review", "result": result})
    except Exception:
        pass

    # P2+: Batch trust calibration
    try:
        result = _il.do_batch_trust_calibration(sample_cap=500)
        if result.get("result", {}).get("calibrated", 0) > 0:
            report["actions"].append({"type": "batch_trust_calibration", "result": result})
    except Exception:
        pass

    # Provider discovery
    if _needs_provider_discovery(before):
        result = _il.do_provider_discovery()
        report["actions"].append({"type": "provider_discovery", "result": result})

    # Flow tuning
    if _needs_flow_tuning():
        result = _il.do_flow_tuning()
        report["actions"].append({"type": "flow_tuning", "result": result})

    # Post-attack sweep (F9)
    if _needs_attack_sweep():
        try:
            unswept = get_unswept_attack_windows()
            for aw in unswept[:3]:
                window_start = aw["detected_at"] - 300
                window_end = aw["detected_at"] + 60
                result = _il.do_attack_sweep(window_start, window_end)
                report["actions"].append({"type": "post_attack_sweep", "result": result})
        except Exception as e:
            report["actions"].append({"type": "post_attack_sweep", "result": {"error": str(e)}})

    # Delayed poisoning audit (M2)
    if _INTEGRITY_AVAILABLE:
        try:
            result = _il.do_delayed_poison_audit()
            if result.get("result", {}).get("flagged", 0) > 0:
                report["actions"].append({"type": "delayed_poison_audit", "result": result})
        except Exception:
            pass

    # --------------------------------------------------------
    # 2e. Anti-Entropy: Epoch management + graph compaction
    # --------------------------------------------------------
    try:
        epoch_st_result = _il.do_epoch_status()
        epoch_st = epoch_st_result.get("result", {})

        if not epoch_st.get("active") and epoch_st.get("should_start"):
            _il.do_start_epoch()
            report["actions"].append({
                "type": "epoch_started",
                "result": {"reason": epoch_st.get("reason", "no_epoch_running")},
            })
        elif epoch_st.get("should_end") and epoch_st.get("active"):
            _il.do_capture_epoch_metrics(before, phase="end")
            epoch_result = _il.do_end_epoch()
            end_data = epoch_result.get("result", {})
            report["actions"].append({
                "type": "epoch_ended",
                "result": {
                    "duration_hours": end_data.get("actual_duration_hours"),
                    "compaction": end_data.get("compaction_report", {}),
                    "drift_court": {
                        "reviewed": end_data.get("drift_court_report", {}).get("deviations_reviewed", 0),
                        "verdicts": end_data.get("drift_court_report", {}).get("verdicts", {}),
                    },
                    "renewal": {
                        "deleted": end_data.get("renewal_report", {}).get("deleted", 0),
                        "compacted": end_data.get("renewal_report", {}).get("compacted", 0),
                    },
                    "entropy_health": end_data.get("budget_report", {}).get("health", "unknown"),
                },
            })
            _il.do_start_epoch()
            report["actions"].append({
                "type": "epoch_started",
                "result": {"reason": "auto_restart_after_end"},
            })
        else:
            report["epoch_status"] = epoch_st
    except Exception as _ee:
        report["epoch_status"] = {"error": str(_ee)}

    # --------------------------------------------------------
    # 3. Optional claim verification — governed
    # --------------------------------------------------------
    if claim is not None:
        if _needs_verification(claim):
            verification = _il.do_claim_verification(claim)
            report["claim_verification"] = verification
            report["actions"].append({
                "type": "claim_verification",
                "claim": claim,
                "result": verification,
            })
        else:
            report["claim_verification"] = {
                "status": "no_verification_needed",
                "claim": claim,
            }

    # --------------------------------------------------------
    # 4. Update self-model again after actions
    # --------------------------------------------------------
    after = update_self_model()
    report["self_model_after"] = after

    return report


# ------------------------------------------------------------
# HIGH-LEVEL META-QUERIES
# ------------------------------------------------------------

def meta_status() -> Dict[str, Any]:
    """
    Returns a high-level summary of system health and meta-state,
    including regression detector, stability trends, severity, and
    circuit breaker status.
    """
    sm = get_self_model()

    status: Dict[str, Any] = {
        "knowledge_quality": sm["confidence"]["knowledge_quality"],
        "graph_coherence": sm["confidence"]["graph_coherence"],
        "consistency": sm["confidence"]["consistency"],
        "storage_ratio": sm["storage"].get("ratio"),
        "blind_spots": sm["blind_spots"][:10],
        "coverage_gaps": len(sm.get("coverage_gaps", [])),
        "frontier_domains": sm.get("frontier_domains", [])[:10],
        "expansion_needed": _needs_knowledge_expansion(sm),
        "subsystem_health": sm["subsystem_health"],
        "regression_detector": _regression_detector.status(),
        "stability_trend": _stability_tracker.status(),
        "severity": _severity_context.status(),
        "defensive_coordinator": _defensive_coordinator.status(),
    }

    if _PACER_AVAILABLE:
        status["circuit_breaker"] = get_circuit_breaker().status()
        status["long_term_trends"] = get_long_term_trends()

    if _DISCOVERY_AVAILABLE:
        status["active_providers"] = provider_registry.get_active_count()
        status["provider_notifications"] = len(
            provider_registry.get_notifications(unacknowledged_only=True)
        )

    if _FLOW_TUNER_AVAILABLE:
        status["flow_tuner"] = _flow_tuner.dashboard()

    try:
        from knowledge.entropy.epoch_engine import get_epoch_status
        from knowledge.entropy.entropy_budget import compute_entropy_budget
        status["epoch"] = get_epoch_status()
        budget = compute_entropy_budget()
        status["entropy_health"] = budget["health"]
        status["entropy_pressure"] = budget["entropy_pressure"]
    except (ImportError, Exception):
        pass

    return status
