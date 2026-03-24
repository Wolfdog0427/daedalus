# runtime/tier3_promotion.py
"""
Tier-3 cross-environment promotion and comparison.

Provides read-only comparison helpers that diff policies, profiles,
and templates between environments, a promotion planner that
describes what operations would be needed, and a runbook generator
that produces a draft runbook for the promotion.  No mutations are
performed; all execution remains operator-triggered.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_PROMOTION_LOG: List[Dict[str, Any]] = []


def get_promotion_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_PROMOTION_LOG[-limit:])


def clear_promotion_log() -> None:
    _PROMOTION_LOG.clear()


# ------------------------------------------------------------------
# Comparison helpers (pure, read-only)
# ------------------------------------------------------------------

def compare_policies_between_envs(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    from runtime.tier3_environments import get_environment

    src = get_environment(source_env_id)
    tgt = get_environment(target_env_id)
    if src is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    if tgt is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}

    src_ids = set(src.get("allowed_policy_ids", []))
    tgt_ids = set(tgt.get("allowed_policy_ids", []))

    return {
        "source_env": source_env_id,
        "target_env": target_env_id,
        "scope": "policies",
        "only_in_source": sorted(src_ids - tgt_ids),
        "only_in_target": sorted(tgt_ids - src_ids),
        "in_both": sorted(src_ids & tgt_ids),
    }


def compare_profiles_between_envs(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    from runtime.tier3_environments import get_environment

    src = get_environment(source_env_id)
    tgt = get_environment(target_env_id)
    if src is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    if tgt is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}

    src_ids = set(src.get("allowed_profile_ids", []))
    tgt_ids = set(tgt.get("allowed_profile_ids", []))

    return {
        "source_env": source_env_id,
        "target_env": target_env_id,
        "scope": "profiles",
        "only_in_source": sorted(src_ids - tgt_ids),
        "only_in_target": sorted(tgt_ids - src_ids),
        "in_both": sorted(src_ids & tgt_ids),
    }


def compare_templates_between_envs(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    from runtime.tier3_environments import get_environment

    src = get_environment(source_env_id)
    tgt = get_environment(target_env_id)
    if src is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    if tgt is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}

    src_ids = set(src.get("allowed_runbook_template_ids", []))
    tgt_ids = set(tgt.get("allowed_runbook_template_ids", []))

    return {
        "source_env": source_env_id,
        "target_env": target_env_id,
        "scope": "templates",
        "only_in_source": sorted(src_ids - tgt_ids),
        "only_in_target": sorted(tgt_ids - src_ids),
        "in_both": sorted(src_ids & tgt_ids),
    }


_COMPARE_DISPATCH = {
    "policies": compare_policies_between_envs,
    "profiles": compare_profiles_between_envs,
    "templates": compare_templates_between_envs,
}


def compare_envs(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> Dict[str, Any]:
    """Compare one or all scopes between two environments."""
    if scope == "all":
        results = {}
        for s, fn in _COMPARE_DISPATCH.items():
            results[s] = fn(source_env_id, target_env_id)
        return {"source_env": source_env_id, "target_env": target_env_id,
                "scope": "all", "comparisons": results}

    fn = _COMPARE_DISPATCH.get(scope)
    if fn is None:
        return {"error": True, "reason": f"unknown scope '{scope}'"}
    return fn(source_env_id, target_env_id)


# ------------------------------------------------------------------
# Promotion planning (read-only)
# ------------------------------------------------------------------

def plan_promotion(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> Dict[str, Any]:
    """
    Build a read-only promotion plan describing what items from source
    would need to be added to target's allowlists.  No mutations.
    """
    from runtime.tier3_environments import get_environment, get_promotion_path

    src = get_environment(source_env_id)
    tgt = get_environment(target_env_id)
    if src is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    if tgt is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}

    path_result = get_promotion_path(source_env_id, target_env_id)
    has_path = not path_result.get("error")

    scopes = [scope] if scope != "all" else ["policies", "profiles", "templates"]
    operations: List[Dict[str, Any]] = []
    conflicts: List[str] = []

    for s in scopes:
        comp = _COMPARE_DISPATCH.get(s)
        if comp is None:
            conflicts.append(f"unknown scope '{s}'")
            continue
        diff = comp(source_env_id, target_env_id)
        if diff.get("error"):
            conflicts.append(diff.get("reason", "comparison failed"))
            continue

        to_add = diff.get("only_in_source", [])
        for item_id in to_add:
            operations.append({
                "scope": s,
                "operation": "add_to_target_allowlist",
                "item_id": item_id,
            })

    plan = {
        "plan_id": str(uuid.uuid4()),
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "has_promotion_path": has_path,
        "promotion_path": path_result.get("path") if has_path else None,
        "operations": operations,
        "conflicts": conflicts,
        "timestamp": time.time(),
    }

    _PROMOTION_LOG.append({
        "type": "plan",
        "plan_id": plan["plan_id"],
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "n_operations": len(operations),
        "timestamp": plan["timestamp"],
    })

    return plan


# ------------------------------------------------------------------
# Promotion runbook generation (creates draft only)
# ------------------------------------------------------------------

def create_promotion_runbook_from_plan(
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a concrete runbook that captures the promotion steps
    described in a promotion plan.  The runbook is registered in
    draft status and NEVER executed.

    Promotion steps are modeled as policy-evaluation and
    adaptive-insight steps that the operator reviews before executing.
    """
    if not plan.get("operations"):
        return {"error": True, "reason": "promotion plan has no operations"}

    try:
        from runtime.tier3_env_guardrails import check_promotion_runbook
        gr = check_promotion_runbook(
            plan.get("source_env_id", ""),
            plan.get("target_env_id", ""))
        if not gr.get("allowed"):
            reasons = gr.get("blocking_reasons", [])
            return {"error": True,
                    "reason": "; ".join(reasons) if reasons
                    else "blocked by guardrail"}
    except Exception:
        pass

    steps: List[Dict[str, Any]] = [
        {"type": "evaluate_policies_once"},
        {"type": "generate_adaptive_insights"},
    ]

    source_name = _env_name(plan.get("source_env_id", "?"))
    target_name = _env_name(plan.get("target_env_id", "?"))

    from runtime.tier3_runbooks import create_runbook

    runbook = create_runbook(
        name=f"Promotion: {source_name} -> {target_name} ({plan.get('scope', 'all')})",
        description=(
            f"Promotion runbook for {len(plan['operations'])} operations "
            f"from {source_name} to {target_name}."
        ),
        steps=steps,
    )

    if runbook.get("error"):
        return runbook

    runbook["promotion_origin"] = {
        "plan_id": plan.get("plan_id"),
        "source_env_id": plan.get("source_env_id"),
        "target_env_id": plan.get("target_env_id"),
        "scope": plan.get("scope"),
        "operations": plan.get("operations", []),
    }

    _PROMOTION_LOG.append({
        "type": "runbook",
        "plan_id": plan.get("plan_id"),
        "runbook_id": runbook["runbook_id"],
        "source_env_id": plan.get("source_env_id"),
        "target_env_id": plan.get("target_env_id"),
        "scope": plan.get("scope"),
        "timestamp": time.time(),
    })

    return runbook


def _env_name(env_id: str) -> str:
    from runtime.tier3_environments import get_environment
    env = get_environment(env_id)
    return env["name"] if env else env_id[:8]
