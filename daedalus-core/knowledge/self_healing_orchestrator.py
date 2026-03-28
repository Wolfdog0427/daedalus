# knowledge/self_healing_orchestrator.py
"""
Full-pipeline Self-Healing Orchestrator (SHO).

Hierarchy position
------------------
This is the *richest* SHO implementation: diagnostics → candidate
generation → sandboxing → scoring → drift reporting → snapshot
persistence.  It is used for nightly / web-triggered improvement
cycles where thorough evaluation and auditability are required.

Related SHO modules (do NOT confuse):
  - ``orchestrator.sho_cycle_orchestrator``  — lightweight functional
    SHO (tier-driven observe / propose / apply).
  - ``runtime.sho_cycle_orchestrator``  — class-based, DI-style
    orchestrator used by ``RuntimeLoop`` / ``runtime_main``.
  - ``orchestrator.orchestrator`` — planning-only orchestrator
    (security checks + proposal-to-plan translation).
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from pathlib import Path

from diagnostics.realtime_diagnoser import RealtimeDiagnoser, FailureReport
from knowledge.patch_generator import generate_patches_for_goal
from knowledge.sandbox_runner import run_in_sandbox
from knowledge.stability_engine import evaluate_stability
from knowledge.trust_scoring import score_candidate
from knowledge.storage_manager import (
    save_version_snapshot,
    save_cockpit_snapshot,
)
from knowledge.audit_log import log_event
from knowledge.drift_detector import (
    load_recent_decisions,
    compute_drift_report,
)


def _timestamp() -> str:
    return datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def _cockpit_path(name: str) -> str:
    return os.path.join("data", "cockpit", name)


def _tune_parameters_based_on_drift(drift: dict) -> dict:
    """
    Adjust SHO behavior based on drift level.
    """

    level = drift.get("level", "none")

    if level == "none":
        return {
            "max_candidates": 2,
            "strict_safety": True,
            "exploration": "low",
            "mode": "stability",
        }

    if level == "low":
        return {
            "max_candidates": 3,
            "strict_safety": True,
            "exploration": "medium",
            "mode": "normal",
        }

    if level == "medium":
        return {
            "max_candidates": 5,
            "strict_safety": False,
            "exploration": "high",
            "mode": "adaptive",
        }

    if level == "high":
        return {
            "max_candidates": 2,
            "strict_safety": True,
            "exploration": "minimal",
            "mode": "recovery",
        }

    return {
        "max_candidates": 3,
        "strict_safety": True,
        "exploration": "medium",
        "mode": "normal",
    }


def _governance_gate() -> dict | None:
    """Check governance state before running an improvement cycle.

    Returns ``None`` if the system is clear.  Returns a structured
    block dict if any emergency state (kill switch, circuit breaker,
    stabilise mode, autonomy-governor lock) is active.
    """
    try:
        from governance.kernel import (
            _kill_switch_active,
            _circuit_breaker_tripped,
            _stabilise_mode,
        )
        if _kill_switch_active:
            return {"blocked": True, "reason": "kill switch active"}
        if _circuit_breaker_tripped:
            return {"blocked": True, "reason": "circuit breaker tripped"}
        if _stabilise_mode:
            return {"blocked": True, "reason": "stabilise mode active"}
    except ImportError:
        pass

    try:
        from knowledge.autonomy_governor import guard_action
        guard = guard_action("sho_improvement_cycle")
        if not guard.get("allowed", False):
            return {"blocked": True, "reason": guard.get("reason", "governor blocked")}
    except ImportError:
        pass

    return None


def run_improvement_cycle(
    goal: str = "general improvement",
    max_candidates: int | None = None,
    max_iterations: int = 5,
    strict_safety: bool | None = None,
):
    cycle_id = str(uuid.uuid4())
    log_event("sho_cycle_start", {"cycle_id": cycle_id, "goal": goal})

    gate = _governance_gate()
    if gate is not None:
        log_event("sho_cycle_blocked", {"cycle_id": cycle_id, **gate})
        return {
            "cycle_id": cycle_id,
            "decision": "blocked",
            **gate,
        }

    # 1. Load previous decision + provisional drift for tuning
    previous_decisions = load_recent_decisions(limit=1)
    previous = previous_decisions[0] if previous_decisions else None

    provisional_drift = compute_drift_report(
        current_decision={"best_candidate": {}, "cycle_id": cycle_id},
        previous_decision=previous,
    )
    tuned = _tune_parameters_based_on_drift(provisional_drift)

    max_candidates = max_candidates or tuned["max_candidates"]
    strict_safety = strict_safety if strict_safety is not None else tuned["strict_safety"]

    # 2. Diagnostics (now subsystem-aware)
    diagnoser = RealtimeDiagnoser()
    synthetic_snapshot = {
        "error_type": "system_review",
        "subsystem": "global",
        "pipeline_stage": "sho_diagnostics",
        "error_message": "",
        "parsed_intent": "",
        "resolver_target": "",
        "user_input": "",
    }
    report = diagnoser.analyze_interaction(synthetic_snapshot)
    if report is None:
        report = FailureReport(
            failure_type="system_review",
            details={"info": "Periodic improvement cycle"},
        )

    subsystem_diagnostics = report.details.get("subsystem_diagnostics", {})

    # 2b. MetaGovernor review (blocks plans that violate meta-invariants)
    try:
        from governance.meta_governor import MetaGovernor
        from core.contracts import ImprovementPlan, SecurityStatus, FixRequest
        _mg = MetaGovernor()
        _fix = FixRequest(
            target_subsystem="knowledge",
            change_type="refactor",
            severity="medium",
            constraints={},
            max_cycles=3,
            max_runtime_seconds=300,
        )
        _plan = ImprovementPlan(
            fix_request=_fix,
            allowed_modules=["knowledge"],
            forbidden_modules=[],
            change_budget_files=5,
            change_budget_lines=50,
            safety_invariants=["NO_AUTONOMY_EXPANSION"],
        )
        _sec = SecurityStatus(
            mode="normal",
            last_events=[],
            integrity_ok=True,
            unknown_capabilities_detected=False,
            recommendations=[],
        )
        _plan = _mg.review_plan(_plan, _sec)
        if _plan.blocked:
            log_event("sho_cycle_meta_blocked", {
                "cycle_id": cycle_id,
                "reason": _plan.block_reason,
            })
            return {
                "cycle_id": cycle_id,
                "decision": "blocked",
                "blocked": True,
                "reason": _plan.block_reason,
            }
    except ImportError:
        pass

    # 3. Generate candidates (drift- and subsystem-aware)
    candidates = generate_patches_for_goal(
        goal=goal,
        diagnostics=subsystem_diagnostics,
        stability={"strict": strict_safety},
        max_candidates=max_candidates,
        exploration=tuned["exploration"],
    )

    scored_candidates = []

    # 4. Sandbox + 5. Score
    for candidate in candidates:
        sandbox_result = run_in_sandbox(candidate)
        scores = score_candidate(
            candidate=candidate,
            sandbox_result=sandbox_result,
            diagnostics=report.details,
        )
        stability = evaluate_stability(candidate)

        scored_candidates.append({
            "candidate": candidate,
            "sandbox": sandbox_result,
            "scores": scores,
            "stability": stability,
        })

    # 6. Select best
    if not scored_candidates:
        log_event("sho_cycle_no_candidates", {"cycle_id": cycle_id, "goal": goal})
        return {
            "cycle_id": cycle_id,
            "decision": "no_candidates",
            "reason": "patch generation produced no viable candidates",
        }

    best = max(
        scored_candidates,
        key=lambda c: c["scores"]["improvement_score"],
    )

    # 7. Compute final drift with real best candidate
    drift_report = compute_drift_report(
        current_decision={"best_candidate": best, "cycle_id": cycle_id},
        previous_decision=previous,
    )

    # 8. Save snapshots
    snapshot_id = save_version_snapshot(best["candidate"])
    cockpit_id = save_cockpit_snapshot({
        "cycle_id": cycle_id,
        "best_candidate": best,
        "drift": drift_report,
        "tuning": tuned,
        "timestamp": _timestamp(),
    })

    # 9. Log decision
    decision_record = {
        "cycle_id": cycle_id,
        "candidate_snapshot_id": snapshot_id,
        "cockpit_snapshot_id": cockpit_id,
        "best_candidate": best,
        "drift": drift_report,
        "tuning": tuned,
        "decision": "accepted",
        "timestamp": _timestamp(),
    }

    decision_path = _cockpit_path(f"decision-{cycle_id}.json")
    from knowledge._atomic_io import atomic_write_json
    atomic_write_json(Path(decision_path), decision_record)

    log_event("sho_cycle_complete", decision_record)

    return decision_record


def run_consistency_scan():
    return run_improvement_cycle(
        goal="consistency scan",
        max_iterations=1,
    )


def run_evolution_cycle():
    return run_improvement_cycle(
        goal="concept evolution",
        max_iterations=1,
    )
