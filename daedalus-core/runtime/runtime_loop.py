from __future__ import annotations
from typing import Dict, Any

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

# ------------------------------------------------------------
# Existing imports (unchanged)
# ------------------------------------------------------------
from runtime.state_sources import fetch_state
from runtime.patch_engine import apply_patch
from runtime.patch_history_manager import record_patch_result
from runtime.metrics_capture import capture_pre_metrics, capture_post_metrics
from runtime.logging_manager import log_event

from runtime.system_health import SystemHealth
from runtime.sho_cycle_orchestrator import run_sho_cycle


def run_runtime_cycle() -> Dict[str, Any]:
    """
    Execute a full runtime cycle:
    - Fetch state
    - Update SystemHealth
    - Run SHO cycle
    - Apply patch (if accepted)
    - Record patch history
    - Capture metrics

    HEM Integration (Option C):
    - Enter HEM on cycle start (external interaction trigger)
    - Transition to post-check after SHO + patch flow
    - Run drift/integrity checks before exiting
    """

    # ------------------------------------------------------------
    # HEM: Enter hostile engagement mode for this cycle
    # ------------------------------------------------------------
    hem_maybe_enter(trigger_reason="runtime_cycle")

    # ------------------------------------------------------------
    # 1. Fetch current state
    # ------------------------------------------------------------
    state = fetch_state()
    drift = state["drift"]
    stability = state["stability"]
    diagnostics = state["diagnostics"]
    patch_history = state["patch_history"]

    # ------------------------------------------------------------
    # 2. Update SystemHealth
    # ------------------------------------------------------------
    health = SystemHealth()
    health.update_drift(drift)
    health.update_stability(stability)
    health.update_diagnostics(diagnostics)
    health.update_patch_history(patch_history)

    log_event("runtime", "SystemHealth updated", {
        "drift": drift,
        "stability": stability,
        "diagnostics": diagnostics,
    })

    # ------------------------------------------------------------
    # 3. Capture pre-metrics for delta validation
    # ------------------------------------------------------------
    pre_metrics = capture_pre_metrics(drift, stability, diagnostics)

    # ------------------------------------------------------------
    # 4. Run SHO cycle orchestrator
    # ------------------------------------------------------------
    cycle_result = run_sho_cycle(
        drift=drift,
        stability=stability,
        diagnostics=diagnostics,
        patch_history=patch_history,
    )

    log_event("sho_cycle", "SHO cycle completed", {
        "cycle_id": cycle_result.get("cycle_id"),
        "decision": cycle_result.get("decision"),
    })

    # ------------------------------------------------------------
    # 5. Apply patch if accepted
    # ------------------------------------------------------------
    decision = cycle_result.get("decision")
    proposal_id = cycle_result.get("proposal_id")
    tier = cycle_result.get("tier")

    if decision == "accepted" and proposal_id:
        patch_result = apply_patch(proposal_id)
    else:
        patch_result = {"status": "not_implemented"}

    # ------------------------------------------------------------
    # 6. Record patch result in history
    # ------------------------------------------------------------
    record_patch_result(
        cycle_id=cycle_result.get("cycle_id"),
        tier=tier,
        result=patch_result,
    )

    # ------------------------------------------------------------
    # 7. Capture post-metrics for delta validation
    # ------------------------------------------------------------
    post_state = fetch_state()
    post_metrics = capture_post_metrics(
        post_state["drift"],
        post_state["stability"],
        post_state["diagnostics"],
    )

    log_event("runtime", "Runtime cycle complete", {
        "cycle_id": cycle_result.get("cycle_id"),
        "patch_status": patch_result.get("status"),
    })

    # ------------------------------------------------------------
    # HEM: Transition to post-check phase
    # ------------------------------------------------------------
    hem_transition_to_postcheck()

    # ------------------------------------------------------------
    # HEM: Run drift + integrity checks, rollback if needed
    # ------------------------------------------------------------
    hem_run_post_engagement_checks()

    # ------------------------------------------------------------
    # Return cycle summary
    # ------------------------------------------------------------
    return {
        "cycle": cycle_result,
        "patch": patch_result,
        "pre_metrics": pre_metrics,
        "post_metrics": post_metrics,
        "state": post_state,
    }
