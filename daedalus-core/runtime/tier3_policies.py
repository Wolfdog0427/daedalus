# runtime/tier3_policies.py
"""
Tier-3 policy engine.

Policies define condition/action pairs that automatically generate
Tier-3 proposals or execution plans when their conditions are met.
Policies NEVER execute proposals or plans — they only create them.
Evaluation is operator-triggered only; no background or scheduled runs.

Phase 39 adds scheduling metadata (intervals, time windows, rate limits)
and a scheduled evaluation path that respects them.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_POLICY_REGISTRY: List[Dict[str, Any]] = []

_TIER3_POLICY_EVAL_LOG: List[Dict[str, Any]] = []

_SUPPORTED_CONDITION_TYPES = {"setting_equals", "drift_above", "proposal_count"}

_SUPPORTED_ACTION_TYPES = {"create_typed_proposal", "create_execution_plan"}


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_policy(
    name: str,
    description: str,
    trigger_conditions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    enabled: bool = True,
    evaluation_interval_seconds: Optional[int] = None,
    allowed_windows: Optional[List[Dict[str, str]]] = None,
    rate_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a new policy and add it to the registry.

    Returns the policy dict, or a dict with ``"error"`` if validation
    fails.
    """
    errors: List[str] = []

    for idx, cond in enumerate(trigger_conditions):
        ctype = cond.get("type", "")
        if ctype not in _SUPPORTED_CONDITION_TYPES:
            errors.append(f"condition[{idx}]: unknown type '{ctype}'")

    for idx, act in enumerate(actions):
        atype = act.get("type", "")
        if atype not in _SUPPORTED_ACTION_TYPES:
            errors.append(f"action[{idx}]: unknown type '{atype}'")

    if errors:
        return {"error": True, "reasons": errors}

    policy = {
        "policy_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "trigger_conditions": trigger_conditions,
        "actions": actions,
        "enabled": enabled,
        "created_at": time.time(),
        "updated_at": time.time(),
        "last_eval_time": None,
        "last_eval_result": None,
        "last_evaluated_at": None,
        "proposals_generated": 0,
        "plans_generated": 0,
        "evaluation_interval_seconds": evaluation_interval_seconds,
        "allowed_windows": allowed_windows or [],
        "rate_limit": rate_limit,
        "trigger_count_window": [],
    }
    _TIER3_POLICY_REGISTRY.append(policy)
    return policy


def get_policies() -> List[Dict[str, Any]]:
    return list(_TIER3_POLICY_REGISTRY)


def get_policy(policy_id: str) -> Optional[Dict[str, Any]]:
    for p in _TIER3_POLICY_REGISTRY:
        if p["policy_id"] == policy_id:
            return p
    return None


def set_policy_enabled(policy_id: str, enabled: bool) -> Dict[str, Any]:
    for p in _TIER3_POLICY_REGISTRY:
        if p["policy_id"] == policy_id:
            p["enabled"] = enabled
            p["updated_at"] = time.time()
            return {"updated": True, "policy_id": policy_id, "enabled": enabled}
    return {"updated": False, "reason": f"policy '{policy_id}' not found"}


def clear_tier3_policies() -> None:
    """Reset the registry (for testing only)."""
    _TIER3_POLICY_REGISTRY.clear()


def clear_tier3_policy_eval_log() -> None:
    """Reset the evaluation log (for testing only)."""
    _TIER3_POLICY_EVAL_LOG.clear()


# ------------------------------------------------------------------
# Phase 42: policy lifecycle helpers
# ------------------------------------------------------------------

_TIER3_POLICY_CHANGE_LOG: List[Dict[str, Any]] = []


def clear_tier3_policy_change_log() -> None:
    """Reset the change log (for testing only)."""
    _TIER3_POLICY_CHANGE_LOG.clear()


def get_policy_change_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_TIER3_POLICY_CHANGE_LOG[-limit:])


def _log_policy_change(
    operation: str,
    policy_id: str,
    detail: Optional[Dict[str, Any]] = None,
    adaptive_origin: Optional[str] = None,
) -> None:
    _TIER3_POLICY_CHANGE_LOG.append({
        "operation": operation,
        "policy_id": policy_id,
        "detail": detail or {},
        "adaptive_origin": adaptive_origin,
        "timestamp": time.time(),
    })


