from __future__ import annotations
from typing import Dict, Any, Optional
import time

# FIXED
from governor.singleton import governor

from runtime.proposal_review import proposal_review

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)


class ExecutionEngine:
    """
    Execution Engine 1.0

    Responsibilities:
      - Execute approved proposals safely
      - Enforce governor tier and strict mode
      - Log execution results
      - Support reversible actions (future)
      - Never execute unapproved proposals
      - Never modify system state outside approved actions

    HEM Integration:
      - Enter HEM when executing approved proposals
      - Run post-engagement checks after execution
    """

    def __init__(self):
        self.execution_log = []
        self.last_execution: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------
    # Governor Safety Gate
    # ------------------------------------------------------------

    def _governor_allows_execution(self) -> bool:
        """
        Tier 1: No execution
        Tier 2: Low-risk execution only
        Tier 3: Full execution allowed
        Strict mode: No execution
        """
        if governor.strict_mode:
            return False

        return governor.tier >= 2

    # ------------------------------------------------------------
    # Execution Logic
    # ------------------------------------------------------------

    def _execute_action(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder execution logic.
        In future versions, this will:
          - run diagnostics
          - tune thresholds
          - apply reversible patches
          - update system state safely
        """

        action = proposal.get("action")

        # For now, execution is symbolic and logged only
        result = {
            "proposal_id": proposal["id"],
            "action": action,
            "timestamp": time.time(),
            "status": "executed",
            "notes": f"Action '{action}' executed symbolically.",
        }

        return result

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def tick(self) -> Optional[Dict[str, Any]]:
        """
        Execute the next approved proposal if:
          - Governor allows execution
          - A proposal is approved
          - It has not already been executed
        """

        # --------------------------------------------------------
        # HEM: Enter hostile engagement mode for execution
        # --------------------------------------------------------
        hem_maybe_enter("execution_engine_tick")

        if not self._governor_allows_execution():
            # Even if we don't execute, we still close out HEM cleanly
            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return None

        # Find approved proposals
        approved = [
            p for p in proposal_review.list_all()
            if p.get("status") == "approved"
        ]

        if not approved:
            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return None

        # Execute the first approved proposal
        proposal = approved[0]

        # Perform execution
        result = self._execute_action(proposal)

        # Mark proposal as executed
        proposal_review.mark_executed(proposal["id"])

        # Log execution
        self.execution_log.append(result)
        self.last_execution = result

        # --------------------------------------------------------
        # HEM: Post-checks after execution
        # --------------------------------------------------------
        hem_transition_to_postcheck()
        hem_run_post_engagement_checks()

        return result

    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        return self.last_execution

    def get_execution_log(self):
        return list(self.execution_log)


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
execution_engine = ExecutionEngine()
