# runtime/tier3_adaptive_bridge.py
"""
Tier-3 adaptive bridge.

Converts adaptive insights into governed Tier-3 proposals or plan
drafts — but ONLY when explicitly approved by the operator.  No
automatic creation, execution, or governance bypass.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_APPLIED_RECOMMENDATIONS: List[Dict[str, Any]] = []


def get_applied_recommendations(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_APPLIED_RECOMMENDATIONS[-limit:])


def clear_applied_recommendations() -> None:
    """Reset the log (for testing only)."""
    _APPLIED_RECOMMENDATIONS.clear()


def preview_recommendation(insight_id: str) -> Dict[str, Any]:
    """
    Show what proposal or plan would be created from an insight.

    Strictly read-only — never creates or mutates anything.
    """
    from runtime.tier3_adaptive import get_insight, insight_to_recommendation_action

    insight = get_insight(insight_id)
    if insight is None:
        return {"error": True, "reason": f"insight '{insight_id}' not found"}

    rec = insight_to_recommendation_action(insight)
    return {
        "insight_id": insight_id,
        "insight_type": insight.get("insight_type", "?"),
        "summary": insight.get("summary", ""),
        "recommendation": rec,
        "preview_only": True,
    }


def apply_recommendation(insight_id: str) -> Dict[str, Any]:
    """
    Create a governed artifact from an adaptive insight.

    For actionable insights this creates a Tier-3 proposal or plan.
    For non-actionable insights it returns the descriptive recommendation.
    All created artifacts carry ``adaptive_origin`` metadata.
    """
    from runtime.tier3_adaptive import get_insight, insight_to_recommendation_action

    insight = get_insight(insight_id)
    if insight is None:
        return {"applied": False, "reason": f"insight '{insight_id}' not found"}

    rec = insight_to_recommendation_action(insight)

    if not rec.get("actionable"):
        return {
            "applied": False,
            "reason": "insight is not actionable (descriptive only)",
            "recommendation": rec,
        }

    kind = rec.get("action_kind")

    if kind == "create_plan":
        result = _apply_create_plan(rec, insight_id)
    elif kind == "create_proposal":
        result = _apply_create_proposal(rec, insight_id)
    elif kind == "policy_edit":
        result = _apply_policy_edit(rec, insight_id)
    else:
        return {"applied": False, "reason": f"unknown action kind '{kind}'"}

    record = {
        "insight_id": insight_id,
        "action_kind": kind,
        "result": result,
        "timestamp": time.time(),
    }
    _APPLIED_RECOMMENDATIONS.append(record)
    return result


def _apply_create_plan(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    from runtime.tier3_plans import create_plan

    result = create_plan(
        name=rec.get("plan_name", "Adaptive plan"),
        description=rec.get("plan_description", "Created from adaptive insight") +
                    f" [adaptive_origin={insight_id}]",
        proposal_ids=rec.get("proposal_ids", []),
    )

    if result.get("error"):
        return {
            "applied": False,
            "artifact_type": "plan",
            "reason": "; ".join(result.get("reasons", [])),
        }

    return {
        "applied": True,
        "artifact_type": "plan",
        "plan_id": result["plan_id"],
        "insight_id": insight_id,
        "adaptive_origin": insight_id,
    }


def _apply_create_proposal(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    from runtime.tier3_proposals import create_typed_tier3_proposal

    result = create_typed_tier3_proposal(
        title=rec.get("title", "Adaptive proposal"),
        rationale=rec.get("rationale", "Created from adaptive insight"),
        action_type=rec.get("action_type", ""),
        payload=rec.get("payload"),
        evidence={"adaptive_origin": insight_id},
    )

    if result.get("error"):
        return {
            "applied": False,
            "artifact_type": "proposal",
            "reason": result.get("reason", "?"),
        }

    return {
        "applied": True,
        "artifact_type": "proposal",
        "proposal_id": result["id"],
        "insight_id": insight_id,
        "adaptive_origin": insight_id,
    }


# ------------------------------------------------------------------
# Phase 42: policy edit actions
# ------------------------------------------------------------------

def _apply_policy_edit(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    operation = rec.get("operation", "")

    if operation == "retire_policy":
        return _apply_retire_policy(rec, insight_id)
    if operation == "clone_and_tune_policy":
        return _apply_clone_and_tune(rec, insight_id)
    if operation == "merge_policies":
        return _apply_merge_policies(rec, insight_id)

    return {"applied": False, "artifact_type": "policy_edit",
            "reason": f"unknown policy_edit operation '{operation}'"}


def _apply_retire_policy(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    from runtime.tier3_policies import retire_policy

    pid = rec.get("target_policy_id", "")
    result = retire_policy(pid, adaptive_origin=insight_id)
    if not result.get("retired"):
        return {"applied": False, "artifact_type": "policy_edit",
                "reason": result.get("reason", "?")}

    return {
        "applied": True,
        "artifact_type": "policy_edit",
        "operation": "retire_policy",
        "policy_id": pid,
        "insight_id": insight_id,
        "adaptive_origin": insight_id,
    }


def _apply_clone_and_tune(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    from runtime.tier3_policies import clone_policy

    pid = rec.get("target_policy_id", "")
    overrides = rec.get("overrides") or {}
    result = clone_policy(pid, overrides=overrides, adaptive_origin=insight_id)
    if result.get("error"):
        return {"applied": False, "artifact_type": "policy_edit",
                "reason": result.get("reason", "?")}

    return {
        "applied": True,
        "artifact_type": "policy_edit",
        "operation": "clone_and_tune_policy",
        "new_policy_id": result["policy_id"],
        "source_policy_id": pid,
        "enabled": False,
        "insight_id": insight_id,
        "adaptive_origin": insight_id,
    }


def _apply_merge_policies(rec: Dict[str, Any], insight_id: str) -> Dict[str, Any]:
    from runtime.tier3_policies import get_policy, clone_policy, retire_policy

    policy_ids = rec.get("policy_ids") or []
    if len(policy_ids) < 2:
        return {"applied": False, "artifact_type": "policy_edit",
                "reason": "merge requires at least 2 policies"}

    primary = get_policy(policy_ids[0])
    if primary is None:
        return {"applied": False, "artifact_type": "policy_edit",
                "reason": f"primary policy '{policy_ids[0]}' not found"}

    merged_actions: List[Dict[str, Any]] = []
    for pid in policy_ids:
        p = get_policy(pid)
        if p:
            merged_actions.extend(p.get("actions") or [])

    clone_result = clone_policy(
        policy_ids[0],
        overrides={
            "name": primary["name"] + " (merged)",
            "actions": merged_actions,
        },
        adaptive_origin=insight_id,
    )
    if clone_result.get("error"):
        return {"applied": False, "artifact_type": "policy_edit",
                "reason": clone_result.get("reason", "?")}

    retired_ids = []
    for pid in policy_ids:
        r = retire_policy(pid, adaptive_origin=insight_id)
        if r.get("retired"):
            retired_ids.append(pid)

    return {
        "applied": True,
        "artifact_type": "policy_edit",
        "operation": "merge_policies",
        "new_policy_id": clone_result["policy_id"],
        "retired_policy_ids": retired_ids,
        "enabled": False,
        "insight_id": insight_id,
        "adaptive_origin": insight_id,
    }
