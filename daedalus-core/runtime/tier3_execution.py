# runtime/tier3_execution.py
"""
Tier-3 execution harness.

Provides a supervised, envelope-gated execution path for approved
Tier-3 proposals.  Reversible action types perform real, governed
mutations and record old/new state in the reversible ledger.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_TIER3_EXECUTION_LOG: List[Dict[str, Any]] = []

_TIER3_DISPATCH_LOG: List[Dict[str, Any]] = []

_TIER3_REVERSIBLE_LEDGER: List[Dict[str, Any]] = []


def validate_proposal_for_execution(proposal: dict) -> Dict[str, Any]:
    """
    Check that a proposal is approved and the envelope allows execution.

    Never mutates anything.
    """
    pid = proposal.get("id", "?")

    if proposal.get("status") != "approved":
        return {
            "valid": False,
            "reason": f"proposal status is '{proposal.get('status')}', must be 'approved'",
            "proposal_id": pid,
        }

    from runtime.system_dashboard import get_maintenance_envelope_summary

    envelope = get_maintenance_envelope_summary()
    if envelope.get("summary") != "pass":
        return {
            "valid": False,
            "reason": f"envelope is '{envelope.get('summary')}', must be 'pass'",
            "proposal_id": pid,
        }

    return {"valid": True, "reason": "approved + envelope pass", "proposal_id": pid}


def sandbox_preview(proposal: dict) -> Dict[str, Any]:
    """Return a non-executable preview of what execution would do."""
    return {
        "proposal_id": proposal.get("id", "?"),
        "preview": f"This proposal would perform: {proposal.get('title', '?')}",
        "rationale": proposal.get("rationale", ""),
        "evidence": proposal.get("evidence", {}),
    }


# ------------------------------------------------------------------
# Phase 34: real, governed per-type handlers
# ------------------------------------------------------------------

def _handle_update_setting(payload: Dict[str, Any]) -> Dict[str, Any]:
    from runtime.system_settings import get_setting, set_setting

    key = payload.get("key", "")
    new_value = payload.get("new_value")

    try:
        old_value = get_setting(key)
    except KeyError:
        return {"handler": "update_setting", "applied": False,
                "reason": f"unknown setting '{key}'"}

    result = set_setting(key, new_value)
    if not result.get("updated"):
        return {"handler": "update_setting", "applied": False,
                "reason": result.get("reason", "validation failed")}

    return {
        "handler": "update_setting",
        "applied": True,
        "old_value": old_value,
        "new_value": new_value,
        "key": key,
    }


def _handle_retire_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = payload.get("action_name", "")
    tier = payload.get("tier")

    if tier == 1:
        from runtime.maintenance_actions import (
            demote_action_from_tier1, is_action_registered_tier1,
        )
        if not is_action_registered_tier1(name):
            return {"handler": "retire_action", "applied": False,
                    "reason": f"'{name}' not in Tier-1 registry"}
        result = demote_action_from_tier1(name)
        return {
            "handler": "retire_action",
            "applied": result.get("demoted", False),
            "old_state": "registered",
            "new_state": "demoted",
            "action_name": name,
            "tier": 1,
            "reason": result.get("reason", ""),
        }

    if tier == 2:
        from runtime.maintenance_actions import (
            retire_tier2_action, get_registered_tier2_actions,
        )
        found = any(a.get("name") == name for a in get_registered_tier2_actions())
        if not found:
            return {"handler": "retire_action", "applied": False,
                    "reason": f"'{name}' not in Tier-2 registry"}
        result = retire_tier2_action(name)
        return {
            "handler": "retire_action",
            "applied": result.get("retired", False),
            "old_state": "registered",
            "new_state": "retired",
            "action_name": name,
            "tier": 2,
            "reason": result.get("reason", ""),
        }

    return {"handler": "retire_action", "applied": False,
            "reason": f"unsupported tier {tier}"}


def _handle_replace_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    old_name = payload.get("old_action_name", "")
    new_action = payload.get("new_action", {})
    tier = payload.get("tier")

    if tier == 1:
        from runtime.maintenance_actions import (
            demote_action_from_tier1, register_tier1_action,
            is_action_registered_tier1,
        )
        if not is_action_registered_tier1(old_name):
            return {"handler": "replace_action", "applied": False,
                    "reason": f"'{old_name}' not in Tier-1 registry"}
        demote_result = demote_action_from_tier1(old_name)
        if not demote_result.get("demoted"):
            return {"handler": "replace_action", "applied": False,
                    "reason": f"demotion failed: {demote_result.get('reason', '?')}"}
        reg_result = register_tier1_action(new_action)
        return {
            "handler": "replace_action",
            "applied": reg_result.get("registered", False),
            "old_action_name": old_name,
            "new_action_name": new_action.get("name", "?"),
            "tier": 1,
            "reason": reg_result.get("reason", ""),
        }

    if tier == 2:
        from runtime.maintenance_actions import (
            retire_tier2_action, register_tier2_action,
            get_registered_tier2_actions,
        )
        found = any(a.get("name") == old_name for a in get_registered_tier2_actions())
        if not found:
            return {"handler": "replace_action", "applied": False,
                    "reason": f"'{old_name}' not in Tier-2 registry"}
        retire_tier2_action(old_name)
        reg_result = register_tier2_action(new_action)
        return {
            "handler": "replace_action",
            "applied": reg_result.get("registered", False),
            "old_action_name": old_name,
            "new_action_name": new_action.get("name", "?"),
            "tier": 2,
            "reason": reg_result.get("reason", ""),
        }

    return {"handler": "replace_action", "applied": False,
            "reason": f"unsupported tier {tier}"}


# ------------------------------------------------------------------
# Phase 35: migration engine
# ------------------------------------------------------------------

_TIER3_MIGRATION_LOG: List[Dict[str, Any]] = []

_MIGRATION_STEP_TYPES = {"set_setting", "retire_action", "replace_action", "note"}


def _execute_migration_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single migration step by delegating to the existing
    governed handlers.  Returns a result dict with status and details.
    """
    step_type = step.get("type", "")

    if step_type not in _MIGRATION_STEP_TYPES:
        return {"status": "failed", "reason": f"unknown step type '{step_type}'"}

    if step_type == "note":
        return {"status": "success", "note": step.get("message", "")}

    if step_type == "set_setting":
        result = _handle_update_setting({
            "key": step.get("key", ""),
            "new_value": step.get("new_value"),
        })
        if result.get("applied"):
            return {"status": "success", "detail": result}
        return {"status": "failed", "reason": result.get("reason", "unknown"),
                "detail": result}

    if step_type == "retire_action":
        result = _handle_retire_action({
            "action_name": step.get("action_name", ""),
            "tier": step.get("tier"),
        })
        if result.get("applied"):
            return {"status": "success", "detail": result}
        return {"status": "failed", "reason": result.get("reason", "unknown"),
                "detail": result}

    if step_type == "replace_action":
        result = _handle_replace_action({
            "old_action_name": step.get("old_action_name", ""),
            "new_action": step.get("new_action", {}),
            "tier": step.get("tier"),
        })
        if result.get("applied"):
            return {"status": "success", "detail": result}
        return {"status": "failed", "reason": result.get("reason", "unknown"),
                "detail": result}

    return {"status": "failed", "reason": "unreachable"}


