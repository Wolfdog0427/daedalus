# runtime/approval_interface.py

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from runtime.logging_manager import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        self._lock = threading.Lock()
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.decisions: Dict[str, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # Proposal Retrieval
    # ---------------------------------------------------------

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self.pending.get(proposal_id)
            if p is None:
                p = self.decisions.get(proposal_id)
            return dict(p) if p else None

    def list_pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(p) for p in self.pending.values()]

    # ---------------------------------------------------------
    # Proposal Lifecycle
    # ---------------------------------------------------------

    def approve(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            proposal = self.pending.pop(proposal_id, None)
            if not proposal:
                return {"status": "not_found", "proposal_id": proposal_id}

            proposal["status"] = "approved"
            proposal["decision"] = {
                "decided_by": "user",
                "decided_at": _now_iso(),
                "reason": reason,
            }
            proposal["rolled_back"] = False

            self.decisions[proposal_id] = proposal

        log_event("proposal", f"Proposal {proposal_id} approved", {"reason": reason})
        return {"proposal_id": proposal_id, "status": "approved", "result": dict(proposal)}

    def reject(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
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
        return {"proposal_id": proposal_id, "status": "rejected", "result": dict(proposal)}

    def cancel(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
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
        return {"proposal_id": proposal_id, "status": "cancelled", "result": dict(proposal)}

    # ---------------------------------------------------------
    # Rollback Integration
    # ---------------------------------------------------------

    def mark_rolled_back(self, proposal_id: str, subsystem: str, snapshot_dir: str) -> None:
        """
        Called by SHO Patch Flow when a rollback occurs.
        """
        with self._lock:
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
