# runtime/proposal_review.py

from __future__ import annotations
from typing import Dict, Any, Optional, List
import time

from runtime.proposal_engine import proposal_engine


class ProposalReviewSystem:
    """
    Proposal Review & Approval System 1.0

    Responsibilities:
      - Maintain a registry of all proposals
      - Allow listing, approving, rejecting, and marking proposals as executed
      - Track proposal lifecycle states
      - Provide full auditability
      - Never apply changes directly (execution engine will handle that later)
    """

    def __init__(self):
        self.proposals: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # Registry Helpers
    # ------------------------------------------------------------

    def _register(self, proposal: Dict[str, Any]):
        pid = proposal["id"]
        if pid not in self.proposals:
            self.proposals[pid] = proposal

    def _update_status(self, pid: str, status: str):
        if pid in self.proposals:
            self.proposals[pid]["status"] = status
            self.proposals[pid]["updated_at"] = time.time()

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def ingest_new_proposal(self):
        """
        Pull the latest proposal from the Proposal Engine and register it.
        """
        proposal = proposal_engine.get_last_proposal()
        if proposal:
            self._register(proposal)

    def list_all(self) -> List[Dict[str, Any]]:
        """
        Return all proposals in the registry.
        """
        return list(self.proposals.values())

    def list_pending(self) -> List[Dict[str, Any]]:
        """
        Return proposals awaiting approval.
        """
        return [
            p for p in self.proposals.values()
            if p.get("status") == "pending_review"
        ]

    def approve(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Approve a proposal. Marks it as approved and ready for execution.
        """
        if pid not in self.proposals:
            return None

        self._update_status(pid, "approved")
        return self.proposals[pid]

    def reject(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Reject a proposal. Marks it as rejected.
        """
        if pid not in self.proposals:
            return None

        self._update_status(pid, "rejected")
        return self.proposals[pid]

    def mark_executed(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Mark a proposal as executed (future execution engine will call this).
        """
        if pid not in self.proposals:
            return None

        self._update_status(pid, "executed")
        return self.proposals[pid]

    def get(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single proposal by ID.
        """
        return self.proposals.get(pid)


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
proposal_review = ProposalReviewSystem()
