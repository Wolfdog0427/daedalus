# runtime/tier3_adaptive.py
"""
Tier-3 adaptive insights engine.

Reads telemetry, proposal outcomes, policy behavior, and scheduling
history to generate descriptive, read-only recommendations.  This
module NEVER mutates system state, creates proposals or plans, or
bypasses governance gates.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_ADAPTIVE_INSIGHTS: List[Dict[str, Any]] = []


def get_insights(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_ADAPTIVE_INSIGHTS[-limit:])


def get_insight(insight_id: str) -> Optional[Dict[str, Any]]:
    for i in _ADAPTIVE_INSIGHTS:
        if i["insight_id"] == insight_id:
            return i
    return None


def clear_insights() -> None:
    """Reset the insight store (for testing only)."""
    _ADAPTIVE_INSIGHTS.clear()


def _add_insight(
    insight_type: str,
    summary: str,
    recommended_action: str,
    related_policy_ids: Optional[List[str]] = None,
    related_proposal_ids: Optional[List[str]] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = {
        "insight_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "insight_type": insight_type,
        "summary": summary,
        "recommended_action": recommended_action,
        "related_policy_ids": related_policy_ids or [],
        "related_proposal_ids": related_proposal_ids or [],
        "detail": detail or {},
    }
    _ADAPTIVE_INSIGHTS.append(entry)
    return entry


# ------------------------------------------------------------------
# Analyzers (pure, read-only)
# ------------------------------------------------------------------

def _analyze_policy_effectiveness() -> List[Dict[str, Any]]:
    """Identify policies that never trigger or trigger excessively."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_policies import get_policies
        policies = get_policies()
    except Exception:
        return insights

    for p in policies:
        if not p.get("enabled"):
            continue

        pid = p["policy_id"]
        name = p["name"]
        generated = p.get("proposals_generated", 0) + p.get("plans_generated", 0)
        evals = p.get("last_eval_result")

        if evals is not None and generated == 0:
            insights.append(_add_insight(
                "policy_never_triggers",
                f"Policy '{name}' has been evaluated but never triggered.",
                f"Consider relaxing conditions or disabling policy '{name}'.",
                related_policy_ids=[pid],
                detail={"proposals_generated": 0, "plans_generated": 0},
            ))

        if generated > 10:
            insights.append(_add_insight(
                "policy_high_trigger_rate",
                f"Policy '{name}' has generated {generated} artifacts.",
                f"Consider tightening conditions or adding a rate limit to '{name}'.",
                related_policy_ids=[pid],
                detail={"total_generated": generated},
            ))

    return insights


def _analyze_proposal_outcomes() -> List[Dict[str, Any]]:
    """Identify patterns in proposal success/failure."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_proposals import get_tier3_proposals
        proposals = get_tier3_proposals()
    except Exception:
        return insights

    if not proposals:
        return insights

    status_counts: Dict[str, int] = {}
    for p in proposals:
        s = p.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(proposals)
    rejected = status_counts.get("rejected", 0)
    invalid = status_counts.get("invalid", 0)

    if total > 0 and (rejected + invalid) / total > 0.5:
        insights.append(_add_insight(
            "high_rejection_rate",
            f"{rejected + invalid}/{total} proposals were rejected or invalid.",
            "Review proposal generation criteria; conditions may be too loose.",
            related_proposal_ids=[p["id"] for p in proposals
                                  if p.get("status") in ("rejected", "invalid")][:5],
            detail={"status_counts": status_counts},
        ))

    pending = status_counts.get("pending", 0)
    if pending > 5:
        insights.append(_add_insight(
            "pending_backlog",
            f"{pending} proposals are pending review.",
            "Consider reviewing pending proposals or adjusting policy generation rate.",
            detail={"pending_count": pending},
        ))

    by_type: Dict[str, int] = {}
    for p in proposals:
        at = p.get("action_type")
        if at:
            by_type[at] = by_type.get(at, 0) + 1

    for at, count in by_type.items():
        if count >= 3:
            ids = [p["id"] for p in proposals if p.get("action_type") == at][:5]
            insights.append(_add_insight(
                "repeated_action_type",
                f"Action type '{at}' appears in {count} proposals.",
                f"Consider consolidating '{at}' proposals into an execution plan.",
                related_proposal_ids=ids,
                detail={"action_type": at, "count": count},
            ))

    return insights


def _analyze_dryrun_patterns() -> List[Dict[str, Any]]:
    """Identify recurring dry-run failures."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_execution import get_tier3_dryrun_log
        dryruns = get_tier3_dryrun_log(50)
    except Exception:
        return insights

    if not dryruns:
        return insights

    failed = [d for d in dryruns if d.get("status") == "fail"]
    if len(failed) > len(dryruns) / 2 and len(dryruns) >= 3:
        insights.append(_add_insight(
            "frequent_dryrun_failures",
            f"{len(failed)}/{len(dryruns)} recent dry-runs failed.",
            "Review migration step definitions; common failure patterns may indicate stale preconditions.",
            detail={"failed_count": len(failed), "total_count": len(dryruns)},
        ))

    return insights


