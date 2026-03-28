from __future__ import annotations
import threading
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

    _MAX_LOG = 500

    def __init__(self):
        self._lock = threading.Lock()
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

        try:
            if not self._governor_allows_execution():
                return None

            # Find approved proposals
            approved = [
                p for p in proposal_review.list_all()
                if p.get("status") == "approved"
            ]

            if not approved:
                return None

            # Execute the first approved proposal
            proposal = approved[0]

            # Perform execution
            result = self._execute_action(proposal)

            # Mark proposal as executed
            proposal_review.mark_executed(proposal["id"])

            with self._lock:
                self.execution_log.append(result)
                if len(self.execution_log) > self._MAX_LOG:
                    self.execution_log[:] = self.execution_log[-self._MAX_LOG:]
                self.last_execution = result

            return result
        finally:
            try:
                hem_transition_to_postcheck()
            except Exception:
                pass
            try:
                hem_run_post_engagement_checks()
            except Exception:
                pass

    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.last_execution

    def get_execution_log(self):
        with self._lock:
            return list(self.execution_log)

    def clear_log(self) -> None:
        with self._lock:
            self.execution_log.clear()
            self.last_execution = None


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
execution_engine = ExecutionEngine()
