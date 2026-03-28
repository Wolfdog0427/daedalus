from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

# ------------------------------------------------------------
# Existing imports
# ------------------------------------------------------------
from runtime.state_sources import fetch_state
from runtime.patch_history_manager import record_patch_result
from runtime.patch_delta_integration import build_pre_metrics, build_post_metrics
from runtime.logging_manager import log_event

from runtime.system_health import SystemHealth
from runtime.sho_cycle_orchestrator import SHOCycleOrchestrator


# ------------------------------------------------------------------
# RuntimeLoop — class-based wrapper expected by runtime_main.py
# ------------------------------------------------------------------

class RuntimeLoop:
    """Governed runtime loop that repeatedly executes SHO cycles.

    Accepts a ``SHOCycleOrchestrator`` (dependency-injected), an
    external ``fetch_state_fn``, and a maintenance cadence.  Each call
    to :meth:`run_once` performs one full cycle with HEM integration.
    """

    def __init__(
        self,
        orchestrator: SHOCycleOrchestrator,
        fetch_state_fn: Callable[[], Dict[str, Any]],
        maintenance_interval_cycles: int = 10,
    ) -> None:
        self.orchestrator = orchestrator
        self.fetch_state_fn = fetch_state_fn
        self.maintenance_interval_cycles = maintenance_interval_cycles
        self._cycle_counter: int = 0

    def tick(self) -> Dict[str, Any]:
        """Alias for :meth:`run_once`."""
        return self.run_once()

    def run_once(self) -> Dict[str, Any]:
        """Execute a single governed runtime cycle."""
        self._cycle_counter += 1
        cycle_id = f"rt-{uuid.uuid4().hex[:12]}"

        hem_maybe_enter(trigger_reason="runtime_cycle")
        try:
            state = self.fetch_state_fn()
            drift = state.get("drift", {})
            stability = state.get("stability", {})
            diagnostics = state.get("diagnostics", {})
            patch_history = state.get("patch_history", {})

            cycle_result = self.orchestrator.run_cycle(
                cycle_id=cycle_id,
                drift=drift,
                diagnostics=diagnostics,
                stability=stability,
                patch_history=patch_history,
            )
        finally:
            try:
                hem_transition_to_postcheck()
            except Exception:
                pass
            try:
                hem_run_post_engagement_checks()
            except Exception:
                pass

        return {
            "cycle_id": cycle_id,
            "cycle_counter": self._cycle_counter,
            "cycle_result": cycle_result,
        }

    @property
    def needs_maintenance(self) -> bool:
        return (
            self._cycle_counter > 0
            and self.maintenance_interval_cycles > 0
            and self._cycle_counter % self.maintenance_interval_cycles == 0
        )


# ------------------------------------------------------------------
# Standalone convenience function (backward-compatible)
# ------------------------------------------------------------------

def run_runtime_cycle() -> Dict[str, Any]:
    """Execute a single runtime cycle using default state sources.

    This standalone function is kept for backward compatibility with
    callers that do not use the class-based ``RuntimeLoop`` path
    (e.g. ad-hoc REPL invocations).
    """
    hem_maybe_enter(trigger_reason="runtime_cycle")
    try:
        state = fetch_state()
        drift = state.get("drift", {})
        stability = state.get("stability", {})
        diagnostics = state.get("diagnostics", {})
        patch_history = state.get("patch_history", {})

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

        pre_metrics = build_pre_metrics(drift, stability, diagnostics)

        cycle_id = f"rt-{uuid.uuid4().hex[:12]}"
        from runtime.sho_bootstrap import run_sho_cycle as _bootstrap_sho
        cycle_result = _bootstrap_sho()

        log_event("sho_cycle", "SHO cycle completed", {
            "cycle_id": cycle_id,
            "result": cycle_result.get("status"),
        })

        decision = cycle_result.get("result", {}).get("cycle", {}).get("mode")
        patch_data = cycle_result.get("result", {}).get("patch")
        proposal_id = None
        if patch_data and isinstance(patch_data, dict):
            proposal_id = patch_data.get("proposal")

        if decision == "autonomous" and proposal_id and patch_data.get("applied"):
            patch_result = {"status": "applied_by_sho"}
        else:
            patch_result = {"status": "not_applied"}

        record_patch_result(
            cycle_id=cycle_id,
            tier=None,
            result=patch_result,
        )

        post_state = fetch_state()
        post_metrics = build_post_metrics(
            post_state.get("drift", {}),
            post_state.get("stability", {}),
            post_state.get("diagnostics", {}),
        )

        log_event("runtime", "Runtime cycle complete", {
            "cycle_id": cycle_id,
            "patch_status": patch_result.get("status"),
        })
    finally:
        try:
            hem_transition_to_postcheck()
        except Exception:
            pass
        try:
            hem_run_post_engagement_checks()
        except Exception:
            pass

    return {
        "cycle": cycle_result,
        "patch": patch_result,
        "pre_metrics": pre_metrics,
        "post_metrics": post_metrics,
        "state": post_state,
    }