def _analyze_scheduling_behavior() -> List[Dict[str, Any]]:
    """Identify policies with excessive scheduling skips."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_policies import get_policy_schedule_log
        logs = get_policy_schedule_log(20)
    except Exception:
        return insights

    skip_counts: Dict[str, Dict[str, int]] = {}
    for entry in logs:
        for sk in entry.get("schedule_skips", []):
            pid = sk.get("policy_id", "?")
            reason = sk.get("reason", "?")
            if pid not in skip_counts:
                skip_counts[pid] = {}
            skip_counts[pid][reason] = skip_counts[pid].get(reason, 0) + 1

    for pid, reasons in skip_counts.items():
        total_skips = sum(reasons.values())
        if total_skips >= 5:
            top_reason = max(reasons, key=reasons.get)  # type: ignore[arg-type]
            if top_reason == "interval_not_elapsed":
                rec = f"Consider increasing the evaluation interval for policy {pid[:8]}.."
            elif top_reason == "outside_allowed_window":
                rec = f"Consider widening allowed windows for policy {pid[:8]}.."
            elif top_reason == "rate_limit_exceeded":
                rec = f"Consider increasing the rate limit for policy {pid[:8]}.."
            else:
                rec = f"Review scheduling constraints for policy {pid[:8]}.."

            insights.append(_add_insight(
                "excessive_schedule_skips",
                f"Policy {pid[:8]}.. skipped {total_skips} times (top reason: {top_reason}).",
                rec,
                related_policy_ids=[pid],
                detail={"skip_reasons": reasons, "total_skips": total_skips},
            ))

    return insights


def _analyze_plan_consolidation() -> List[Dict[str, Any]]:
    """Suggest plan consolidation when proposals frequently share action types."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_proposals import get_tier3_proposals
        proposals = get_tier3_proposals()
    except Exception:
        return insights

    pending = [p for p in proposals if p.get("status") == "pending" and p.get("action_type")]
    if len(pending) < 3:
        return insights

    by_type: Dict[str, List[str]] = {}
    for p in pending:
        at = p["action_type"]
        by_type.setdefault(at, []).append(p["id"])

    for at, ids in by_type.items():
        if len(ids) >= 3:
            insights.append(_add_insight(
                "plan_consolidation",
                f"{len(ids)} pending '{at}' proposals could be grouped into a single plan.",
                f"Use t3_plan_create to bundle these {len(ids)} proposals for coordinated execution.",
                related_proposal_ids=ids[:5],
                detail={"action_type": at, "proposal_count": len(ids)},
            ))

    return insights


# ------------------------------------------------------------------
# Phase 42: policy evolution analyzers (pure, read-only)
# ------------------------------------------------------------------