def _handle_apply_migration(payload: Dict[str, Any]) -> Dict[str, Any]:
    migration_name = payload.get("migration_name", "?")
    steps = payload.get("migration_steps") or []

    record: Dict[str, Any] = {
        "migration_name": migration_name,
        "timestamp": time.time(),
        "total_steps": len(steps),
        "steps_executed": 0,
        "steps_succeeded": 0,
        "steps_failed": 0,
        "status": "running",
        "step_results": [],
    }

    for idx, step in enumerate(steps):
        try:
            result = _execute_migration_step(step)
        except Exception as exc:
            result = {"status": "failed", "reason": str(exc)}

        step_entry = {
            "index": idx,
            "type": step.get("type", "?"),
            "status": result["status"],
            "detail": result,
        }
        record["step_results"].append(step_entry)
        record["steps_executed"] += 1

        if result["status"] == "success":
            record["steps_succeeded"] += 1
        else:
            record["steps_failed"] += 1
            record["status"] = "failed"
            record["failure_reason"] = result.get("reason", "unknown")
            break

    if record["status"] == "running":
        record["status"] = "completed"

    _TIER3_MIGRATION_LOG.append(record)

    return {
        "handler": "apply_migration",
        "applied": record["status"] == "completed",
        "migration_name": migration_name,
        "migration_status": record["status"],
        "steps_executed": record["steps_executed"],
        "steps_succeeded": record["steps_succeeded"],
        "steps_failed": record["steps_failed"],
    }


def get_tier3_migration_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_TIER3_MIGRATION_LOG[-limit:])


def get_tier3_migration_status(migration_name: str) -> Optional[Dict[str, Any]]:
    """Return the most recent log entry for a given migration name."""
    for entry in reversed(_TIER3_MIGRATION_LOG):
        if entry.get("migration_name") == migration_name:
            return dict(entry)
    return None


def clear_tier3_migration_log() -> None:
    """Reset the migration log (for testing only)."""
    _TIER3_MIGRATION_LOG.clear()


