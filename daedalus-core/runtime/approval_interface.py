# runtime/approval_interface.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from runtime.logging_manager import log_event


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class ApprovalInterface:
    """
    Stores and manages proposals:
    - pending proposals
    - approved proposals
    - rejected proposals
    - cancelled proposals
    - rollback-aware metadata
    """

    def __init__(self):
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.decisions: Dict[str, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # Proposal Retrieval
    # ---------------------------------------------------------

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return self.pending.get(proposal_id) or self.decisions.get(proposal_id)

    def list_pending(self) -> List[Dict[str, Any]]:
        return list(self.pending.values())

    # ---------------------------------------------------------
    # Proposal Lifecycle
    # ---------------------------------------------------------

    def approve(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        proposal = self.pending.pop(proposal_id, None)
        if not proposal:
            return {"status": "not_found", "proposal_id": proposal_id}

        proposal["status"] = "approved"
        proposal["decision"] = {
            "decided_by": "user",
            "decided_at": _now_iso(),
            "reason": reason,
        }
        proposal["rolled_back"] = False  # default

        self.decisions[proposal_id] = proposal

        log_event("proposal", f"Proposal {proposal_id} approved", {"reason": reason})
        return {"proposal_id": proposal_id, "status": "approved", "result": proposal}

    def reject(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        proposal = self.pending.pop(proposal_id, None)
        if not proposal:
            return {"status": "not_found", "proposal_id": proposal_id}

        proposal["status"] = "rejected"
        proposal["decision"] = {
            "decided_by": "user",
            "decided_at": _now_iso(),
            "reason": reason,
        }
        proposal["rolled_back"] = False

        self.decisions[proposal_id] = proposal

        log_event("proposal", f"Proposal {proposal_id} rejected", {"reason": reason})
        return {"proposal_id": proposal_id, "status": "rejected", "result": proposal}

    def cancel(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        proposal = self.pending.pop(proposal_id, None)
        if not proposal:
            return {"status": "not_found", "proposal_id": proposal_id}

        proposal["status"] = "cancelled"
        proposal["decision"] = {
            "decided_by": "user",
            "decided_at": _now_iso(),
            "reason": reason,
        }
        proposal["rolled_back"] = False

        self.decisions[proposal_id] = proposal

        log_event("proposal", f"Proposal {proposal_id} cancelled", {"reason": reason})
        return {"proposal_id": proposal_id, "status": "cancelled", "result": proposal}

    # ---------------------------------------------------------
    # Rollback Integration
    # ---------------------------------------------------------

    def mark_rolled_back(self, proposal_id: str, subsystem: str, snapshot_dir: str) -> None:
        """
        Called by SHO Patch Flow when a rollback occurs.
        """
        proposal = self.decisions.get(proposal_id)
        if not proposal:
            return

        proposal["rolled_back"] = True
        proposal["rollback_info"] = {
            "timestamp": _now_iso(),
            "subsystem": subsystem,
            "snapshot_dir": snapshot_dir,
        }

        log_event(
            "proposal",
            f"Proposal {proposal_id} marked as rolled back",
            {"subsystem": subsystem, "snapshot_dir": snapshot_dir},
        )
