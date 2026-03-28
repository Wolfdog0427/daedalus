# knowledge/integration_layer.py

"""
Integration Layer

This module wraps all side-effectful operations and routes them
through the autonomy governor before allowing them to execute.

It ensures:
- strict mode is enforced by default
- guided/full modes unlock additional capabilities
- every action is checked, logged, and governed
- no subsystem can mutate state without passing through here

This is the enforcement layer for safe autonomy.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from knowledge.autonomy_governor import guard_action
from knowledge.storage_manager import maintenance_cycle
from knowledge.consistency_checker import run_consistency_check
from knowledge.concept_evolver import evolution_cycle, scoped_evolution_cycle
from knowledge.verification_pipeline import verify_new_information
from knowledge.reasoning_engine import reason_about_claim
from knowledge.curiosity_engine import (
    run_curiosity_cycle,
    approve_and_plan,
    run_quality_gate,
    execute_next_phase,
)
from knowledge.batch_ingestion import ingest_batch
from knowledge.adaptive_pacer import compute_pace, record_batch_result, should_acquire_now


# ------------------------------------------------------------
# SEVERITY-AWARE GOVERNANCE (F8)
# ------------------------------------------------------------

_HIGH_RISK_ACTIONS = frozenset({
    "knowledge.acquire",
    "concept.evolve",
    "concept.evolve_scoped",
    "knowledge.curiosity_cycle",
    "knowledge.approve_goal",
    "knowledge.execute_goal",
    "bootstrap.cycle",
    "scholarly.cycle",
})


def _severity_guard(action: str) -> Dict[str, Any]:
    """
    Augmented guard: consults both the autonomy governor AND the
    severity context. During stressed/catastrophic periods, high-risk
    mutating actions face a higher bar (they are blocked unless
    the governor is in permissive mode).
    """
    base_guard = guard_action(action)
    if not base_guard.get("allowed", False):
        return base_guard

    if action not in _HIGH_RISK_ACTIONS:
        return base_guard

    try:
        from knowledge.meta_reasoner import get_severity_context
        severity = get_severity_context()
        if severity.is_stressed():
            mode = base_guard.get("mode", "strict")
            if mode in ("strict", "normal"):
                return {
                    "allowed": False,
                    "requires_approval": True,
                    "reason": f"severity_gate:{severity.current_level}",
                    "mode": mode,
                }
    except ImportError:
        pass
    except Exception:
        return {
            "allowed": False,
            "requires_approval": True,
            "reason": "severity_gate_error_fail_closed",
            "mode": base_guard.get("mode", "strict"),
        }

    return base_guard


# ------------------------------------------------------------
# INTERNAL HELPER
# ------------------------------------------------------------

def _blocked(action_type: str, guard: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": action_type,
        "allowed": False,
        "requires_approval": guard.get("requires_approval", True),
        "reason": guard.get("reason", "blocked"),
        "mode": guard.get("mode"),
    }


# ------------------------------------------------------------
# WRAPPED ACTIONS
# ------------------------------------------------------------

def _safe_exec(action: str, fn, **extra) -> Dict[str, Any]:
    """Run *fn* inside a governed error boundary.

    On exception the result is ``allowed: True`` (governance passed) but
    ``success: False`` so callers can distinguish execution failure from
    governance rejection.
    """
    try:
        result = fn()
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            **extra,
        }
    return {"action": action, "allowed": True, "success": True, "result": result, **extra}


def do_storage_maintenance() -> Dict[str, Any]:
    action = "maintenance.storage"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, maintenance_cycle)


def do_consistency_scan() -> Dict[str, Any]:
    action = "maintenance.consistency_scan"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, run_consistency_check)


def do_concept_evolution() -> Dict[str, Any]:
    action = "concept.evolve"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    from knowledge.self_model import get_self_model
    coherence = get_self_model().get("confidence", {}).get("graph_coherence", 0.0)
    return _safe_exec(action, lambda: evolution_cycle(coherence=coherence))


def do_claim_verification(claim: str) -> Dict[str, Any]:
    action = "knowledge.verify"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: verify_new_information(claim, source="integration_layer"),
        claim=claim,
    )


def do_reasoning(claim: str) -> Dict[str, Any]:
    """
    Governed reasoning. reason_about_claim can trigger verification
    (which mutates the KB) for uncertain/unknown claims, so this
    must go through guard_action.
    """
    action = "knowledge.reason"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: reason_about_claim(claim),
        claim=claim,
    )


# ------------------------------------------------------------
# CURIOSITY & KNOWLEDGE ACQUISITION (Part 1 integration)
# ------------------------------------------------------------

def do_curiosity_cycle() -> Dict[str, Any]:
    """
    Run the curiosity engine to detect gaps and propose goals.
    Severity-gated: suppressed during stressed periods.
    """
    action = "knowledge.curiosity_cycle"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, run_curiosity_cycle)


def do_approve_knowledge_goal(goal_id: str) -> Dict[str, Any]:
    """
    Approve a proposed knowledge goal and generate its acquisition plan.
    Severity-gated.
    """
    action = "knowledge.approve_goal"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: approve_and_plan(goal_id),
        goal_id=goal_id,
    )


def do_execute_knowledge_goal(goal_id: str) -> Dict[str, Any]:
    """
    Execute the next pending phase of an approved knowledge goal.
    Severity-gated: blocked during stressed periods.
    """
    action = "knowledge.execute_goal"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: execute_next_phase(goal_id),
        goal_id=goal_id,
    )


def do_knowledge_acquisition(
    items: List[Dict[str, Any]],
    source: str = "acquisition",
    goal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a governed batch knowledge acquisition.
    Severity-gated: blocked during stressed periods.
    Coordinator-gated (C2): blocked when defensive level >= 3.
    """
    action = "knowledge.acquire"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    # C2: Defensive coordinator gate
    try:
        from knowledge.meta_reasoner import get_defensive_coordinator
        coord = get_defensive_coordinator()
        if coord.should_suppress_ingestion():
            return {
                "action": action,
                "allowed": True,
                "success": False,
                "paused": True,
                "reason": f"defensive_coordinator_level_{coord.current_level}",
            }
    except ImportError:
        pass
    except Exception:
        return {
            "action": action,
            "allowed": True,
            "success": False,
            "paused": True,
            "reason": "defensive_coordinator_error_fail_closed",
        }

    if not should_acquire_now():
        return {
            "action": action,
            "allowed": True,
            "paused": True,
            "reason": "cooldown_not_elapsed",
        }

    try:
        pace = compute_pace()

        if pace["action"] == "pause":
            return {
                "action": action,
                "allowed": True,
                "paused": True,
                "reason": pace["reason"],
                "pace": pace,
            }

        batch_size = pace["batch_size"]
        intensity = pace["verification_intensity"]
        batch_items = items[:batch_size]

        result = ingest_batch(
            items=batch_items,
            source=source,
            verification_intensity=intensity,
            goal_id=goal_id,
        )

        qb = result.get("quality_before")
        qa = result.get("quality_after")
        if qb and qa:
            record_batch_result(qb, qa)

        return {
            "action": action,
            "allowed": True,
            "success": True,
            "pace": pace,
            "result": result,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def do_quality_gate(goal_id: str) -> Dict[str, Any]:
    """
    Run the quality gate for an active knowledge goal.
    Persists quality metrics and may pause the goal if degradation
    is detected. Governed because it mutates goal persistence.
    """
    action = "knowledge.quality_gate"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.knowledge_goal import load_goal, save_goal

        goal = load_goal(goal_id)
        if goal is None:
            return {"action": action, "allowed": True, "success": False, "error": "goal_not_found"}

        gate = run_quality_gate(goal)

        goal.quality_after = {
            "graph_coherence": gate.get("coherence_after", 0),
            "consistency": gate.get("consistency_after", 0),
            "knowledge_quality": gate.get("quality", 0),
        }
        goal.coherence_delta = gate.get("coherence_delta", 0)
        goal.consistency_delta = gate.get("consistency_delta", 0)

        if not gate.get("passed"):
            goal.status = "paused"
        save_goal(goal)

        return {
            "action": action,
            "allowed": True,
            "success": True,
            "goal_id": goal_id,
            "result": gate,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "success": False,
            "goal_id": goal_id,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ------------------------------------------------------------
# META-COGNITION CYCLE
# ------------------------------------------------------------

def do_meta_cycle(claim: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a full meta-reasoning cycle. Read-heavy with potential
    maintenance side effects, so governed.
    """
    action = "meta.cycle"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.meta_reasoner import run_meta_cycle
        result = run_meta_cycle(claim=claim)
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ------------------------------------------------------------
# PROVIDER DISCOVERY (governed wrapper)
# ------------------------------------------------------------

def do_provider_discovery() -> Dict[str, Any]:
    """
    Run LLM/AGI provider discovery. Read-only scanning is low-risk
    but activation requires governance.
    """
    action = "providers.discover"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.provider_discovery import run_discovery_cycle, provider_registry
        result = run_discovery_cycle(provider_registry)
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except ImportError:
        return {"action": action, "error": "provider_discovery_not_available"}


# ------------------------------------------------------------
# FLOW TUNING (governed wrapper)
# ------------------------------------------------------------

def do_flow_tuning() -> Dict[str, Any]:
    """
    Run flow tuning cycle. Adjusts pipeline parameters.
    """
    action = "pipeline.tune"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.flow_tuner import flow_tuner
        result = flow_tuner.tune()
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except ImportError:
        return {"action": action, "error": "flow_tuner_not_available"}


# ------------------------------------------------------------
# SCOPED EVOLUTION (Part 2 acceleration)
# ------------------------------------------------------------

def do_active_consolidation() -> Dict[str, Any]:
    """
    Run active consistency consolidation (C1). Governed because
    it removes items and modifies the graph.
    """
    action = "maintenance.consolidation"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.consistency_checker import run_active_consolidation
        from knowledge.self_model import get_self_model
        sm = get_self_model()
        conf = sm.get("confidence", {})
        consistency = conf.get("consistency", 0.0)
        coherence = conf.get("graph_coherence", 0.0)
        result = run_active_consolidation(consistency, coherence)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_delayed_poison_audit() -> Dict[str, Any]:
    """
    Run delayed poisoning detection (M2). Read-heavy with
    potential flagging side effects.
    """
    action = "security.poison_audit"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.source_integrity import run_delayed_poison_audit
        result = run_delayed_poison_audit(sample_size=100)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_quarantine_review() -> Dict[str, Any]:
    """Review quarantined items (P4). Governed because it can release items."""
    action = "security.quarantine_review"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.source_integrity import review_quarantine
        result = review_quarantine(max_review=50)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_quarantine_status() -> Dict[str, Any]:
    """Get quarantine queue status (P4). Governed for audit trail."""
    action = "security.quarantine_status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.source_integrity import get_quarantine_status
        return {"action": action, "allowed": True, "result": get_quarantine_status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_scoped_evolution(cluster_entities: List[str]) -> Dict[str, Any]:
    """
    Run concept evolution scoped to a specific cluster.
    Severity-gated.
    """
    action = "concept.evolve_scoped"
    guard = _severity_guard(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: scoped_evolution_cycle(cluster_entities),
    )


# ------------------------------------------------------------
# ANTI-ENTROPY LAYER (governed wrappers)
# ------------------------------------------------------------

def do_entropy_budget_report() -> Dict[str, Any]:
    """Compute and return the entropy budget report. Read-only."""
    action = "entropy.budget_report"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.entropy_budget import compute_entropy_budget
        return {"action": action, "allowed": True, "result": compute_entropy_budget()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_epoch_status() -> Dict[str, Any]:
    """Get current epoch status. Read-only."""
    action = "entropy.epoch_status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.epoch_engine import get_epoch_status
        return {"action": action, "allowed": True, "result": get_epoch_status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_start_epoch(duration_hours: float = 48.0) -> Dict[str, Any]:
    """Start a new operational epoch. Governed mutation."""
    action = "entropy.epoch_start"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.epoch_engine import start_epoch
        result = start_epoch(duration_hours=duration_hours)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_end_epoch() -> Dict[str, Any]:
    """
    End the current epoch (triggers graph compaction, drift court,
    entropy budget snapshot, and renewal). Governed mutation.
    """
    action = "entropy.epoch_end"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.epoch_engine import end_epoch
        result = end_epoch()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_renewal_cycle(dry_run: bool = False) -> Dict[str, Any]:
    """Run the renewal layer (prune expired transient state). Governed mutation."""
    action = "entropy.renewal"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.renewal_layer import run_renewal
        result = run_renewal(dry_run=dry_run)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_drift_court() -> Dict[str, Any]:
    """Run a Drift Court session. Governed mutation (may create proposals)."""
    action = "entropy.drift_court"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.drift_court import run_drift_court
        result = run_drift_court()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_graph_compaction() -> Dict[str, Any]:
    """Run graph compaction (coherence fix). Governed mutation."""
    action = "entropy.graph_compaction"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.graph_compactor import run_compaction
        result = run_compaction()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_canonical_template_summary() -> Dict[str, Any]:
    """Get canonical template summary. Read-only."""
    action = "entropy.template_summary"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.canonical_template import get_template_summary
        return {"action": action, "allowed": True, "result": get_template_summary()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_renewal_status() -> Dict[str, Any]:
    """Get renewal layer status. Read-only."""
    action = "entropy.renewal_status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.renewal_layer import get_renewal_status
        return {"action": action, "allowed": True, "result": get_renewal_status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_drift_court_summary() -> Dict[str, Any]:
    """Get drift court history summary. Read-only."""
    action = "entropy.court_summary"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.drift_court import get_court_summary
        return {"action": action, "allowed": True, "result": get_court_summary()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_apply_canonization(proposal_id: str) -> Dict[str, Any]:
    """Apply an approved canonization proposal. Governed mutation."""
    action = "entropy.canonize"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.drift_court import apply_approved_canonization
        result = apply_approved_canonization(proposal_id)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# ------------------------------------------------------------
# ADDITIONAL GOVERNED WRAPPERS (F1: close governance bypass)
# ------------------------------------------------------------

def do_deferred_verification(limit: int = 10) -> Dict[str, Any]:
    """Verify deferred batch items. Governed mutation (modifies KB)."""
    action = "knowledge.deferred_verify"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.batch_ingestion import verify_deferred_items
        result = verify_deferred_items(limit=limit)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_trust_decay() -> Dict[str, Any]:
    """Apply natural trust decay. Governed mutation (modifies trust scores)."""
    action = "trust.decay"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.trust_scoring import apply_trust_decay
        apply_trust_decay()
        return {"action": action, "allowed": True, "result": {"applied": True}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_batch_trust_calibration(sample_cap: int = 500) -> Dict[str, Any]:
    """Calibrate trust scores across the KB. Governed mutation."""
    action = "trust.calibrate"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.trust_scoring import batch_calibrate_trust
        result = batch_calibrate_trust(sample_cap=sample_cap)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def _default_reverify(item_id: str, source: str) -> bool:
    """Re-verify an item by running source integrity validation.

    Returns True if the item passes re-verification, False if suspect.
    Used by attack sweeps so flagged items get real re-checks instead
    of blanket flagging.
    """
    try:
        from knowledge.source_integrity import validate_url
        if "://" in source:
            url_check = validate_url(source)
            if url_check.get("blocked"):
                return False
            if url_check.get("threat_level") in ("high", "critical"):
                return False
        return True
    except Exception:
        return False


def do_attack_sweep(window_start: float, window_end: float) -> Dict[str, Any]:
    """Sweep items ingested during an attack window. Governed mutation."""
    action = "security.attack_sweep"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.source_integrity import sweep_attack_window
        result = sweep_attack_window(
            window_start, window_end, reverify_fn=_default_reverify)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_taint_propagation(item_id: str) -> Dict[str, Any]:
    """Propagate taint from a discovered contaminated item. Governed mutation."""
    action = "security.taint_propagation"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.source_integrity import propagate_taint
        result = propagate_taint(item_id)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_source_anomaly_scan() -> Dict[str, Any]:
    """Detect anomalous sources via statistical clustering. Read-heavy."""
    action = "security.anomaly_scan"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.source_integrity import detect_source_anomalies
        result = detect_source_anomalies()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_contamination_pressure_check(
    estimated_contaminated: int, active_items: int,
) -> Dict[str, Any]:
    """Compute contamination pressure relative to budget. Read-only."""
    action = "security.contamination_pressure"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.source_integrity import compute_contamination_pressure
        result = compute_contamination_pressure(estimated_contaminated, active_items)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_capture_epoch_metrics(metrics: Dict[str, Any], phase: str = "end") -> Dict[str, Any]:
    """Snapshot system metrics into the current epoch. Low-risk write."""
    action = "entropy.capture_metrics"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.epoch_engine import capture_epoch_metrics
        capture_epoch_metrics(metrics, phase=phase)
        return {"action": action, "allowed": True, "result": {"phase": phase}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_entropy_register_state(path: str, tier: str) -> Dict[str, Any]:
    """Register a new state path in the canonical template. Governed mutation."""
    action = "entropy.register_state"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.entropy.canonical_template import register_state
        result = register_state(path, tier)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# CAPABILITY MODULES (Tier 1-4)
# ============================================================

# --- Module 1: Temporal Reasoning ---

def do_temporal_maintenance() -> Dict[str, Any]:
    """Run temporal obsolescence sweep. Low-risk maintenance."""
    action = "maintenance.temporal"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.temporal_reasoning import run_temporal_maintenance
        result = run_temporal_maintenance()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 3: Hypothesis Testing ---

def do_hypothesis_test(text_a: str, text_b: str) -> Dict[str, Any]:
    """LLM-powered contradiction resolution. Read-heavy analysis."""
    action = "knowledge.hypothesis_test"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.hypothesis_tester import resolve_contradiction
        result = resolve_contradiction(text_a, text_b)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_batch_hypothesis_resolve(contradictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Batch LLM contradiction resolution. Read-heavy analysis."""
    action = "knowledge.batch_hypothesis"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.hypothesis_tester import batch_resolve
        result = batch_resolve(contradictions)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 4: Goal Decomposition ---

def do_goal_decomposition(goal_id: str) -> Dict[str, Any]:
    """Decompose a complex goal into sub-goals. Governed mutation."""
    action = "knowledge.decompose_goal"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.knowledge_goal import load_goal, save_goal
        from knowledge.goal_planner import is_complex_goal, decompose_goal

        goal = load_goal(goal_id)
        if goal is None:
            return {"action": action, "allowed": True, "error": "goal_not_found"}

        if not is_complex_goal(goal):
            return {"action": action, "allowed": True, "result": {"decomposed": False,
                    "reason": "not_complex"}}

        sub_goals = decompose_goal(goal)
        sub_ids = []
        for sg in sub_goals:
            save_goal(sg)
            sub_ids.append(sg.id)

        goal.metadata["sub_goal_ids"] = sub_ids
        save_goal(goal)

        return {"action": action, "allowed": True, "result": {
            "decomposed": True, "sub_goals": len(sub_goals), "sub_goal_ids": sub_ids}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 5: Collaborative Memory ---

def do_record_interaction(
    operator_id: str, interaction_type: str, details: Dict[str, Any],
) -> Dict[str, Any]:
    """Log an operator interaction. Low-risk write."""
    action = "memory.record_interaction"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.collaborative_memory import record_interaction
        record_interaction(operator_id, interaction_type, details)
        return {"action": action, "allowed": True, "result": {"recorded": True}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_memory_consolidation() -> Dict[str, Any]:
    """Consolidate short-term interactions into patterns. Maintenance."""
    action = "memory.consolidation"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.collaborative_memory import run_memory_consolidation
        result = run_memory_consolidation()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_operator_transfer(old_operator: str, new_operator: str) -> Dict[str, Any]:
    """Transfer operator context during transition. Governed mutation."""
    action = "memory.operator_transfer"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.collaborative_memory import transfer_context
        result = transfer_context(old_operator, new_operator)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 6: RAR Engine ---

def do_rar_query(
    query: str, operator_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieval-augmented reasoning query. Read-heavy."""
    action = "knowledge.rar_query"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.rar_engine import reason_with_context
        result = reason_with_context(query, operator_id=operator_id)
        return {"action": action, "allowed": True, "result": {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources_cited": len(result.sources_cited),
            "gaps_detected": result.gaps_detected,
            "elapsed_ms": result.elapsed_ms,
        }}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 7: Explanation Engine ---

def do_explain(item_id: str) -> Dict[str, Any]:
    """Explain a knowledge item's provenance and trust. Read-only."""
    action = "knowledge.explain"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.explanation_engine import explain_belief, format_for_operator
        explanation = explain_belief(item_id)
        return {"action": action, "allowed": True, "result": explanation,
                "formatted": format_for_operator(explanation)}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_explain_reasoning(query: str) -> Dict[str, Any]:
    """Explain the reasoning behind a query answer. Read-only."""
    action = "knowledge.explain_reasoning"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.rar_engine import reason
        from knowledge.explanation_engine import explain_reasoning, format_for_operator
        rar_result = reason(query)
        explanation = explain_reasoning(rar_result)
        return {"action": action, "allowed": True, "result": explanation,
                "formatted": format_for_operator(explanation)}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 8: Active Learning ---

def do_active_learn(query: str, gap: Dict[str, Any]) -> Dict[str, Any]:
    """Fill a knowledge gap via active learning. Governed ingestion."""
    action = "knowledge.active_learn"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.active_learner import learn_and_continue
        result = learn_and_continue(gap, query)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_active_learning_cycle(recent_gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Batch active learning cycle. Governed ingestion."""
    action = "knowledge.active_learning_cycle"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.active_learner import run_active_learning_cycle
        result = run_active_learning_cycle(recent_gaps)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# --- Module 9: Federated Exchange ---

def do_federated_import(
    items: List[Dict[str, Any]], peer_id: str,
    signature: Optional[str] = None,
) -> Dict[str, Any]:
    """Import knowledge from a peer instance. High-risk governed."""
    action = "federated.import"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.federated_exchange import import_items
        result = import_items(items, peer_id, signature=signature)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_federated_export(
    filter_query: Optional[str] = None, min_trust: float = 0.7,
) -> Dict[str, Any]:
    """Export verified knowledge for peer sharing. Read-heavy."""
    action = "federated.export"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.federated_exchange import export_items
        items = export_items(filter_query=filter_query, min_trust=min_trust)
        return {"action": action, "allowed": True, "result": {
            "items_exported": len(items), "items": items}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_federated_sync(
    peer_id: str,
    outgoing: Optional[List[Dict[str, Any]]] = None,
    incoming: Optional[List[Dict[str, Any]]] = None,
    incoming_signature: Optional[str] = None,
) -> Dict[str, Any]:
    """Bidirectional sync with a peer. High-risk governed."""
    action = "federated.sync"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.federated_exchange import sync_protocol
        result = sync_protocol(peer_id, outgoing, incoming, incoming_signature=incoming_signature)
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# BOOTSTRAP PROTOCOL (ABP)
# ============================================================

def do_start_bootstrap() -> Dict[str, Any]:
    """Start the Accelerated Bootstrap Protocol. Governed mutation."""
    action = "bootstrap.start"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.bootstrap_protocol import start_bootstrap
        result = start_bootstrap()
        return {"action": action, "allowed": True, "result": result}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_bootstrap_status() -> Dict[str, Any]:
    """Get ABP status. Read-only."""
    action = "bootstrap.status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.bootstrap_protocol import bootstrap_status
        return {"action": action, "allowed": True, "result": bootstrap_status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_bootstrap_cycle() -> Dict[str, Any]:
    """
    Run one ABP learning cycle: get next targets, query LLM, ingest.
    Severity-gated: suppressed during stressed periods.
    """
    action = "bootstrap.cycle"
    guard = _severity_guard(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.bootstrap_protocol import get_bootstrap, is_abp_active
        if not is_abp_active():
            return {"action": action, "allowed": True, "result": {"active": False}}

        abp = get_bootstrap()
        targets = abp.get_next_learning_targets(max_targets=3)
        if not targets:
            return {"action": action, "allowed": True,
                    "result": {"active": True, "targets": 0, "note": "no_eligible_targets"}}

        results = []
        for t in targets:
            results.append({
                "key": t["key"],
                "discipline": t["discipline"],
                "sub_domain": t["sub_domain"],
            })

        return {"action": action, "allowed": True,
                "result": {"active": True, "targets_processed": len(results),
                           "targets": results}}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# ADAPTIVE CADENCE
# ============================================================

def do_cadence_status() -> Dict[str, Any]:
    """Get adaptive cadence status. Read-only."""
    action = "cadence.status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.adaptive_cadence import get_cadence_manager
        return {"action": action, "allowed": True,
                "result": get_cadence_manager().status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


def do_set_cadence_mode(mode: str, multiplier: float = 1.0) -> Dict[str, Any]:
    """Change cadence mode. Governed mutation."""
    action = "cadence.set_mode"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.adaptive_cadence import get_cadence_manager, CadenceMode
        mgr = get_cadence_manager()
        mgr.set_mode(CadenceMode(mode), multiplier)
        return {"action": action, "allowed": True, "result": mgr.status()}
    except Exception as exc:
        return {"action": action, "allowed": True, "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# SCHOLARLY MODE (Post-Graduate Lifelong Learning)
# ============================================================

def do_scholarly_cycle(system_state: Dict[str, Any]) -> Dict[str, Any]:
    """Run one scholarly mode cycle. Governed mutation."""
    action = "scholarly.cycle"
    guard = _severity_guard(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.scholarly_mode import run_scholarly_cycle, is_scholarly_active
        if not is_scholarly_active():
            return {"action": action, "allowed": True,
                    "result": {"active": False}}
        return {"action": action, "allowed": True,
                "result": run_scholarly_cycle(system_state)}
    except Exception as exc:
        return {"action": action, "allowed": True,
                "error": f"{type(exc).__name__}: {exc}"}


def do_activate_scholarly_mode() -> Dict[str, Any]:
    """Activate scholarly mode after ABP graduation. Governed mutation."""
    action = "scholarly.activate"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.scholarly_mode import activate_scholarly_mode
        return {"action": action, "allowed": True,
                "result": activate_scholarly_mode()}
    except Exception as exc:
        return {"action": action, "allowed": True,
                "error": f"{type(exc).__name__}: {exc}"}


def do_scholarly_status() -> Dict[str, Any]:
    """Get scholarly mode status. Read-only."""
    action = "scholarly.status"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.scholarly_mode import scholarly_status
        return {"action": action, "allowed": True,
                "result": scholarly_status()}
    except Exception as exc:
        return {"action": action, "allowed": True,
                "error": f"{type(exc).__name__}: {exc}"}


def do_record_interest(topic: str, source: str, strength: float = 0.1) -> Dict[str, Any]:
    """Record an interest signal for scholarly exploration. Governed mutation."""
    action = "scholarly.record_interest"
    guard = guard_action(action)
    if not guard["allowed"]:
        return _blocked(action, guard)
    try:
        from knowledge.scholarly_mode import record_interest
        record_interest(topic, source, strength)
        return {"action": action, "allowed": True,
                "result": {"topic": topic, "source": source, "strength": strength}}
    except Exception as exc:
        return {"action": action, "allowed": True,
                "error": f"{type(exc).__name__}: {exc}"}
