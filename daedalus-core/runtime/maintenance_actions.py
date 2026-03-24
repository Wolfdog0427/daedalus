# runtime/maintenance_actions.py
"""
Maintenance action scaffolding (governed, non-autonomous).

Provides pure-data helpers for defining, validating, and previewing
maintenance actions. No real maintenance is performed — every function
returns descriptive structures only.
"""

from __future__ import annotations

from typing import Any, Dict, List


def define_maintenance_action(
    name: str,
    description: str,
    steps: List[str],
) -> Dict[str, Any]:
    """Return a structured action definition. Pure data, no execution."""
    return {
        "name": name,
        "description": description,
        "steps": list(steps),
    }


def validate_maintenance_action(
    action: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check whether *action* is allowed under the current maintenance *envelope*.

    Allowed only when ``envelope["summary"] == "pass"``.
    """
    summary = envelope.get("summary", "fail")
    allowed = summary == "pass"
    reasons: List[str] = []
    if not allowed:
        reasons.append(f"envelope summary is '{summary}' (must be 'pass')")
        reasons.extend(envelope.get("reasons") or [])
    return {
        "action": action,
        "envelope_summary": summary,
        "allowed": allowed,
        "reasons": reasons,
    }


def dry_run_maintenance_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Describe what *action* would do without performing it."""
    return {
        "action": action,
        "dry_run": True,
        "steps": list(action.get("steps") or []),
        "note": "This is a dry-run only. No operations performed.",
    }


def prepare_maintenance_execution_plan(action: Dict[str, Any]) -> Dict[str, Any]:
    """Build a pending execution plan for *action*. No operations performed."""
    return {
        "action": action,
        "plan": [{"step": s, "status": "pending"} for s in action.get("steps") or []],
        "note": "Execution plan only. No operations performed.",
    }


# ------------------------------------------------------------
# Phase 12: governed execution engine (in-memory, reversible)
# ------------------------------------------------------------


def _copy_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-enough copy so the caller's plan dict is never mutated."""
    return {
        "action": plan.get("action"),
        "plan": [dict(entry) for entry in plan.get("plan") or []],
        "note": plan.get("note", ""),
    }


def execute_maintenance_plan_step(plan: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Simulate executing a single step (pending → executing → completed).

    Returns a *new* plan dict. No real maintenance is performed.
    """
    new = _copy_plan(plan)
    steps = new["plan"]
    if 0 <= index < len(steps):
        steps[index] = dict(steps[index], status="completed")
    new["note"] = "Simulated execution. No real operations performed."
    return new


def execute_maintenance_plan_all(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate executing every pending step in order.

    Returns a *new* plan dict with all steps marked completed.
    """
    current = plan
    for i in range(len((plan.get("plan") or []))):
        current = execute_maintenance_plan_step(current, i)
    return current


def rollback_maintenance_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate rollback: completed/executing → rolled_back; pending stays pending.

    Returns a *new* plan dict. No real rollback is performed.
    """
    new = _copy_plan(plan)
    for entry in new["plan"]:
        if entry["status"] in ("completed", "executing"):
            entry["status"] = "rolled_back"
    new["note"] = "Simulated rollback. No real operations performed."
    return new


# ------------------------------------------------------------
# Phase 13: real, governed maintenance operations
#
# All operations target only the in-memory sandbox below.
# Nothing touches subsystems, persistence, or telemetry.
# ------------------------------------------------------------

_MAINTENANCE_SANDBOX: Dict[str, Any] = {}
_SANDBOX_SNAPSHOT: Dict[str, Any] = {}


def _snapshot_sandbox() -> None:
    """Capture current sandbox state for rollback."""
    _SANDBOX_SNAPSHOT.clear()
    _SANDBOX_SNAPSHOT.update({k: v for k, v in _MAINTENANCE_SANDBOX.items()})


def _restore_sandbox() -> None:
    """Restore sandbox to the last snapshot."""
    _MAINTENANCE_SANDBOX.clear()
    _MAINTENANCE_SANDBOX.update({k: v for k, v in _SANDBOX_SNAPSHOT.items()})


def get_sandbox() -> Dict[str, Any]:
    """Read-only view of the maintenance sandbox (for inspection)."""
    return dict(_MAINTENANCE_SANDBOX)


def perform_maintenance_operation(
    action: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute *action* against the in-memory sandbox.

    The operation is gated by the maintenance envelope: it only proceeds
    when ``envelope["summary"] == "pass"``. All mutations target
    ``_MAINTENANCE_SANDBOX`` exclusively — no subsystems, persistence,
    or telemetry are touched.
    """
    validation = validate_maintenance_action(action, envelope)
    if not validation["allowed"]:
        return {
            "action": action,
            "performed": False,
            "result": "blocked by envelope",
            "steps": [],
            "rollback_available": False,
            "reasons": validation["reasons"],
        }

    _snapshot_sandbox()

    steps_done: List[Dict[str, str]] = []
    for step_name in action.get("steps") or []:
        _MAINTENANCE_SANDBOX[f"step:{step_name}"] = "completed"
        steps_done.append({"step": step_name, "status": "completed"})

    _MAINTENANCE_SANDBOX["_last_action"] = action.get("name", "unknown")

    return {
        "action": action,
        "performed": True,
        "result": "completed in sandbox",
        "steps": steps_done,
        "rollback_available": True,
    }


def rollback_maintenance_operation(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reverse the effects of :func:`perform_maintenance_operation`.

    Restores ``_MAINTENANCE_SANDBOX`` to its pre-operation snapshot.
    """
    if not result.get("rollback_available"):
        return {
            "rolled_back": False,
            "restored_state": "no rollback available",
        }

    _restore_sandbox()

    return {
        "rolled_back": True,
        "restored_state": "sandbox restored to pre-operation snapshot",
    }


# ------------------------------------------------------------
# Phase 14: action classification & autonomy eligibility
# ------------------------------------------------------------

_HIGH_RISK_KEYWORDS = frozenset([
    "delete", "drop", "remove permanently", "truncate",
    "migrate", "upgrade", "downgrade", "deploy",
    "modify subsystem", "patch subsystem",
])


def classify_maintenance_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify *action* into tier1 / tier2 / tier3.

    Purely descriptive — no autonomy, no execution.
      tier1 – safe, reversible, sandbox-only, ≤ 5 steps
      tier2 – reversible but > 5 steps or needs user context
      tier3 – irreversible, structural, or subsystem-affecting
    """
    steps = action.get("steps") or []
    name_lower = (action.get("name") or "").lower()
    desc_lower = (action.get("description") or "").lower()
    combined = f"{name_lower} {desc_lower} {' '.join(s.lower() for s in steps)}"

    if any(kw in combined for kw in _HIGH_RISK_KEYWORDS):
        return {
            "action": action,
            "class": "tier3",
            "reason": "contains high-risk or irreversible keywords",
        }

    if len(steps) > 5:
        return {
            "action": action,
            "class": "tier2",
            "reason": f"step count ({len(steps)}) exceeds tier1 limit of 5",
        }

    return {
        "action": action,
        "class": "tier1",
        "reason": "safe, reversible, sandbox-only, 5 steps or fewer",
    }


def check_autonomy_eligibility(
    action: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Determine whether *action* would be eligible for future automatic execution.

    Eligible only when: tier1 AND envelope pass AND validation allowed.
    No autonomy is performed — this is classification only.
    """
    classification = classify_maintenance_action(action)
    validation = validate_maintenance_action(action, envelope)

    reasons: List[str] = []
    eligible = True

    if classification["class"] != "tier1":
        eligible = False
        reasons.append(f"action class is {classification['class']} (must be tier1)")

    if not validation["allowed"]:
        eligible = False
        reasons.append("validation not allowed under current envelope")
        reasons.extend(validation["reasons"])

    if eligible:
        reasons.append("all eligibility criteria met")

    return {
        "eligible": eligible,
        "class": classification["class"],
        "reasons": reasons,
    }


# ------------------------------------------------------------
# Phase 15: autonomy framework (disabled by default)
# ------------------------------------------------------------

_AUTONOMY_SETTINGS: Dict[str, Any] = {
    "tier1_enabled": False,
}


def get_autonomy_settings() -> Dict[str, Any]:
    """Return a copy of the current in-memory autonomy settings."""
    return dict(_AUTONOMY_SETTINGS)


def set_autonomy_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Merge *settings* into in-memory autonomy settings (non-persistent)."""
    _AUTONOMY_SETTINGS.update(settings)
    return dict(_AUTONOMY_SETTINGS)


def evaluate_tier1_autonomy(
    action: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Determine whether *action* should be auto-executed under Tier-1 autonomy.

    Returns a verdict dict — no execution is performed.
    should_auto_execute is True only when autonomy is enabled, the action
    is classified as tier1, the envelope passes, and validation allows it.
    """
    autonomy_enabled = _AUTONOMY_SETTINGS.get("tier1_enabled", False)
    eligibility = check_autonomy_eligibility(action, envelope)
    eligible = eligibility["eligible"]

    should_auto_execute = autonomy_enabled and eligible

    reasons: List[str] = list(eligibility["reasons"])
    if not autonomy_enabled:
        reasons.insert(0, "tier1 autonomy is disabled")

    return {
        "action": action,
        "eligible": eligible,
        "autonomy_enabled": autonomy_enabled,
        "should_auto_execute": should_auto_execute,
        "reasons": reasons,
    }


# ------------------------------------------------------------
# Phase 16: tier-1 autonomy execution path (user-controlled)
# ------------------------------------------------------------

def run_tier1_autonomy_cycle(
    actions: List[Dict[str, Any]],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute eligible Tier-1 actions in order, sandbox-only.

    Must be called explicitly by an operator — never scheduled, never
    triggered automatically, never run in the background.
    """
    autonomy_enabled = _AUTONOMY_SETTINGS.get("tier1_enabled", False)
    executed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for action in actions:
        verdict = evaluate_tier1_autonomy(action, envelope)

        if verdict["should_auto_execute"]:
            result = perform_maintenance_operation(action, envelope)
            executed.append({
                "action": action,
                "verdict": verdict,
                "result": result,
            })
        else:
            skipped.append({
                "action": action,
                "verdict": verdict,
            })

    return {
        "autonomy_enabled": autonomy_enabled,
        "executed": executed,
        "skipped": skipped,
    }


# ------------------------------------------------------------
# Phase 17: autonomy loop (disabled, operator-controlled)
# ------------------------------------------------------------

def run_autonomy_loop(
    actions: List[Dict[str, Any]],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate all actions and produce a full autonomy report.

    Read-only — no execution, no sandbox mutation.  Must be called
    explicitly by an operator; never scheduled or backgrounded.
    """
    autonomy_enabled = _AUTONOMY_SETTINGS.get("tier1_enabled", False)
    action_reports: List[Dict[str, Any]] = []
    would_execute: List[str] = []
    would_skip: List[str] = []

    for action in actions:
        classification = classify_maintenance_action(action)
        eligibility = check_autonomy_eligibility(action, envelope)
        verdict = evaluate_tier1_autonomy(action, envelope)

        name = action.get("name", "?")
        if verdict["should_auto_execute"]:
            would_execute.append(name)
        else:
            would_skip.append(name)

        action_reports.append({
            "action": action,
            "classification": classification,
            "eligibility": eligibility,
            "verdict": verdict,
        })

    return {
        "autonomy_enabled": autonomy_enabled,
        "envelope_summary": envelope.get("summary", "unknown"),
        "actions": action_reports,
        "would_execute": would_execute,
        "would_skip": would_skip,
    }


# ------------------------------------------------------------
# Phase 19: Tier-1 action registry & dynamic discovery
# ------------------------------------------------------------

_TIER1_ACTION_REGISTRY: List[Dict[str, Any]] = []

_BUILTIN_TIER1_ACTIONS: List[Dict[str, Any]] = [
    {
        "name": "clear_temp_cache",
        "description": "Clear temporary sandbox cache entries",
        "steps": ["snapshot", "clear_entries", "verify"],
    },
    {
        "name": "compact_telemetry_buffer",
        "description": "Compact in-memory telemetry buffer metadata",
        "steps": ["scan", "compact", "verify"],
    },
    {
        "name": "refresh_health_snapshot",
        "description": "Refresh cached health summary in sandbox",
        "steps": ["collect", "store", "verify"],
    },
]


def register_tier1_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and register *action* into the Tier-1 registry.

    Rejects anything that doesn't classify as tier1.  No execution,
    no subsystem mutation — just appends to the in-memory list.
    """
    classification = classify_maintenance_action(action)

    if classification["class"] != "tier1":
        return {
            "registered": False,
            "reason": f"action classifies as {classification['class']}, not tier1: "
                      f"{classification['reason']}",
            "action": action,
        }

    existing_names = {a.get("name") for a in _TIER1_ACTION_REGISTRY}
    name = action.get("name", "")
    if name in existing_names:
        return {
            "registered": False,
            "reason": f"action '{name}' is already registered",
            "action": action,
        }

    _TIER1_ACTION_REGISTRY.append(dict(action))
    return {
        "registered": True,
        "reason": "accepted as tier1",
        "action": action,
    }


def get_registered_tier1_actions() -> List[Dict[str, Any]]:
    """Return a copy of the Tier-1 action registry."""
    return [dict(a) for a in _TIER1_ACTION_REGISTRY]


def clear_tier1_action_registry() -> None:
    """Clear the registry (for testing / reset)."""
    _TIER1_ACTION_REGISTRY.clear()


def seed_default_tier1_actions() -> List[Dict[str, Any]]:
    """Register the built-in Tier-1 actions if the registry is empty."""
    if not _TIER1_ACTION_REGISTRY:
        for spec in _BUILTIN_TIER1_ACTIONS:
            register_tier1_action(define_maintenance_action(**spec))
    return get_registered_tier1_actions()


def get_default_tier1_actions() -> List[Dict[str, Any]]:
    """Return registered Tier-1 actions, seeding built-ins if empty."""
    if not _TIER1_ACTION_REGISTRY:
        seed_default_tier1_actions()
    return get_registered_tier1_actions()


# ------------------------------------------------------------
# Phase 20: Tier-1 action promotion & demotion
# ------------------------------------------------------------

import time as _time

_TIER1_PROMOTION_EVENTS: List[Dict[str, Any]] = []
_TIER1_DEMOTION_EVENTS: List[Dict[str, Any]] = []


def _record_promotion_event(
    action_name: str, success: bool, reason: str,
) -> None:
    _TIER1_PROMOTION_EVENTS.append({
        "timestamp": _time.time(),
        "action_name": action_name,
        "result": "success" if success else "failure",
        "reason": reason,
    })


def _record_demotion_event(
    action_name: str, success: bool, reason: str,
) -> None:
    _TIER1_DEMOTION_EVENTS.append({
        "timestamp": _time.time(),
        "action_name": action_name,
        "result": "success" if success else "failure",
        "reason": reason,
    })


def get_tier1_promotion_events() -> List[Dict[str, Any]]:
    return list(_TIER1_PROMOTION_EVENTS)


def get_tier1_demotion_events() -> List[Dict[str, Any]]:
    return list(_TIER1_DEMOTION_EVENTS)


def is_action_registered_tier1(name: str) -> bool:
    return any(a.get("name") == name for a in _TIER1_ACTION_REGISTRY)


def promote_action_to_tier1(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and promote *action* into the Tier-1 registry.

    Rejects anything that doesn't classify as tier1 or is already
    registered.  No execution — only data validation and registration.
    """
    name = action.get("name", "?")
    classification = classify_maintenance_action(action)

    if classification["class"] != "tier1":
        reason = (f"action classifies as {classification['class']}, not tier1: "
                  f"{classification['reason']}")
        _record_promotion_event(name, False, reason)
        return {"promoted": False, "reason": reason, "action": action}

    reg_result = register_tier1_action(action)
    if not reg_result["registered"]:
        _record_promotion_event(name, False, reg_result["reason"])
        return {
            "promoted": False,
            "reason": reg_result["reason"],
            "action": action,
        }

    _record_promotion_event(name, True, "promoted to tier1")
    return {"promoted": True, "reason": "promoted to tier1", "action": action}


def demote_action_from_tier1(name: str) -> Dict[str, Any]:
    """
    Remove the action named *name* from the Tier-1 registry.

    No execution, no subsystem mutation.
    """
    idx = next(
        (i for i, a in enumerate(_TIER1_ACTION_REGISTRY) if a.get("name") == name),
        None,
    )

    if idx is None:
        reason = f"action '{name}' not found in tier1 registry"
        _record_demotion_event(name, False, reason)
        return {"demoted": False, "reason": reason, "name": name}

    _TIER1_ACTION_REGISTRY.pop(idx)
    _record_demotion_event(name, True, "demoted from tier1")
    return {"demoted": True, "reason": "demoted from tier1", "name": name}


# ------------------------------------------------------------
# Phase 21: Tier-2 action registry + supervised execution
# ------------------------------------------------------------

_TIER2_ACTION_REGISTRY: List[Dict[str, Any]] = []
_TIER2_PENDING_QUEUE: List[Dict[str, Any]] = []
_TIER2_EXECUTION_EVENTS: List[Dict[str, Any]] = []


def register_tier2_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and register *action* into the Tier-2 registry.

    Rejects anything that doesn't classify as tier2.
    """
    classification = classify_maintenance_action(action)

    if classification["class"] != "tier2":
        return {
            "registered": False,
            "reason": f"action classifies as {classification['class']}, not tier2: "
                      f"{classification['reason']}",
            "action": action,
        }

    name = action.get("name", "")
    if any(a.get("name") == name for a in _TIER2_ACTION_REGISTRY):
        return {
            "registered": False,
            "reason": f"action '{name}' is already registered as tier2",
            "action": action,
        }

    _TIER2_ACTION_REGISTRY.append(dict(action))
    return {"registered": True, "reason": "accepted as tier2", "action": action}


def get_registered_tier2_actions() -> List[Dict[str, Any]]:
    return [dict(a) for a in _TIER2_ACTION_REGISTRY]


def clear_tier2_action_registry() -> None:
    _TIER2_ACTION_REGISTRY.clear()
    _TIER2_PENDING_QUEUE.clear()


# -- pending queue --

def queue_tier2_action_for_review(name: str) -> Dict[str, Any]:
    """
    Move a registered Tier-2 action into the pending-review queue.

    The action stays in the queue until an operator explicitly executes
    or removes it. No autonomous execution.
    """
    action = next(
        (a for a in _TIER2_ACTION_REGISTRY if a.get("name") == name), None,
    )
    if action is None:
        return {
            "queued": False,
            "reason": f"action '{name}' not found in tier2 registry",
            "name": name,
        }

    if any(a.get("name") == name for a in _TIER2_PENDING_QUEUE):
        return {
            "queued": False,
            "reason": f"action '{name}' is already in the pending queue",
            "name": name,
        }

    _TIER2_PENDING_QUEUE.append(dict(action))
    return {"queued": True, "reason": "queued for operator review", "name": name}


def get_tier2_pending_queue() -> List[Dict[str, Any]]:
    return [dict(a) for a in _TIER2_PENDING_QUEUE]


# -- supervised execution --

def execute_tier2_action(
    name: str, envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a Tier-2 action from the pending queue, after full validation.

    Must be explicitly called by an operator — never automatic.
    """
    idx = next(
        (i for i, a in enumerate(_TIER2_PENDING_QUEUE) if a.get("name") == name),
        None,
    )
    if idx is None:
        reason = f"action '{name}' not in pending queue"
        _TIER2_EXECUTION_EVENTS.append({
            "timestamp": _time.time(), "action_name": name,
            "result": "failure", "reason": reason,
        })
        return {"executed": False, "reason": reason, "action": None, "result": None}

    action = _TIER2_PENDING_QUEUE[idx]

    classification = classify_maintenance_action(action)
    if classification["class"] != "tier2":
        reason = f"reclassified as {classification['class']}, refusing execution"
        _TIER2_EXECUTION_EVENTS.append({
            "timestamp": _time.time(), "action_name": name,
            "result": "failure", "reason": reason,
        })
        return {"executed": False, "reason": reason, "action": action, "result": None}

    if envelope.get("summary") != "pass":
        reason = f"envelope summary is '{envelope.get('summary')}' (must be 'pass')"
        _TIER2_EXECUTION_EVENTS.append({
            "timestamp": _time.time(), "action_name": name,
            "result": "failure", "reason": reason,
        })
        return {"executed": False, "reason": reason, "action": action, "result": None}

    op_result = perform_maintenance_operation(action, envelope)
    _TIER2_PENDING_QUEUE.pop(idx)

    _TIER2_EXECUTION_EVENTS.append({
        "timestamp": _time.time(), "action_name": name,
        "result": "success", "reason": "executed in sandbox",
    })
    return {
        "executed": True,
        "reason": "executed in sandbox",
        "action": action,
        "result": op_result,
    }


def get_tier2_execution_events() -> List[Dict[str, Any]]:
    return list(_TIER2_EXECUTION_EVENTS)


# ------------------------------------------------------------
# Phase 22: Tier-2 -> Tier-1 promotion eligibility
# ------------------------------------------------------------

TIER2_PROMOTION_SUCCESS_THRESHOLD: int = 5


def get_tier2_promotion_candidates() -> List[Dict[str, Any]]:
    """
    Analyse every registered Tier-2 action's execution history and
    return a recommendation signal for each.

    Read-only — no promotion or execution is performed.
    """
    candidates: List[Dict[str, Any]] = []

    for action in _TIER2_ACTION_REGISTRY:
        name = action.get("name", "?")
        events = [
            e for e in _TIER2_EXECUTION_EVENTS if e.get("action_name") == name
        ]

        total_runs = len(events)
        successful_runs = sum(1 for e in events if e.get("result") == "success")
        failed_runs = sum(1 for e in events if e.get("result") == "failure")
        last_result = events[-1]["result"] if events else "never_executed"

        if total_runs == 0:
            recommendation = "insufficient_data"
        elif failed_runs > 0:
            recommendation = "not_recommended"
        elif successful_runs >= TIER2_PROMOTION_SUCCESS_THRESHOLD:
            recommendation = "strong_candidate"
        else:
            recommendation = "weak_candidate"

        candidates.append({
            "name": name,
            "classification": "tier2",
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "last_result": last_result,
            "recommendation": recommendation,
        })

    return candidates


# ------------------------------------------------------------
# Phase 23: Tier-2 lifecycle controls
# ------------------------------------------------------------

_TIER2_LIFECYCLE_LOG: List[Dict[str, Any]] = []


def retire_tier2_action(name: str) -> Dict[str, Any]:
    """
    Remove a Tier-2 action from registry and pending queue.

    Execution history is preserved for audit purposes.
    """
    idx = next(
        (i for i, a in enumerate(_TIER2_ACTION_REGISTRY) if a.get("name") == name),
        None,
    )
    if idx is None:
        reason = f"action '{name}' not found in tier2 registry"
        _TIER2_LIFECYCLE_LOG.append({
            "timestamp": _time.time(), "operation": "retire",
            "action_name": name, "result": "failure", "reason": reason,
        })
        return {"retired": False, "reason": reason, "name": name}

    _TIER2_ACTION_REGISTRY.pop(idx)

    pq_idx = next(
        (i for i, a in enumerate(_TIER2_PENDING_QUEUE) if a.get("name") == name),
        None,
    )
    if pq_idx is not None:
        _TIER2_PENDING_QUEUE.pop(pq_idx)

    reason = "retired from tier2 registry"
    _TIER2_LIFECYCLE_LOG.append({
        "timestamp": _time.time(), "operation": "retire",
        "action_name": name, "result": "success", "reason": reason,
    })
    return {"retired": True, "reason": reason, "name": name}


def reset_tier2_action_history(name: str) -> Dict[str, Any]:
    """Remove all execution events for a specific Tier-2 action."""
    before = len(_TIER2_EXECUTION_EVENTS)
    _TIER2_EXECUTION_EVENTS[:] = [
        e for e in _TIER2_EXECUTION_EVENTS if e.get("action_name") != name
    ]
    removed = before - len(_TIER2_EXECUTION_EVENTS)

    if removed == 0:
        reason = f"no events found for '{name}'"
        _TIER2_LIFECYCLE_LOG.append({
            "timestamp": _time.time(), "operation": "reset_history",
            "action_name": name, "result": "failure", "reason": reason,
        })
        return {"reset": False, "reason": reason, "name": name}

    reason = f"cleared {removed} events for '{name}'"
    _TIER2_LIFECYCLE_LOG.append({
        "timestamp": _time.time(), "operation": "reset_history",
        "action_name": name, "result": "success", "reason": reason,
    })
    return {"reset": True, "reason": reason, "name": name}


def reset_all_tier2_history() -> Dict[str, Any]:
    """Clear all Tier-2 execution events. Registries are unchanged."""
    count = len(_TIER2_EXECUTION_EVENTS)
    _TIER2_EXECUTION_EVENTS.clear()

    reason = f"all tier2 history cleared ({count} events)"
    _TIER2_LIFECYCLE_LOG.append({
        "timestamp": _time.time(), "operation": "reset_all_history",
        "action_name": "*", "result": "success", "reason": reason,
    })
    return {"reset": True, "reason": reason}


def recompute_tier2_promotion_candidates() -> List[Dict[str, Any]]:
    """Re-evaluate promotion candidates (convenience wrapper)."""
    return get_tier2_promotion_candidates()


def get_tier2_lifecycle_log() -> List[Dict[str, Any]]:
    return list(_TIER2_LIFECYCLE_LOG)
