# runtime/command_console.py

from __future__ import annotations
from typing import Dict, Any, Optional

from runtime.proposal_review import proposal_review
from runtime.execution_engine import execution_engine
from runtime.rollback_engine import rollback_engine
from runtime.snapshot_engine import snapshot_engine
from runtime.restoration_engine import restoration_engine
from runtime.integrity_validator import integrity_validator
from runtime.integrity_score_engine import integrity_score_engine

from governor.singleton import governor


class CommandConsole:
    """
    Command Console 1.0

    Responsibilities:
      - Provide write-side control over:
          - proposals
          - execution
          - rollback
          - restoration
          - snapshots
          - governor configuration
          - validation
          - integrity scoring
      - Serve as the authoritative command interface for UI/CLI/agents
      - Enforce safety and governor rules
    """

    # ------------------------------------------------------------
    # Proposal Commands
    # ------------------------------------------------------------

    def approve_proposal(self, proposal_id: str) -> Dict[str, Any]:
        result = proposal_review.approve(proposal_id)
        return {"approved": result}

    def reject_proposal(self, proposal_id: str) -> Dict[str, Any]:
        result = proposal_review.reject(proposal_id)
        return {"rejected": result}

    # ------------------------------------------------------------
    # Execution Commands
    # ------------------------------------------------------------

    def execute_next(self) -> Dict[str, Any]:
        """
        Force execution of the next approved proposal.
        Governor rules still apply.
        """
        result = execution_engine.tick()
        return {"execution": result}

    # ------------------------------------------------------------
    # Rollback Commands
    # ------------------------------------------------------------

    def rollback(self, proposal_id: str) -> Dict[str, Any]:
        result = rollback_engine.rollback(proposal_id)
        return {"rollback": result}

    # ------------------------------------------------------------
    # Snapshot Commands
    # ------------------------------------------------------------

    def capture_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        sid = snapshot_engine.capture(state)
        return {"snapshot_id": sid}

    # ------------------------------------------------------------
    # Restoration Commands
    # ------------------------------------------------------------

    def restore(self, snapshot_id: str, keys: Optional[list[str]] = None) -> Dict[str, Any]:
        result = restoration_engine.restore(snapshot_id, keys)
        return {"restoration": result}

    # ------------------------------------------------------------
    # Validation Commands
    # ------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        result = integrity_validator.validate()
        return {"validation": result}

    # ------------------------------------------------------------
    # Integrity Score Commands
    # ------------------------------------------------------------

    def compute_integrity_score(self) -> Dict[str, Any]:
        result = integrity_score_engine.compute()
        return {"integrity_score": result}

    # ------------------------------------------------------------
    # Governor Commands
    # ------------------------------------------------------------

    def set_governor_tier(self, tier: int) -> Dict[str, Any]:
        governor.set_tier(tier)
        return {"governor_state": governor.get_state()}

    def enable_strict_mode(self) -> Dict[str, Any]:
        governor.enable_strict_mode()
        return {"governor_state": governor.get_state()}

    def disable_strict_mode(self) -> Dict[str, Any]:
        governor.disable_strict_mode()
        return {"governor_state": governor.get_state()}

    # ------------------------------------------------------------
    # Log Management Commands
    # ------------------------------------------------------------

    def clear_execution_log(self) -> Dict[str, Any]:
        execution_engine.clear_log()
        return {"execution_log_cleared": True}

    def clear_rollback_log(self) -> Dict[str, Any]:
        rollback_engine.clear_log()
        return {"rollback_log_cleared": True}

    def clear_restoration_log(self) -> Dict[str, Any]:
        restoration_engine.clear_log()
        return {"restoration_log_cleared": True}

    def clear_validation_log(self) -> Dict[str, Any]:
        integrity_validator.clear_log()
        return {"validation_log_cleared": True}

    def clear_integrity_score_history(self) -> Dict[str, Any]:
        integrity_score_engine.clear_log()
        return {"integrity_score_history_cleared": True}


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
command_console = CommandConsole()
