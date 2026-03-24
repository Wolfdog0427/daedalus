# runtime/rollback_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time

# FIXED
from governor.singleton import governor

from runtime.execution_engine import execution_engine
from runtime.proposal_review import proposal_review


class RollbackEngine:
    """
    Rollback Engine 1.0

    Responsibilities:
      - Provide safe rollback for executed proposals
      - Maintain a rollback log
      - Enforce governor tier and strict mode
      - Never rollback unexecuted proposals
      - Never modify system state outside approved rollback actions
    """

    def __init__(self):
        self.rollback_log = []
        self.last_rollback: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------
    # Governor Safety Gate
    # ------------------------------------------------------------

    def _governor_allows_rollback(self) -> bool:
        """
        Tier 1: No rollback
        Tier 2: Low-risk rollback only
        Tier 3: Full rollback allowed
        Strict mode: No rollback
        """
        if governor.strict_mode:
            return False

        return governor.tier >= 2

    # ------------------------------------------------------------
    # Rollback Logic
    # ------------------------------------------------------------

    def _rollback_action(self, execution_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder rollback logic.
        In future versions, this will:
          - reverse threshold changes
          - undo diagnostics modifications
          - revert patches
          - restore previous system state
        """

        result = {
            "proposal_id": execution_record["proposal_id"],
            "timestamp": time.time(),
            "status": "rolled_back",
            "notes": (
                f"Rollback performed symbolically for action "
                f"'{execution_record['action']}'."
            ),
        }

        return result

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def rollback(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Roll back a specific executed proposal if:
          - Governor allows rollback
          - Proposal exists and was executed
        """

        if not self._governor_allows_rollback():
            return None

        # Find execution record
        execution_records = execution_engine.get_execution_log()
        record = next(
            (r for r in execution_records if r["proposal_id"] == proposal_id),
            None
        )

        if not record:
            return None

        # Perform rollback
        result = self._rollback_action(record)

        # Log rollback
        self.rollback_log.append(result)
        self.last_rollback = result

        # Mark proposal as rolled back
        proposal_review._update_status(proposal_id, "rolled_back")

        return result

    def get_last_rollback(self) -> Optional[Dict[str, Any]]:
        return self.last_rollback

    def get_rollback_log(self):
        return list(self.rollback_log)


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
rollback_engine = RollbackEngine()
