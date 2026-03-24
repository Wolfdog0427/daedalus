# governor/proposal_manager.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from .state_store import (
    load_proposals,
    save_proposals,
    load_state,
    save_state,
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ------------------------------------------------------------
# Core helpers
# ------------------------------------------------------------

def load_proposal_by_id(proposal_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single proposal by ID.
    Returns None if not found.
    """
    proposals = load_proposals()
    for p in proposals:
        if p.get("id") == proposal_id:
            return p
    return None


def _update_state_pending(proposal_id: str, add: bool) -> None:
    """
    Add or remove a proposal ID from the state's pending list.
    """
    state = load_state()
    pending = state["proposals"]["pending"]

    if add:
        if proposal_id not in pending:
            pending.append(proposal_id)
    else:
        if proposal_id in pending:
            pending.remove(proposal_id)

    save_state(state)


def _record_recent_decision(
    proposal_id: str,
    status: str,
    tier: int,
    decided_by: str,
    decided_at: str,
) -> None:
    """
    Append a recent decision entry to the state.
    """
    state = load_state()
    state["proposals"]["recent_decisions"].append(
        {
            "id": proposal_id,
            "status": status,
            "tier": tier,
            "decided_by": decided_by,
            "decided_at": decided_at,
        }
    )
    save_state(state)


# ------------------------------------------------------------
# Proposal creation
# ------------------------------------------------------------

def create_proposal(
    tier_requested: int,
    subsystem: str,
    risk_level: str,
    priority: str,
    drift_context: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
    proposal_summary: str,
    justification: List[str],
    planned_actions: List[Dict[str, Any]],
    expected_impact: Dict[str, Any],
    sandbox_preview: Dict[str, Any],
    source_cycle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new proposal, persist it, and register it as pending.
    """
    proposals = load_proposals()

    proposal_id = f"prop-{uuid.uuid4()}"
    proposal = {
        "id": proposal_id,
        "created_at": _now_iso(),
        "source_cycle_id": source_cycle_id,
        "tier_requested": tier_requested,
        "subsystem": subsystem,
        "risk_level": risk_level,
        "priority": priority,
        "drift_context": drift_context,
        "diagnostics_summary": diagnostics_summary,
        "proposal_summary": proposal_summary,
        "justification": justification,
        "planned_actions": planned_actions,
        "expected_impact": expected_impact,
        "sandbox_preview": sandbox_preview,
        "status": "pending",
        "decision": {
            "decided_by": None,
            "decided_at": None,
            "reason": None,
        },
    }

    proposals.append(proposal)
    save_proposals(proposals)

    # Register as pending
    _update_state_pending(proposal_id, add=True)

    return proposal


# ------------------------------------------------------------
# Listing
# ------------------------------------------------------------

def list_pending_proposals() -> List[Dict[str, Any]]:
    """
    Return all proposals with status == 'pending'.
    """
    proposals = load_proposals()
    return [p for p in proposals if p.get("status") == "pending"]


# ------------------------------------------------------------
# Status updates
# ------------------------------------------------------------

def update_proposal_status(
    proposal_id: str,
    status: str,
    decided_by: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update the status of a proposal and record the decision in state.
    """
    proposals = load_proposals()
    updated: Optional[Dict[str, Any]] = None

    for p in proposals:
        if p.get("id") == proposal_id:
            p["status"] = status
            p["decision"] = {
                "decided_by": decided_by,
                "decided_at": _now_iso(),
                "reason": reason,
            }
            updated = p
            break

    if updated is None:
        return None

    save_proposals(proposals)

    # Update pending list
    _update_state_pending(proposal_id, add=(status == "pending"))

    # Record recent decision
    _record_recent_decision(
        proposal_id=proposal_id,
        status=status,
        tier=updated.get("tier_requested"),
        decided_by=decided_by,
        decided_at=updated["decision"]["decided_at"],
    )

    return updated
