# runtime/tier3_proposals.py
"""
Tier-3 proposal registry.

Proposals are structured requests for high-impact operations that require
explicit operator review.  This module stores proposals in-memory — it
never executes actions, mutates subsystems, or bypasses governance logic.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_PROPOSAL_REGISTRY: List[Dict[str, Any]] = []

_VALID_STATUSES = {"pending", "approved", "rejected", "awaiting_approval", "invalid"}


def create_tier3_proposal(
    title: str,
    rationale: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a proposal, append it to the registry, and return it."""
    proposal = {
        "id": str(uuid.uuid4()),
        "title": title,
        "rationale": rationale,
        "evidence": evidence or {},
        "timestamp": time.time(),
        "status": "pending",
    }
    _TIER3_PROPOSAL_REGISTRY.append(proposal)
    return proposal


def get_tier3_proposals() -> List[Dict[str, Any]]:
    return list(_TIER3_PROPOSAL_REGISTRY)


def update_tier3_proposal_status(
    proposal_id: str, new_status: str
) -> Dict[str, Any]:
    """
    Change a proposal's status.  Never executes anything.

    Returns a result dict indicating success or failure.
    """
    if new_status not in _VALID_STATUSES:
        return {
            "updated": False,
            "reason": f"invalid status '{new_status}'; must be one of {sorted(_VALID_STATUSES)}",
        }

    for p in _TIER3_PROPOSAL_REGISTRY:
        if p["id"] == proposal_id:
            old = p["status"]
            p["status"] = new_status
            return {
                "updated": True,
                "id": proposal_id,
                "old_status": old,
                "new_status": new_status,
            }

    return {"updated": False, "reason": f"proposal '{proposal_id}' not found"}


def create_typed_tier3_proposal(
    title: str,
    rationale: str,
    action_type: str,
    payload: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a proposal with a validated action type and payload.

    Returns the proposal dict (with ``action_type`` and ``payload`` fields)
    or a dict with ``"error"`` if validation fails.
    """
    from runtime.tier3_actions import validate_tier3_payload

    payload = payload or {}
    val = validate_tier3_payload(action_type, payload)
    if not val["valid"]:
        return {"error": True, "reason": val["reason"], "action_type": action_type}

    proposal = {
        "id": str(uuid.uuid4()),
        "title": title,
        "rationale": rationale,
        "action_type": action_type,
        "payload": payload,
        "reversible": val.get("reversible", False),
        "evidence": evidence or {},
        "timestamp": time.time(),
        "status": "pending",
    }
    _TIER3_PROPOSAL_REGISTRY.append(proposal)
    return proposal


def create_migration_proposal(
    title: str,
    rationale: str,
    migration_name: str,
    migration_steps: Optional[List] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a typed migration proposal with automatic dry-run.

    If the dry-run passes, sets status to ``awaiting_approval``.
    If it fails, sets status to ``invalid``.
    """
    from runtime.tier3_actions import validate_tier3_payload

    payload = {
        "migration_name": migration_name,
        "migration_steps": migration_steps or [],
    }
    val = validate_tier3_payload("apply_migration", payload)
    if not val["valid"]:
        return {"error": True, "reason": val["reason"], "action_type": "apply_migration"}

    proposal_id = str(uuid.uuid4())

    from runtime.tier3_execution import dryrun_migration

    dryrun_result = dryrun_migration(payload)
    dryrun_result["proposal_id"] = proposal_id

    if dryrun_result["status"] == "pass":
        status = "awaiting_approval"
    else:
        status = "invalid"

    proposal = {
        "id": proposal_id,
        "title": title,
        "rationale": rationale,
        "action_type": "apply_migration",
        "payload": payload,
        "reversible": False,
        "evidence": evidence or {},
        "dryrun": dryrun_result,
        "timestamp": time.time(),
        "status": status,
    }
    _TIER3_PROPOSAL_REGISTRY.append(proposal)
    return proposal


def get_proposals_awaiting_approval() -> List[Dict[str, Any]]:
    return [p for p in _TIER3_PROPOSAL_REGISTRY
            if p.get("status") == "awaiting_approval"]


def clear_tier3_proposals() -> None:
    """Reset the registry (for testing only)."""
    _TIER3_PROPOSAL_REGISTRY.clear()
