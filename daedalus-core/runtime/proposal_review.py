# runtime/proposal_review.py

from __future__ import annotations
import threading
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
        self._lock = threading.Lock()
        self.proposals: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # Registry Helpers
    # ------------------------------------------------------------

    def _register(self, proposal: Dict[str, Any]):
        pid = proposal.get("id")
        if not pid:
            return
        with self._lock:
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
        with self._lock:
            return [dict(p) for p in self.proposals.values()]

    def list_pending(self) -> List[Dict[str, Any]]:
        """
        Return proposals awaiting approval.
        """
        with self._lock:
            return [
                dict(p) for p in self.proposals.values()
                if p.get("status") == "pending_review"
            ]

    _TERMINAL_STATUSES = frozenset({"executed", "rolled_back"})
    _APPROVABLE = frozenset({"pending_review"})
    _REJECTABLE = frozenset({"pending_review", "approved"})

    def approve(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Approve a proposal. Only pending_review proposals can be approved.
        """
        with self._lock:
            if pid not in self.proposals:
                return None
            current = self.proposals[pid].get("status")
            if current not in self._APPROVABLE:
                return dict(self.proposals[pid])
            self._update_status(pid, "approved")
            return dict(self.proposals[pid])

    def reject(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Reject a proposal. Pending or approved proposals can be rejected.
        """
        with self._lock:
            if pid not in self.proposals:
                return None
            current = self.proposals[pid].get("status")
            if current in self._TERMINAL_STATUSES:
                return dict(self.proposals[pid])
            self._update_status(pid, "rejected")
            return dict(self.proposals[pid])

    def mark_executed(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Mark a proposal as executed (future execution engine will call this).
        """
        with self._lock:
            if pid not in self.proposals:
                return None
            self._update_status(pid, "executed")
            return dict(self.proposals[pid])

    def mark_rolled_back(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Mark a proposal as rolled back (called by rollback engine).
        """
        with self._lock:
            if pid not in self.proposals:
                return None
            self._update_status(pid, "rolled_back")
            return dict(self.proposals[pid])

    def get(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single proposal by ID.
        """
        with self._lock:
            p = self.proposals.get(pid)
            return dict(p) if p is not None else None


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
proposal_review = ProposalReviewSystem()
