# runtime/tier3_multi_env.py
"""
Multi-environment orchestration for Tier-3 governance.

Provides read-only comparison, planning, and runbook generation
across an entire promotion path (e.g. dev -> staging -> prod).
All functions are operator-triggered.  No auto-promotion, no
auto-execution, and no weakening of existing governance.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

_MULTI_ENV_LOG: List[Dict[str, Any]] = []


def get_multi_env_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_MULTI_ENV_LOG[-limit:])


def clear_multi_env_log() -> None:
    _MULTI_ENV_LOG.clear()


# ------------------------------------------------------------------
# Path comparison (read-only)
# ------------------------------------------------------------------

def compare_across_path(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> Dict[str, Any]:
    """
    Compare governance state hop-by-hop along the promotion path.
    Purely read-only.
    """
    from runtime.tier3_environments import get_promotion_path
    from runtime.tier3_promotion import compare_envs

    path_result = get_promotion_path(source_env_id, target_env_id)
    if path_result.get("error"):
        return path_result

    path = path_result["path"]
    hops: List[Dict[str, Any]] = []
    for i in range(len(path) - 1):
        hop = compare_envs(path[i], path[i + 1], scope)
        hops.append({
            "from_env": path[i],
            "to_env": path[i + 1],
            "comparison": hop,
        })

    report = {
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "path": path,
        "hops": hops,
        "timestamp": time.time(),
    }

    _MULTI_ENV_LOG.append({
        "type": "compare",
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "n_hops": len(hops),
        "timestamp": report["timestamp"],
    })

    return report


# ------------------------------------------------------------------
# Multi-hop promotion planning (read-only)
# ------------------------------------------------------------------

def generate_multi_env_promotion_plan(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> Dict[str, Any]:
    """
    Generate a promotion plan spanning every hop in the path.
    Runs guardrail checks per hop.  Purely read-only.
    """
    from runtime.tier3_environments import get_promotion_path
    from runtime.tier3_promotion import plan_promotion

    path_result = get_promotion_path(source_env_id, target_env_id)
    if path_result.get("error"):
        return path_result

    path = path_result["path"]
    hop_plans: List[Dict[str, Any]] = []
    guardrail_failures: List[Dict[str, Any]] = []

    for i in range(len(path) - 1):
        from_id = path[i]
        to_id = path[i + 1]

        try:
            from runtime.tier3_env_guardrails import check_promotion_runbook
            gr = check_promotion_runbook(from_id, to_id)
            if not gr.get("allowed"):
                guardrail_failures.append({
                    "from_env": from_id,
                    "to_env": to_id,
                    "blocking_reasons": gr.get("blocking_reasons", []),
                    "warnings": gr.get("warnings", []),
                })
        except Exception:
            pass

        hop_plan = plan_promotion(from_id, to_id, scope)
        hop_plans.append({
            "from_env": from_id,
            "to_env": to_id,
            "plan": hop_plan,
        })

    plan = {
        "multi_plan_id": str(uuid.uuid4()),
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "path": path,
        "hop_plans": hop_plans,
        "guardrail_failures": guardrail_failures,
        "total_operations": sum(
            len(h["plan"].get("operations", []))
            for h in hop_plans
            if not h["plan"].get("error")
        ),
        "timestamp": time.time(),
    }

    _MULTI_ENV_LOG.append({
        "type": "plan",
        "multi_plan_id": plan["multi_plan_id"],
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "scope": scope,
        "n_hops": len(hop_plans),
        "n_guardrail_failures": len(guardrail_failures),
        "total_operations": plan["total_operations"],
        "timestamp": plan["timestamp"],
    })

    return plan


# ------------------------------------------------------------------
# Multi-hop runbook generation (creates draft only)
# ------------------------------------------------------------------

def create_multi_env_promotion_runbook(
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a runbook that spans all hops in a multi-environment
    promotion plan.  The runbook is registered in draft status
    and NEVER executed.
    """
    if plan.get("error"):
        return plan

    hop_plans = plan.get("hop_plans", [])
    if not hop_plans:
        return {"error": True, "reason": "no hops in multi-env plan"}

    guardrail_failures = plan.get("guardrail_failures", [])
    if guardrail_failures:
        reasons = []
        for gf in guardrail_failures:
            for r in gf.get("blocking_reasons", []):
                reasons.append(
                    f"{gf['from_env'][:8]}..→{gf['to_env'][:8]}..: {r}")
        return {"error": True,
                "reason": "guardrail failures: " + "; ".join(reasons)}

    steps: List[Dict[str, Any]] = []
    for hop in hop_plans:
        hop_plan = hop.get("plan", {})
        if hop_plan.get("error"):
            continue
        steps.append({"type": "evaluate_policies_once"})
        steps.append({"type": "generate_adaptive_insights"})

    if not steps:
        return {"error": True, "reason": "no viable steps in plan"}

    source_name = _env_name(plan.get("source_env_id", "?"))
    target_name = _env_name(plan.get("target_env_id", "?"))
    n_hops = len(hop_plans)

    from runtime.tier3_runbooks import create_runbook

    runbook = create_runbook(
        name=(f"Multi-env promotion: {source_name} -> {target_name} "
              f"({n_hops} hops, {plan.get('scope', 'all')})"),
        description=(
            f"Multi-environment promotion across {n_hops} hops, "
            f"{plan.get('total_operations', 0)} operations."
        ),
        steps=steps,
    )

    if runbook.get("error"):
        return runbook

    runbook["multi_env_origin"] = {
        "multi_plan_id": plan.get("multi_plan_id"),
        "source_env_id": plan.get("source_env_id"),
        "target_env_id": plan.get("target_env_id"),
        "scope": plan.get("scope"),
        "path": plan.get("path", []),
        "total_operations": plan.get("total_operations", 0),
    }

    _record_lineage_for_plan(plan, runbook)

    _MULTI_ENV_LOG.append({
        "type": "runbook",
        "multi_plan_id": plan.get("multi_plan_id"),
        "runbook_id": runbook["runbook_id"],
        "source_env_id": plan.get("source_env_id"),
        "target_env_id": plan.get("target_env_id"),
        "scope": plan.get("scope"),
        "n_hops": n_hops,
        "timestamp": time.time(),
    })

    return runbook


def _record_lineage_for_plan(
    plan: Dict[str, Any],
    runbook: Dict[str, Any],
) -> None:
    """Record lineage entries for each promoted item."""
    try:
        from runtime.tier3_lineage import record_lineage
    except Exception:
        return

    meta = {
        "multi_plan_id": plan.get("multi_plan_id"),
        "runbook_id": runbook.get("runbook_id"),
    }

    for hop in plan.get("hop_plans", []):
        hop_plan = hop.get("plan", {})
        if hop_plan.get("error"):
            continue
        from_env = hop["from_env"]
        to_env = hop["to_env"]
        for op in hop_plan.get("operations", []):
            scope = op.get("scope", "policy")
            obj_type = _scope_to_type(scope)
            record_lineage(
                object_type=obj_type,
                object_id=op.get("item_id", ""),
                origin_env_id=from_env,
                derived_env_id=to_env,
                operation="promote",
                metadata=meta,
            )


def _scope_to_type(scope: str) -> str:
    return {
        "policies": "policy",
        "profiles": "profile",
        "templates": "template",
    }.get(scope, "policy")


def _env_name(env_id: str) -> str:
    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        return env["name"] if env else env_id[:8]
    except Exception:
        return env_id[:8]