# ------------------------------------------------------------------
# Phase 36: dry-run engine + structural diff
# ------------------------------------------------------------------

_TIER3_DRYRUN_LOG: List[Dict[str, Any]] = []


def _diff_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a structural diff for a single migration step without
    performing any mutation.  Returns a human-readable diff dict.
    """
    step_type = step.get("type", "")

    if step_type not in _MIGRATION_STEP_TYPES:
        return {"step_type": step_type, "status": "error",
                "reason": f"unknown step type '{step_type}'"}

    if step_type == "note":
        return {"step_type": "note", "status": "ok",
                "message": step.get("message", ""), "diff": None}

    if step_type == "set_setting":
        key = step.get("key", "")
        new_value = step.get("new_value")
        try:
            from runtime.system_settings import get_setting
            current = get_setting(key)
        except KeyError:
            return {"step_type": "set_setting", "status": "error",
                    "reason": f"unknown setting '{key}'"}
        return {
            "step_type": "set_setting",
            "status": "ok",
            "key": key,
            "diff": {"before": current, "after": new_value},
        }

    if step_type == "retire_action":
        name = step.get("action_name", "")
        tier = step.get("tier")
        exists = _check_action_exists(name, tier)
        if not exists:
            return {"step_type": "retire_action", "status": "error",
                    "reason": f"'{name}' not in Tier-{tier} registry"}
        return {
            "step_type": "retire_action",
            "status": "ok",
            "action_name": name,
            "tier": tier,
            "diff": {"before": "registered", "after": "removed"},
        }

    if step_type == "replace_action":
        old_name = step.get("old_action_name", "")
        new_action = step.get("new_action", {})
        tier = step.get("tier")
        exists = _check_action_exists(old_name, tier)
        if not exists:
            return {"step_type": "replace_action", "status": "error",
                    "reason": f"'{old_name}' not in Tier-{tier} registry"}
        return {
            "step_type": "replace_action",
            "status": "ok",
            "old_action_name": old_name,
            "new_action_name": new_action.get("name", "?"),
            "tier": tier,
            "diff": {"before": old_name, "after": new_action.get("name", "?")},
        }

    return {"step_type": step_type, "status": "error", "reason": "unreachable"}


def _check_action_exists(name: str, tier: Any) -> bool:
    """Read-only check for action existence in a tier registry."""
    if tier == 1:
        from runtime.maintenance_actions import is_action_registered_tier1
        return is_action_registered_tier1(name)
    if tier == 2:
        from runtime.maintenance_actions import get_registered_tier2_actions
        return any(a.get("name") == name for a in get_registered_tier2_actions())
    return False


def dryrun_migration(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a migration without performing any mutations.

    Returns a structured dry-run result with per-step diffs and
    an overall pass/fail verdict.
    """
    migration_name = payload.get("migration_name", "?")
    steps = payload.get("migration_steps") or []

    step_diffs: List[Dict[str, Any]] = []
    all_ok = True

    for idx, step in enumerate(steps):
        try:
            diff = _diff_step(step)
        except Exception as exc:
            diff = {"step_type": step.get("type", "?"), "status": "error",
                    "reason": str(exc)}

        step_diffs.append({"index": idx, **diff})
        if diff.get("status") != "ok":
            all_ok = False
            break  # stop on first predicted failure

    result = {
        "migration_name": migration_name,
        "timestamp": time.time(),
        "total_steps": len(steps),
        "steps_evaluated": len(step_diffs),
        "status": "pass" if all_ok else "fail",
        "step_diffs": step_diffs,
    }
    _TIER3_DRYRUN_LOG.append(result)
    return result


def get_tier3_dryrun_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_TIER3_DRYRUN_LOG[-limit:])