def clone_policy(
    policy_id: str,
    overrides: Optional[Dict[str, Any]] = None,
    adaptive_origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Clone an existing policy with optional field overrides.

    The clone always starts disabled.
    """
    source = get_policy(policy_id)
    if source is None:
        return {"error": True, "reason": f"policy '{policy_id}' not found"}

    overrides = overrides or {}

    new_policy = {
        "policy_id": str(uuid.uuid4()),
        "name": overrides.get("name", source["name"] + " (clone)"),
        "description": overrides.get("description", source["description"]),
        "trigger_conditions": overrides.get("trigger_conditions",
                                            list(source["trigger_conditions"])),
        "actions": overrides.get("actions", list(source["actions"])),
        "enabled": False,
        "created_at": time.time(),
        "updated_at": time.time(),
        "last_eval_time": None,
        "last_eval_result": None,
        "last_evaluated_at": None,
        "proposals_generated": 0,
        "plans_generated": 0,
        "evaluation_interval_seconds": overrides.get(
            "evaluation_interval_seconds", source.get("evaluation_interval_seconds")),
        "allowed_windows": overrides.get(
            "allowed_windows", list(source.get("allowed_windows") or [])),
        "rate_limit": overrides.get("rate_limit", source.get("rate_limit")),
        "trigger_count_window": [],
        "cloned_from": policy_id,
    }
    if adaptive_origin:
        new_policy["adaptive_origin"] = adaptive_origin

    _TIER3_POLICY_REGISTRY.append(new_policy)
    _log_policy_change("clone", new_policy["policy_id"],
                       {"source": policy_id, "overrides": list(overrides.keys())},
                       adaptive_origin)
    return new_policy


def retire_policy(
    policy_id: str,
    adaptive_origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retire a policy by disabling it and marking it as retired.

    Retired policies are never evaluated by any evaluation path.
    """
    p = get_policy(policy_id)
    if p is None:
        return {"retired": False, "reason": f"policy '{policy_id}' not found"}

    if p.get("retired"):
        return {"retired": False, "reason": f"policy '{policy_id}' already retired"}

    p["enabled"] = False
    p["retired"] = True
    p["retired_at"] = time.time()
    p["updated_at"] = time.time()
    if adaptive_origin:
        p["adaptive_origin"] = adaptive_origin

    _log_policy_change("retire", policy_id, {}, adaptive_origin)
    return {"retired": True, "policy_id": policy_id}


_UPDATABLE_FIELDS = {
    "name", "description", "trigger_conditions", "actions",
    "evaluation_interval_seconds", "allowed_windows", "rate_limit",
}


def update_policy_fields(
    policy_id: str,
    fields: Dict[str, Any],
    adaptive_origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply controlled edits to a policy's configuration fields.

    Never auto-enables the policy.
    """
    p = get_policy(policy_id)
    if p is None:
        return {"updated": False, "reason": f"policy '{policy_id}' not found"}

    if p.get("retired"):
        return {"updated": False, "reason": f"policy '{policy_id}' is retired"}

    invalid = [k for k in fields if k not in _UPDATABLE_FIELDS]
    if invalid:
        return {"updated": False,
                "reason": f"non-updatable fields: {invalid}"}

    old_values = {k: p.get(k) for k in fields}
    for k, v in fields.items():
        p[k] = v
    p["updated_at"] = time.time()
    if adaptive_origin:
        p["adaptive_origin"] = adaptive_origin

    _log_policy_change("update_fields", policy_id,
                       {"changed": list(fields.keys()), "old_values": old_values},
                       adaptive_origin)
    return {"updated": True, "policy_id": policy_id,
            "changed_fields": list(fields.keys())}


# ------------------------------------------------------------------
# Phase 39: scheduling helpers
# ------------------------------------------------------------------

def set_policy_interval(policy_id: str, seconds: int) -> Dict[str, Any]:
    p = get_policy(policy_id)
    if p is None:
        return {"updated": False, "reason": f"policy '{policy_id}' not found"}
    if not isinstance(seconds, int) or seconds <= 0:
        return {"updated": False, "reason": "interval must be a positive integer"}
    p["evaluation_interval_seconds"] = seconds
    p["updated_at"] = time.time()
    return {"updated": True, "policy_id": policy_id,
            "evaluation_interval_seconds": seconds}


def set_policy_window(
    policy_id: str,
    windows: List[Dict[str, str]],
) -> Dict[str, Any]:
    p = get_policy(policy_id)
    if p is None:
        return {"updated": False, "reason": f"policy '{policy_id}' not found"}
    p["allowed_windows"] = windows
    p["updated_at"] = time.time()
    return {"updated": True, "policy_id": policy_id, "allowed_windows": windows}


def set_policy_rate_limit(policy_id: str, limit: int) -> Dict[str, Any]:
    p = get_policy(policy_id)
    if p is None:
        return {"updated": False, "reason": f"policy '{policy_id}' not found"}
    if not isinstance(limit, int) or limit <= 0:
        return {"updated": False, "reason": "rate_limit must be a positive integer"}
    p["rate_limit"] = limit
    p["updated_at"] = time.time()
    return {"updated": True, "policy_id": policy_id, "rate_limit": limit}


def _is_within_window(
    windows: List[Dict[str, str]],
    now_hhmm: Optional[str] = None,
) -> bool:
    """Check if current time-of-day falls within any allowed window."""
    if not windows:
        return True  # no windows means always allowed

    if now_hhmm is None:
        import datetime
        now_hhmm = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M")

    for w in windows:
        start = w.get("start", "00:00")
        end = w.get("end", "23:59")
        if start <= end:
            if start <= now_hhmm <= end:
                return True
        else:
            if now_hhmm >= start or now_hhmm <= end:
                return True
    return False


def _prune_trigger_window(entries: List[float], window_seconds: int = 3600) -> List[float]:
    """Remove entries older than window_seconds from the rolling window."""
    cutoff = time.time() - window_seconds
    return [t for t in entries if t > cutoff]


def _check_rate_limit(policy: Dict[str, Any]) -> bool:
    """Return True if the policy has NOT exceeded its rate limit."""
    limit = policy.get("rate_limit")
    if limit is None:
        return True
    window = _prune_trigger_window(policy.get("trigger_count_window") or [])
    policy["trigger_count_window"] = window
    return len(window) < limit


def _check_interval(policy: Dict[str, Any], now: float) -> bool:
    """Return True if enough time has passed since last evaluation."""
    interval = policy.get("evaluation_interval_seconds")
    if interval is None:
        return True
    last = policy.get("last_evaluated_at")
    if last is None:
        return True
    return (now - last) >= interval


def get_next_eligible_time(policy: Dict[str, Any]) -> Optional[float]:
    """Compute the earliest timestamp at which this policy may next be evaluated."""
    interval = policy.get("evaluation_interval_seconds")
    if interval is None:
        return None
    last = policy.get("last_evaluated_at")
    if last is None:
        return None
    return last + interval


_TIER3_POLICY_SCHEDULE_LOG: List[Dict[str, Any]] = []


def clear_tier3_policy_schedule_log() -> None:
    """Reset the schedule log (for testing only)."""
    _TIER3_POLICY_SCHEDULE_LOG.clear()


def get_policy_schedule_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_TIER3_POLICY_SCHEDULE_LOG[-limit:])


def evaluate_policies_scheduled(
    now_hhmm: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate all enabled policies that pass scheduling constraints.

    Operator-triggered only.  Checks interval, windows, and rate limits
    before evaluating each policy.  When an active governance profile
    exists, only policies in the profile's scope are considered, and
    scheduling overrides from the profile take precedence.
    """
    from runtime.tier3_profiles import is_policy_in_scope, get_scheduling_override
    from runtime.tier3_environments import (
        is_policy_allowed, is_policy_default, get_env_scheduling_override,
    )

    now = time.time()
    results: List[Dict[str, Any]] = []
    triggered = 0
    skipped_disabled = 0
    skipped_schedule: List[Dict[str, Any]] = []

    for policy in _TIER3_POLICY_REGISTRY:
        if policy.get("retired") or not policy.get("enabled"):
            skipped_disabled += 1
            continue

        pid = policy["policy_id"]
        in_scope = is_policy_in_scope(pid)
        env_default = is_policy_default(pid)
        if not in_scope and not env_default:
            skipped_disabled += 1
            continue

        if not is_policy_allowed(pid) and not env_default:
            skipped_disabled += 1
            continue

        profile_override = get_scheduling_override(pid)
        env_override = get_env_scheduling_override(pid)
        override = {**(env_override or {}), **(profile_override or {})}
        eff_interval = (override or {}).get(
            "evaluation_interval_seconds",
            policy.get("evaluation_interval_seconds"))
        eff_windows = (override or {}).get(
            "allowed_windows",
            policy.get("allowed_windows") or [])
        eff_rate_limit = (override or {}).get(
            "rate_limit",
            policy.get("rate_limit"))

        eff_policy = dict(policy)
        eff_policy["evaluation_interval_seconds"] = eff_interval
        eff_policy["rate_limit"] = eff_rate_limit

        skip_reason = None
        if not _check_interval(eff_policy, now):
            skip_reason = "interval_not_elapsed"
        elif not _is_within_window(eff_windows, now_hhmm):
            skip_reason = "outside_allowed_window"
        elif not _check_rate_limit(eff_policy):
            skip_reason = "rate_limit_exceeded"

        if skip_reason:
            skipped_schedule.append({
                "policy_id": policy["policy_id"],
                "policy_name": policy["name"],
                "reason": skip_reason,
            })
            continue

        result = _evaluate_single_policy(policy)
        policy["last_evaluated_at"] = now
        if result["result"] == "triggered":
            triggered += 1
            policy["trigger_count_window"] = _prune_trigger_window(
                policy.get("trigger_count_window") or [])
            policy["trigger_count_window"].append(now)
        results.append(result)

    summary = {
        "timestamp": now,
        "total_evaluated": len(results),
        "total_skipped_disabled": skipped_disabled,
        "total_skipped_schedule": len(skipped_schedule),
        "total_triggered": triggered,
        "policy_results": results,
        "schedule_skips": skipped_schedule,
    }
    _TIER3_POLICY_EVAL_LOG.append(summary)
    _TIER3_POLICY_SCHEDULE_LOG.append(summary)
    return summary


# ------------------------------------------------------------------
# Condition evaluators (pure, read-only)
# ------------------------------------------------------------------

def _eval_setting_equals(cond: Dict[str, Any]) -> bool:
    try:
        from runtime.system_settings import get_setting
        return get_setting(cond["key"]) == cond["value"]
    except Exception:
        return False


def _eval_drift_above(cond: Dict[str, Any]) -> bool:
    metric = cond.get("metric", "")
    threshold = cond.get("threshold", 0)

    try:
        from runtime.autonomy_cycle_log import get_autonomy_drift_report
        report = get_autonomy_drift_report()
    except Exception:
        return False

    _METRIC_KEYS = {
        "skip_rate": "skip_rate",
        "envelope_fail_rate": "fail_rate",
        "cadence_drift": "drift",
    }

    section_map = {
        "skip_rate": "skip_rate",
        "envelope_fail_rate": "envelope_stability",
        "cadence_drift": "cadence_drift",
    }

    section_name = section_map.get(metric)
    value_key = _METRIC_KEYS.get(metric)
    if section_name is None or value_key is None:
        return False

    section = report.get(section_name, {})
    value = section.get(value_key, 0)
    if metric == "cadence_drift":
        value = abs(value)
    return value > threshold


def _eval_proposal_count(cond: Dict[str, Any]) -> bool:
    status = cond.get("status", "")
    min_count = cond.get("min_count", 0)

    try:
        from runtime.tier3_proposals import get_tier3_proposals
        matching = [p for p in get_tier3_proposals() if p.get("status") == status]
        return len(matching) >= min_count
    except Exception:
        return False


_CONDITION_EVALUATORS = {
    "setting_equals": _eval_setting_equals,
    "drift_above": _eval_drift_above,
    "proposal_count": _eval_proposal_count,
}


# ------------------------------------------------------------------
# Action executors (create only, never execute)
# ------------------------------------------------------------------

def _exec_create_typed_proposal(act: Dict[str, Any], policy_id: str) -> Dict[str, Any]:
    from runtime.tier3_profiles import get_feature_flag

    if not get_feature_flag("allow_policy_generated_proposals"):
        return {"action": "create_typed_proposal", "created": False,
                "reason": "blocked by profile flag: allow_policy_generated_proposals=False"}

    from runtime.tier3_proposals import create_typed_tier3_proposal

    result = create_typed_tier3_proposal(
        title=act.get("title", "Policy-generated proposal"),
        rationale=act.get("rationale", "Generated by policy"),
        action_type=act.get("action_type", ""),
        payload=act.get("payload"),
        evidence={"policy_origin": policy_id},
    )

    if result.get("error"):
        return {"action": "create_typed_proposal", "created": False,
                "reason": result.get("reason", "?")}

    return {"action": "create_typed_proposal", "created": True,
            "proposal_id": result.get("id", "?")}


def _exec_create_execution_plan(act: Dict[str, Any], policy_id: str) -> Dict[str, Any]:
    from runtime.tier3_profiles import get_feature_flag

    if not get_feature_flag("allow_plans"):
        return {"action": "create_execution_plan", "created": False,
                "reason": "blocked by profile flag: allow_plans=False"}

    from runtime.tier3_plans import create_plan

    result = create_plan(
        name=act.get("name", "Policy-generated plan"),
        description=act.get("description", "Generated by policy"),
        proposal_ids=act.get("proposal_ids", []),
        dependencies=act.get("dependencies"),
    )

    if result.get("error"):
        return {"action": "create_execution_plan", "created": False,
                "reasons": result.get("reasons", [])}

    return {"action": "create_execution_plan", "created": True,
            "plan_id": result.get("plan_id", "?")}


_ACTION_EXECUTORS = {
    "create_typed_proposal": _exec_create_typed_proposal,
    "create_execution_plan": _exec_create_execution_plan,
}


# ------------------------------------------------------------------
# Evaluation engine
# ------------------------------------------------------------------

def _evaluate_single_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate one policy: check all conditions, run actions if all pass.
    Returns a structured evaluation result.
    """
    policy_id = policy["policy_id"]
    conditions = policy.get("trigger_conditions") or []
    actions = policy.get("actions") or []

    condition_results: List[Dict[str, Any]] = []
    all_pass = True

    for cond in conditions:
        ctype = cond.get("type", "")
        evaluator = _CONDITION_EVALUATORS.get(ctype)
        if evaluator is None:
            condition_results.append({"type": ctype, "result": False,
                                      "reason": "unknown condition type"})
            all_pass = False
            continue

        try:
            result = evaluator(cond)
        except Exception as exc:
            result = False
            condition_results.append({"type": ctype, "result": False,
                                      "reason": str(exc)})
            all_pass = False
            continue

        condition_results.append({"type": ctype, "result": result})
        if not result:
            all_pass = False

    action_results: List[Dict[str, Any]] = []
    if all_pass:
        for act in actions:
            atype = act.get("type", "")
            executor = _ACTION_EXECUTORS.get(atype)
            if executor is None:
                action_results.append({"type": atype, "created": False,
                                       "reason": "unknown action type"})
                continue

            try:
                ar = executor(act, policy_id)
            except Exception as exc:
                ar = {"type": atype, "created": False, "reason": str(exc)}

            action_results.append(ar)
            if ar.get("created"):
                if atype == "create_typed_proposal":
                    policy["proposals_generated"] += 1
                elif atype == "create_execution_plan":
                    policy["plans_generated"] += 1

    eval_result = "triggered" if all_pass else "conditions_not_met"
    policy["last_eval_time"] = time.time()
    policy["last_eval_result"] = eval_result
    policy["updated_at"] = time.time()

    return {
        "policy_id": policy_id,
        "policy_name": policy["name"],
        "result": eval_result,
        "conditions": condition_results,
        "actions": action_results,
        "timestamp": time.time(),
    }


def evaluate_policies() -> Dict[str, Any]:
    """
    Evaluate all enabled policies.  Operator-triggered only.

    When an active governance profile exists, only policies in the
    profile's scope are considered.
    """
    from runtime.tier3_profiles import is_policy_in_scope
    from runtime.tier3_environments import is_policy_allowed, is_policy_default

    results: List[Dict[str, Any]] = []
    triggered = 0
    skipped = 0

    for policy in _TIER3_POLICY_REGISTRY:
        if policy.get("retired") or not policy.get("enabled"):
            skipped += 1
            continue

        pid = policy["policy_id"]
        in_scope = is_policy_in_scope(pid)
        env_default = is_policy_default(pid)
        if not in_scope and not env_default:
            skipped += 1
            continue

        if not is_policy_allowed(pid) and not env_default:
            skipped += 1
            continue

        result = _evaluate_single_policy(policy)
        results.append(result)
        if result["result"] == "triggered":
            triggered += 1

    summary = {
        "timestamp": time.time(),
        "total_evaluated": len(results),
        "total_skipped": skipped,
        "total_triggered": triggered,
        "policy_results": results,
    }
    _TIER3_POLICY_EVAL_LOG.append(summary)
    return summary


def get_policy_eval_log(limit: int = 10) -> List[Dict[str, Any]]:
    return list(_TIER3_POLICY_EVAL_LOG[-limit:])
