# runtime/tier3_plans.py
"""
Tier-3 execution plans.

A plan references one or more existing Tier-3 proposals and executes
them in dependency-respecting order through the existing governed
dispatcher.  All execution is operator-triggered — no background or
scheduled runs.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

_TIER3_PLAN_REGISTRY: List[Dict[str, Any]] = []

_VALID_PLAN_STATUSES = {"draft", "ready", "running", "completed", "failed"}

_ELIGIBLE_PROPOSAL_STATUSES = {"pending", "approved", "awaiting_approval"}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _find_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    from runtime.tier3_proposals import get_tier3_proposals

    for p in get_tier3_proposals():
        if p["id"] == proposal_id:
            return p
    return None


def _topological_sort(
    proposal_ids: List[str],
    dependencies: Dict[str, List[str]],
) -> Optional[List[str]]:
    """
    Return proposal_ids in dependency-respecting order, or None if a
    cycle is detected.  Uses Kahn's algorithm.
    """
    id_set = set(proposal_ids)
    in_degree: Dict[str, int] = {pid: 0 for pid in proposal_ids}
    adj: Dict[str, List[str]] = {pid: [] for pid in proposal_ids}

    for pid, deps in dependencies.items():
        if pid not in id_set:
            continue
        for dep in deps:
            if dep not in id_set:
                continue
            adj[dep].append(pid)
            in_degree[pid] += 1

    queue = deque(pid for pid in proposal_ids if in_degree[pid] == 0)
    result: List[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbour in adj[node]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(result) != len(proposal_ids):
        return None  # cycle
    return result


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_plan(
    name: str,
    description: str,
    proposal_ids: List[str],
    dependencies: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Create a new execution plan referencing existing typed proposals.

    Returns the plan dict, or a dict with ``"error"`` if validation fails.
    """
    dependencies = dependencies or {}

    errors: List[str] = []
    for pid in proposal_ids:
        p = _find_proposal(pid)
        if p is None:
            errors.append(f"proposal '{pid}' not found")
        elif not p.get("action_type"):
            errors.append(f"proposal '{pid[:8]}' is not typed")
        elif p.get("status") not in _ELIGIBLE_PROPOSAL_STATUSES:
            errors.append(f"proposal '{pid[:8]}' status '{p.get('status')}' "
                          f"is not eligible for plan inclusion")

    for dep_pid in set().union(*dependencies.values()) if dependencies else []:
        if dep_pid not in proposal_ids:
            errors.append(f"dependency '{dep_pid[:8]}' is not in the plan's proposal list")

    if errors:
        return {"error": True, "reasons": errors}

    order = _topological_sort(proposal_ids, dependencies)
    if order is None:
        return {"error": True, "reasons": ["dependency cycle detected"]}

    plan = {
        "plan_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "proposal_ids": proposal_ids,
        "execution_order": order,
        "dependencies": dependencies,
        "status": "draft",
        "proposal_results": {},
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _TIER3_PLAN_REGISTRY.append(plan)
    return plan


def get_plans() -> List[Dict[str, Any]]:
    return list(_TIER3_PLAN_REGISTRY)


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    for p in _TIER3_PLAN_REGISTRY:
        if p["plan_id"] == plan_id:
            return p
    return None


def update_plan_status(plan_id: str, new_status: str) -> Dict[str, Any]:
    if new_status not in _VALID_PLAN_STATUSES:
        return {"updated": False, "reason": f"invalid plan status '{new_status}'"}

    for p in _TIER3_PLAN_REGISTRY:
        if p["plan_id"] == plan_id:
            old = p["status"]
            p["status"] = new_status
            p["updated_at"] = time.time()
            return {"updated": True, "plan_id": plan_id,
                    "old_status": old, "new_status": new_status}

    return {"updated": False, "reason": f"plan '{plan_id}' not found"}


def clear_tier3_plans() -> None:
    """Reset the plan registry (for testing only)."""
    _TIER3_PLAN_REGISTRY.clear()


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def execute_plan(plan_id: str) -> Dict[str, Any]:
    """
    Execute all proposals in a plan in dependency-respecting order.

    Uses the existing governed execution path for each proposal.
    Stops on first failure; marks remaining as skipped.
    """
    plan = get_plan(plan_id)
    if plan is None:
        return {"executed": False, "reason": f"plan '{plan_id}' not found"}

    if plan["status"] not in ("draft", "ready"):
        return {"executed": False,
                "reason": f"plan status is '{plan['status']}', must be 'draft' or 'ready'"}

    from runtime.tier3_execution import (
        validate_proposal_for_execution,
        execute_tier3_proposal,
    )

    plan["status"] = "running"
    plan["updated_at"] = time.time()

    order = plan["execution_order"]
    results: Dict[str, Dict[str, Any]] = {}
    failed = False

    for pid in order:
        if failed:
            results[pid] = {"status": "skipped", "reason": "prior proposal failed"}
            continue

        proposal = _find_proposal(pid)
        if proposal is None:
            results[pid] = {"status": "failed", "reason": "proposal not found"}
            failed = True
            continue

        val = validate_proposal_for_execution(proposal)
        if not val["valid"]:
            results[pid] = {"status": "failed", "reason": val["reason"]}
            failed = True
            continue

        try:
            exec_result = execute_tier3_proposal(proposal)
            dr = exec_result.get("dispatch_result") or {}
            hr = dr.get("handler_result") or {}
            applied = hr.get("applied", False)

            if dr.get("dispatched") and applied:
                results[pid] = {"status": "success", "timestamp": time.time()}
            elif dr.get("dispatched") and not applied:
                results[pid] = {"status": "failed",
                                "reason": hr.get("reason", "handler did not apply")}
                failed = True
            else:
                results[pid] = {"status": "success", "timestamp": time.time(),
                                "note": "untyped or no dispatch"}
        except Exception as exc:
            results[pid] = {"status": "failed", "reason": str(exc)}
            failed = True

    plan["proposal_results"] = results
    plan["status"] = "failed" if failed else "completed"
    plan["updated_at"] = time.time()

    succeeded = sum(1 for r in results.values() if r["status"] == "success")
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")

    return {
        "executed": True,
        "plan_id": plan_id,
        "status": plan["status"],
        "total": len(order),
        "succeeded": succeeded,
        "failed": failed_count,
        "skipped": skipped,
        "proposal_results": results,
    }