def get_dryrun_for_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent dry-run result attached to a proposal id."""
    for entry in reversed(_TIER3_DRYRUN_LOG):
        if entry.get("proposal_id") == proposal_id:
            return dict(entry)
    return None


def clear_tier3_dryrun_log() -> None:
    """Reset the dry-run log (for testing only)."""
    _TIER3_DRYRUN_LOG.clear()


_HANDLER_MAP: Dict[str, Any] = {
    "update_setting": _handle_update_setting,
    "retire_action": _handle_retire_action,
    "replace_action": _handle_replace_action,
    "apply_migration": _handle_apply_migration,
}


# ------------------------------------------------------------------
# Reversible ledger
# ------------------------------------------------------------------

def _record_ledger_entry(
    proposal_id: str,
    action_type: str,
    old_values: Any,
    new_values: Any,
    reversible: bool,
) -> None:
    _TIER3_REVERSIBLE_LEDGER.append({
        "proposal_id": proposal_id,
        "action_type": action_type,
        "old_values": old_values,
        "new_values": new_values,
        "reversible": reversible,
        "timestamp": time.time(),
    })


def get_tier3_reversible_ledger(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_TIER3_REVERSIBLE_LEDGER[-limit:])


def clear_tier3_reversible_ledger() -> None:
    """Reset the ledger (for testing only)."""
    _TIER3_REVERSIBLE_LEDGER.clear()


# ------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------

def dispatch_tier3_action(
    action_type: str,
    payload: Dict[str, Any],
    reversible: bool,
    proposal_id: str = "?",
) -> Dict[str, Any]:
    """
    Route a typed action to its handler after payload validation.

    Reversible actions that succeed are recorded in the ledger.
    """
    from runtime.tier3_actions import validate_tier3_payload

    val = validate_tier3_payload(action_type, payload)
    if not val["valid"]:
        return {"dispatched": False, "reason": val["reason"], "action_type": action_type}

    handler = _HANDLER_MAP.get(action_type)
    if handler is None:
        return {
            "dispatched": False,
            "reason": f"no handler registered for '{action_type}'",
            "action_type": action_type,
        }

    handler_result = handler(payload)

    now = time.time()
    applied = handler_result.get("applied", False)
    note = "action applied" if applied else "handler invoked (not applied)"

    entry = {
        "action_type": action_type,
        "payload": payload,
        "reversible": reversible,
        "handler_result": handler_result,
        "timestamp": now,
        "note": note,
    }
    _TIER3_DISPATCH_LOG.append(entry)

    if applied and reversible:
        old_vals = {k: handler_result[k] for k in handler_result
                    if k.startswith("old_")}
        new_vals = {k: handler_result[k] for k in handler_result
                    if k.startswith("new_") or k == "key"}
        _record_ledger_entry(proposal_id, action_type, old_vals, new_vals, True)
    elif applied and not reversible:
        _record_ledger_entry(proposal_id, action_type, {}, {}, False)

    return {"dispatched": True, **entry}


def get_tier3_dispatch_log() -> List[Dict[str, Any]]:
    return list(_TIER3_DISPATCH_LOG)


def get_last_tier3_dispatch() -> Optional[Dict[str, Any]]:
    return dict(_TIER3_DISPATCH_LOG[-1]) if _TIER3_DISPATCH_LOG else None


def clear_tier3_dispatch_log() -> None:
    """Reset the dispatch log (for testing only)."""
    _TIER3_DISPATCH_LOG.clear()


# ------------------------------------------------------------------
# Execution entry point
# ------------------------------------------------------------------

def execute_tier3_proposal(proposal: dict) -> Dict[str, Any]:
    """
    Execute an approved proposal.

    For typed proposals, routes through the dispatcher which calls real
    governed handlers.  Untyped proposals are logged without dispatch.
    Respects active profile feature flags.
    """
    now = time.time()

    action_type = proposal.get("action_type")

    if action_type == "apply_migration":
        try:
            from runtime.tier3_env_guardrails import check_migration_execution
            gr = check_migration_execution(proposal.get("id", ""))
            if not gr.get("allowed"):
                reasons = gr.get("blocking_reasons", [])
                return {
                    "executed": False,
                    "proposal_id": proposal.get("id", "?"),
                    "reason": "; ".join(reasons) if reasons
                    else "blocked by guardrail",
                    "timestamp": now,
                }
        except Exception:
            pass

        try:
            from runtime.tier3_profiles import get_feature_flag
            if not get_feature_flag("allow_migrations"):
                return {
                    "executed": False,
                    "proposal_id": proposal.get("id", "?"),
                    "reason": "blocked by profile flag: allow_migrations=False",
                    "timestamp": now,
                }
        except Exception:
            pass

    dispatch_result = None
    if action_type:
        dispatch_result = dispatch_tier3_action(
            action_type,
            proposal.get("payload", {}),
            proposal.get("reversible", False),
            proposal.get("id", "?"),
        )

    entry = {
        "proposal_id": proposal.get("id", "?"),
        "title": proposal.get("title", "?"),
        "timestamp": now,
        "action_type": action_type,
        "dispatch_result": dispatch_result,
        "note": "Tier-3 execution harness invoked",
    }
    _TIER3_EXECUTION_LOG.append(entry)
    return {"executed": True, **entry}


def get_tier3_execution_log() -> List[Dict[str, Any]]:
    return list(_TIER3_EXECUTION_LOG)


def clear_tier3_execution_log() -> None:
    """Reset the log (for testing only)."""
    _TIER3_EXECUTION_LOG.clear()
