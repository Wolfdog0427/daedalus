# runtime/tier3_runbooks.py
"""
Tier-3 runbooks.

A runbook is an ordered sequence of operator-defined steps that
orchestrate existing governed operations (profile switching, plan
execution, policy evaluation, adaptive insights, recommendation
application).  Runbooks introduce no new mutation pathways — every
step delegates to an existing, fully-governed function.

All execution is operator-triggered.  No automatic or scheduled
runbook execution.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_RUNBOOK_REGISTRY: List[Dict[str, Any]] = []

_VALID_STEP_TYPES = {
    "set_profile",
    "execute_plan",
    "evaluate_policies_once",
    "evaluate_policies_scheduled_once",
    "generate_adaptive_insights",
    "apply_recommendation",
}

_VALID_RUNBOOK_STATUSES = {"draft", "ready", "running", "completed", "failed"}


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_runbook(
    name: str,
    description: str,
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    errors: List[str] = []
    for i, step in enumerate(steps):
        stype = step.get("type", "")
        if stype not in _VALID_STEP_TYPES:
            errors.append(f"step {i}: unknown type '{stype}'")
        if stype == "set_profile" and not step.get("profile_id"):
            errors.append(f"step {i}: set_profile requires 'profile_id'")
        if stype == "execute_plan" and not step.get("plan_id"):
            errors.append(f"step {i}: execute_plan requires 'plan_id'")
        if stype == "apply_recommendation" and not step.get("insight_id"):
            errors.append(f"step {i}: apply_recommendation requires 'insight_id'")

    if errors:
        return {"error": True, "reasons": errors}

    runbook = {
        "runbook_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "steps": list(steps),
        "status": "draft",
        "step_results": [],
        "created_at": time.time(),
        "updated_at": time.time(),
        "last_executed_at": None,
    }
    _TIER3_RUNBOOK_REGISTRY.append(runbook)
    return runbook


def list_runbooks() -> List[Dict[str, Any]]:
    return list(_TIER3_RUNBOOK_REGISTRY)


def get_runbook(runbook_id: str) -> Optional[Dict[str, Any]]:
    for r in _TIER3_RUNBOOK_REGISTRY:
        if r["runbook_id"] == runbook_id:
            return r
    return None


def clear_tier3_runbooks() -> None:
    """Reset the runbook registry (for testing only)."""
    _TIER3_RUNBOOK_REGISTRY.clear()


# ------------------------------------------------------------------
# Step handlers
# ------------------------------------------------------------------

def _step_set_profile(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_profiles import activate_profile
    result = activate_profile(step["profile_id"])
    if result.get("activated"):
        return {"success": True, "detail": result}
    return {"success": False, "reason": result.get("reason", "activation failed")}


def _step_execute_plan(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_plans import execute_plan
    result = execute_plan(step["plan_id"])
    if result.get("executed"):
        ok = result.get("status") != "failed"
        return {"success": ok, "detail": result,
                "reason": None if ok else "plan execution had failures"}
    return {"success": False, "reason": result.get("reason", "plan execution failed")}


def _step_evaluate_policies_once(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_policies import evaluate_policies
    try:
        result = evaluate_policies()
        return {"success": True, "detail": result}
    except Exception as exc:
        return {"success": False, "reason": str(exc)}


def _step_evaluate_policies_scheduled_once(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_policies import evaluate_policies_scheduled
    try:
        result = evaluate_policies_scheduled()
        return {"success": True, "detail": result}
    except Exception as exc:
        return {"success": False, "reason": str(exc)}


def _step_generate_adaptive_insights(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_adaptive import generate_adaptive_insights
    try:
        result = generate_adaptive_insights()
        return {"success": True, "detail": result}
    except Exception as exc:
        return {"success": False, "reason": str(exc)}


def _step_apply_recommendation(step: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.tier3_adaptive_bridge import apply_recommendation
    try:
        result = apply_recommendation(step["insight_id"])
        if result.get("error") or result.get("applied") is False:
            return {"success": False,
                    "reason": result.get("reason", "apply failed")}
        return {"success": True, "detail": result}
    except Exception as exc:
        return {"success": False, "reason": str(exc)}


_STEP_HANDLERS = {
    "set_profile": _step_set_profile,
    "execute_plan": _step_execute_plan,
    "evaluate_policies_once": _step_evaluate_policies_once,
    "evaluate_policies_scheduled_once": _step_evaluate_policies_scheduled_once,
    "generate_adaptive_insights": _step_generate_adaptive_insights,
    "apply_recommendation": _step_apply_recommendation,
}


# ------------------------------------------------------------------
# Execution engine
# ------------------------------------------------------------------

def execute_runbook(runbook_id: str) -> Dict[str, Any]:
    """
    Execute all steps in a runbook in order, stopping on first failure.

    Returns a summary with per-step results.
    """
    runbook = get_runbook(runbook_id)
    if runbook is None:
        return {"executed": False, "reason": f"runbook '{runbook_id}' not found"}

    if runbook["status"] not in ("draft", "ready"):
        return {"executed": False,
                "reason": f"runbook status is '{runbook['status']}', must be 'draft' or 'ready'"}

    runbook["status"] = "running"
    runbook["updated_at"] = time.time()
    runbook["last_executed_at"] = time.time()

    steps = runbook["steps"]
    step_results: List[Dict[str, Any]] = []
    failed = False

    for i, step in enumerate(steps):
        if failed:
            step_results.append({
                "step_index": i,
                "type": step.get("type", "?"),
                "status": "skipped",
                "reason": "prior step failed",
            })
            continue

        stype = step.get("type", "")
        handler = _STEP_HANDLERS.get(stype)
        if handler is None:
            step_results.append({
                "step_index": i,
                "type": stype,
                "status": "failed",
                "reason": f"unknown step type '{stype}'",
            })
            failed = True
            continue

        try:
            result = handler(step)
        except Exception as exc:
            result = {"success": False, "reason": str(exc)}

        if result.get("success"):
            step_results.append({
                "step_index": i,
                "type": stype,
                "status": "success",
                "detail": result.get("detail"),
                "timestamp": time.time(),
            })
        else:
            step_results.append({
                "step_index": i,
                "type": stype,
                "status": "failed",
                "reason": result.get("reason", "unknown"),
                "timestamp": time.time(),
            })
            failed = True

    runbook["step_results"] = step_results
    runbook["status"] = "failed" if failed else "completed"
    runbook["updated_at"] = time.time()

    succeeded = sum(1 for r in step_results if r["status"] == "success")
    failed_count = sum(1 for r in step_results if r["status"] == "failed")
    skipped = sum(1 for r in step_results if r["status"] == "skipped")

    return {
        "executed": True,
        "runbook_id": runbook_id,
        "status": runbook["status"],
        "total_steps": len(steps),
        "succeeded": succeeded,
        "failed": failed_count,
        "skipped": skipped,
        "step_results": step_results,
    }
