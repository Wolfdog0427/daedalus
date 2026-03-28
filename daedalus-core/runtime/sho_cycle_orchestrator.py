# runtime/sho_cycle_orchestrator.py
"""
Class-based, dependency-injection SHO orchestrator for the runtime layer.

Hierarchy position
------------------
This module provides ``SHOCycleOrchestrator``, the class instantiated
by ``runtime_main.start_runtime()`` and driven by ``RuntimeLoop``.
It does NOT own the patch engine or state sources — those are injected
via ``PatchEngineAdapter.bind()``.

Related SHO modules (do NOT confuse):
  - ``orchestrator.sho_cycle_orchestrator``  — lightweight functional
    SHO used by ``sho_bootstrap`` and ``scheduler`` (knowledge-layer).
  - ``knowledge.self_healing_orchestrator`` — full pipeline SHO with
    sandboxing, scoring, and persistence for nightly / web-triggered
    improvement cycles.
  - ``orchestrator.orchestrator`` — planning-only orchestrator
    (security checks + proposal-to-plan translation).
"""

from __future__ import annotations

from typing import Any, Dict, Callable, Optional

from governor.autonomy_governor import AutonomyGovernor
from runtime.system_health import SystemHealth
from runtime.reliability_loader import load_reliability_dashboard
from runtime.patch_delta_integration import (
    build_pre_metrics,
    build_post_metrics,
    record_patch_deltas,
)


ApplyPatchFn = Callable[[str], Dict[str, Any]]
FetchPostStateFn = Callable[[], Dict[str, Any]]
FetchPlanFn = Callable[[str], Dict[str, Any]]


class SHOCycleOrchestrator:
    """Orchestrates a single SHO improvement cycle via dependency injection.

    Flow:
    - Build pre-metrics from current drift/stability/diagnostics
    - Ask governor for decision (which may create a proposal)
    - Optionally apply patch via injected apply_patch_fn
    - Optionally fetch post state via injected fetch_post_state_fn
    - Optionally log delta accuracy via injected plan fetch
    - Update SystemHealth (drift, stability, autonomy, reliability)
    """

    def __init__(
        self,
        governor: AutonomyGovernor,
        health: SystemHealth,
        apply_patch_fn: Optional[ApplyPatchFn] = None,
        fetch_post_state_fn: Optional[FetchPostStateFn] = None,
        fetch_plan_fn: Optional[FetchPlanFn] = None,
    ) -> None:
        self.governor = governor
        self.health = health
        self.apply_patch_fn = apply_patch_fn
        self.fetch_post_state_fn = fetch_post_state_fn
        self.fetch_plan_fn = fetch_plan_fn

    def run_cycle(
        self,
        cycle_id: str,
        drift: Dict[str, Any],
        diagnostics: Dict[str, Any],
        stability: Dict[str, Any],
        patch_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run a single SHO cycle with optional patch + delta logging.

        Returns a summary dict:
        {
            "governor_decision": ...,
            "patch_result": ... | None,
            "delta_logged": bool,
            "health_snapshot": ...,
        }
        """

        # Pre-metrics snapshot (before any patch)
        pre_metrics = build_pre_metrics(drift, stability, diagnostics)

        # Governor decision (this may create a proposal)
        decision = self.governor.decide_for_cycle(
            cycle_id=cycle_id,
            drift=drift,
            diagnostics=diagnostics,
            stability=stability,
            patch_history=patch_history,
        )

        proposal_id = decision.get("proposal_id")
        patch_result: Optional[Dict[str, Any]] = None
        delta_logged = False

        # Update SystemHealth with current state + governor state
        self._update_health(
            drift=drift,
            stability=stability,
            diagnostics=diagnostics,
            patch_history=patch_history,
        )

        # If no proposal or no patch function, we stop here
        if not proposal_id or not self.apply_patch_fn:
            snapshot = self.health.get_snapshot()
            return {
                "governor_decision": decision,
                "patch_result": patch_result,
                "delta_logged": delta_logged,
                "health_snapshot": snapshot,
            }

        # Apply patch via injected function
        patch_result = self.apply_patch_fn(proposal_id)

        # If we can't fetch post state, we can't log deltas safely
        if not self.fetch_post_state_fn:
            snapshot = self.health.get_snapshot()
            return {
                "governor_decision": decision,
                "patch_result": patch_result,
                "delta_logged": delta_logged,
                "health_snapshot": snapshot,
            }

        # Fetch post state (e.g. after next cycle or after validation)
        post_state = self.fetch_post_state_fn()

        post_drift = post_state.get("drift", {})
        post_stability = post_state.get("stability", {})
        post_diagnostics = post_state.get("diagnostics", diagnostics)

        # Update SystemHealth with post state
        self._update_health(
            drift=post_drift,
            stability=post_stability,
            diagnostics=post_diagnostics,
            patch_history=post_state.get("patch_history", patch_history),
        )

        # Build post-metrics snapshot
        post_metrics = build_post_metrics(
            post_drift,
            post_stability,
            post_diagnostics,
        )

        # If we can't fetch the plan, we can't log deltas
        if self.fetch_plan_fn and proposal_id:
            plan = self.fetch_plan_fn(proposal_id)
            record_patch_deltas(
                cycle_id=cycle_id,
                proposal_id=proposal_id,
                plan=plan,
                pre_metrics=pre_metrics,
                post_metrics=post_metrics,
            )
            delta_logged = True

        snapshot = self.health.get_snapshot()

        return {
            "governor_decision": decision,
            "patch_result": patch_result,
            "delta_logged": delta_logged,
            "health_snapshot": snapshot,
        }

    def _update_health(
        self,
        drift: Dict[str, Any],
        stability: Dict[str, Any],
        diagnostics: Dict[str, Any],
        patch_history: Dict[str, Any],
    ) -> None:
        """
        Push current state into SystemHealth, including reliability.
        """
        self.health.update_drift(drift)
        self.health.update_stability(stability)

        weakest = self._extract_weakest_subsystem(diagnostics)
        self.health.update_weakest_subsystem(weakest)

        self.health.update_patch_history(patch_history)

        # Autonomy state from governor
        self.health.update_autonomy_state(self.governor.get_state())

        # Reliability dashboard
        reliability = load_reliability_dashboard()
        self.health.update_reliability(
            reliability.get("subsystems", {}),
            reliability.get("actions", {}),
        )

    @staticmethod
    def _extract_weakest_subsystem(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
        subs = diagnostics.get("subsystems") or []
        if not subs:
            return {
                "name": "global",
                "score": 1.0,
                "risk": "none",
            }
        weakest = min(subs, key=lambda s: s.get("score", 1.0))
        return {
            "name": weakest.get("name") or weakest.get("subsystem", "unknown"),
            "score": weakest.get("score", 1.0),
            "risk": weakest.get("risk", "none"),
        }
