# runtime/proposal_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time

# FIX: import governor instance from the singleton module
from governor.singleton import governor

from runtime.maintenance_scheduler import maintenance_scheduler


class ProposalEngine:
    """
    Proposal Engine 1.0

    Responsibilities:
      - Convert maintenance advisories into structured proposals
      - Respect governor tier and strict mode
      - Never apply changes directly
      - Prepare proposals for human approval or SHO Tier 3 execution
      - Remain safe, deterministic, and auditable
    """

    def __init__(self):
        self.last_proposal: Optional[Dict[str, Any]] = None
        self.proposal_id_counter = 0

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _new_id(self) -> str:
        self.proposal_id_counter += 1
        return f"proposal_{self.proposal_id_counter}"

    def _governor_allows_proposals(self) -> bool:
        """
        Governor must allow proposal generation.
        Tier 1: No proposals
        Tier 2: Low-risk proposals only
        Tier 3: Full proposals allowed
        """
        if governor.strict_mode:
            return False

        return governor.tier >= 2

    # ------------------------------------------------------------
    # Proposal Construction
    # ------------------------------------------------------------

    def _build_proposal(self, advisory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a maintenance advisory into a structured proposal.
        """

        proposal = {
            "id": self._new_id(),
            "timestamp": time.time(),
            "source": "maintenance_scheduler",
            "priority": advisory.get("priority", "low"),
            "action": advisory.get("action"),
            "reason": advisory.get("reason"),
            "details": advisory.get("details", {}),
            "status": "pending_review",
            "requires_approval": True,
        }

        return proposal

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def tick(self) -> Optional[Dict[str, Any]]:
        """
        Generate a proposal if:
          - Governor allows it
          - Maintenance scheduler has advisories
          - No proposal is currently pending
        """

        # Governor must allow proposals
        if not self._governor_allows_proposals():
            return None

        # Check maintenance advisories
        advisory = maintenance_scheduler.recommendations
        if not advisory or "action" not in advisory:
            return None

        # Avoid generating duplicate proposals
        if self.last_proposal and self.last_proposal.get("status") == "pending_review":
            return self.last_proposal

        # Build new proposal
        proposal = self._build_proposal(advisory)
        self.last_proposal = proposal

        return proposal

    def get_last_proposal(self) -> Optional[Dict[str, Any]]:
        return self.last_proposal


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
proposal_engine = ProposalEngine()
