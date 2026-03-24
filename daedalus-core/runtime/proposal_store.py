# runtime/proposal_store.py

from __future__ import annotations
from typing import Dict, Any, Optional

from governor.proposal_manager import load_proposals


def fetch_plan(proposal_id: str) -> Dict[str, Any]:
    """
    Retrieve the full proposal (with planned_actions and predicted deltas)
    for delta validation and patch application.

    Returns:
        {
            "id": str,
            "planned_actions": [...],
            ...
        }
    """
    proposals = load_proposals()
    for p in proposals:
        if p.get("id") == proposal_id:
            return p

    # If not found, return a structured empty plan
    return {
        "id": proposal_id,
        "planned_actions": [],
        "error": "proposal not found",
    }