def _analyze_policy_evolution() -> List[Dict[str, Any]]:
    """Identify policies that are candidates for structural evolution."""
    insights: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_policies import get_policies
        policies = get_policies()
    except Exception:
        return insights

    active = [p for p in policies if p.get("enabled") and not p.get("retired")]

    for p in active:
        pid = p["policy_id"]
        name = p["name"]
        generated = p.get("proposals_generated", 0) + p.get("plans_generated", 0)
        evals = p.get("last_eval_result")

        if evals is not None and generated == 0:
            insights.append(_add_insight(
                "policy_candidate_retire",
                f"Policy '{name}' never triggers and is a candidate for retirement.",
                f"Retire policy '{name}' to reduce evaluation overhead.",
                related_policy_ids=[pid],
                detail={"operation": "retire_policy"},
            ))

        if generated > 10:
            insights.append(_add_insight(
                "policy_candidate_split",
                f"Policy '{name}' is noisy ({generated} artifacts). Consider cloning with tighter thresholds.",
                f"Clone '{name}' with adjusted conditions and retire the original.",
                related_policy_ids=[pid],
                detail={
                    "operation": "clone_and_tune_policy",
                    "total_generated": generated,
                    "suggested_overrides": {"rate_limit": max(1, generated // 5)},
                },
            ))

    seen_conditions: Dict[str, List[str]] = {}
    for p in active:
        key = str(sorted(
            (c.get("type", ""), str(c))
            for c in p.get("trigger_conditions") or []))
        seen_conditions.setdefault(key, []).append(p["policy_id"])

    for key, pids in seen_conditions.items():
        if len(pids) >= 2:
            names = []
            for pid in pids:
                pol = next((p for p in active if p["policy_id"] == pid), None)
                if pol:
                    names.append(pol["name"])
            insights.append(_add_insight(
                "policy_candidate_merge",
                f"Policies {names} share identical conditions and could be merged.",
                f"Clone one policy combining both action sets, then retire the originals.",
                related_policy_ids=pids,
                detail={"operation": "merge_policies", "policy_ids": pids},
            ))

    return insights


# ------------------------------------------------------------------
# Phase 41: recommendation action mapper (pure, read-only)
# ------------------------------------------------------------------

def insight_to_recommendation_action(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map an insight to a structured recommendation action.

    Returns a recommendation object describing what governed artifact
    would be created.  This function MUST NOT create proposals or plans,
    mutate state, or execute anything.
    """
    itype = insight.get("insight_type", "")
    detail = insight.get("detail") or {}
    related_proposals = insight.get("related_proposal_ids") or []
    related_policies = insight.get("related_policy_ids") or []

    # Phase 42: policy evolution recommendations
    if itype == "policy_candidate_retire" and related_policies:
        return {
            "actionable": True,
            "action_kind": "policy_edit",
            "operation": "retire_policy",
            "target_policy_id": related_policies[0],
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "policy_candidate_split" and related_policies:
        return {
            "actionable": True,
            "action_kind": "policy_edit",
            "operation": "clone_and_tune_policy",
            "target_policy_id": related_policies[0],
            "overrides": detail.get("suggested_overrides") or {},
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "policy_candidate_merge" and len(related_policies) >= 2:
        return {
            "actionable": True,
            "action_kind": "policy_edit",
            "operation": "merge_policies",
            "policy_ids": detail.get("policy_ids") or related_policies,
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype in ("plan_consolidation", "repeated_action_type") and related_proposals:
        at = detail.get("action_type", "unknown")
        return {
            "actionable": True,
            "action_kind": "create_plan",
            "plan_name": f"Consolidated {at} plan",
            "plan_description": f"Auto-suggested plan grouping {len(related_proposals)} "
                                f"'{at}' proposals from adaptive insight.",
            "proposal_ids": list(related_proposals),
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "excessive_schedule_skips":
        skip_reasons = detail.get("skip_reasons") or {}
        top_reason = max(skip_reasons, key=skip_reasons.get) if skip_reasons else "unknown"  # type: ignore[arg-type]
        return {
            "actionable": False,
            "action_kind": "descriptive",
            "description": insight.get("recommended_action", ""),
            "suggested_adjustment": top_reason,
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "policy_high_trigger_rate":
        return {
            "actionable": False,
            "action_kind": "descriptive",
            "description": insight.get("recommended_action", ""),
            "suggested_adjustment": "add_or_tighten_rate_limit",
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "policy_never_triggers":
        return {
            "actionable": False,
            "action_kind": "descriptive",
            "description": insight.get("recommended_action", ""),
            "suggested_adjustment": "relax_conditions_or_disable",
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "high_rejection_rate":
        return {
            "actionable": False,
            "action_kind": "descriptive",
            "description": insight.get("recommended_action", ""),
            "suggested_adjustment": "review_generation_criteria",
            "insight_id": insight.get("insight_id", "?"),
        }

    if itype == "frequent_dryrun_failures":
        return {
            "actionable": False,
            "action_kind": "descriptive",
            "description": insight.get("recommended_action", ""),
            "suggested_adjustment": "review_migration_steps",
            "insight_id": insight.get("insight_id", "?"),
        }

    return {
        "actionable": False,
        "action_kind": "descriptive",
        "description": insight.get("recommended_action", ""),
        "insight_id": insight.get("insight_id", "?"),
    }


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def generate_adaptive_insights() -> Dict[str, Any]:
    """
    Run all analyzers and collect insights.

    This function is strictly read-only: it reads telemetry, proposals,
    policies, and plans, but never modifies them.
    """
    before_count = len(_ADAPTIVE_INSIGHTS)

    _analyze_policy_effectiveness()
    _analyze_proposal_outcomes()
    _analyze_dryrun_patterns()
    _analyze_scheduling_behavior()
    _analyze_plan_consolidation()
    _analyze_policy_evolution()

    new_insights = _ADAPTIVE_INSIGHTS[before_count:]

    return {
        "timestamp": time.time(),
        "insights_generated": len(new_insights),
        "total_insights": len(_ADAPTIVE_INSIGHTS),
        "new_insights": list(new_insights),
    }
