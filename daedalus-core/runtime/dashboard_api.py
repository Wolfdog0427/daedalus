from __future__ import annotations
from typing import Dict, Any

from runtime.system_console import (
    status,
    health,
    run_scheduler,
)

from runtime.proposal_review import proposal_review
from runtime.execution_engine import execution_engine
from runtime.rollback_engine import rollback_engine
from runtime.snapshot_engine import snapshot_engine
from runtime.restoration_engine import restoration_engine
from runtime.integrity_validator import integrity_validator
from runtime.integrity_score_engine import integrity_score_engine

# FIXED
from governor.singleton import governor

# HEM
from hem.hem_state_machine import hem_get_state


class DashboardAPI:
    """
    Dashboard API 1.0

    Responsibilities:
      - Provide a unified JSON interface for:
          - system status
          - system health
          - scheduler output
          - proposals
          - execution
          - rollback
          - snapshots
          - restoration
          - validation
          - integrity scoring
          - governor state
          - HEM status
      - Serve as the top-level API for UI, CLI, or external agents
    """

    # ------------------------------------------------------------
    # Core Endpoints
    # ------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        return status()

    def get_health(self) -> Dict[str, Any]:
        return health()

    def tick(self) -> Dict[str, Any]:
        """
        Run a full scheduler tick and return the complete system state.
        """
        return run_scheduler()

    # ------------------------------------------------------------
    # Proposal Endpoints
    # ------------------------------------------------------------

    def list_proposals(self) -> Dict[str, Any]:
        return {
            "proposals": proposal_review.list_all()
        }

    # ------------------------------------------------------------
    # Execution Endpoints
    # ------------------------------------------------------------

    def get_execution_log(self) -> Dict[str, Any]:
        return {
            "execution_log": execution_engine.get_execution_log()
        }

    # ------------------------------------------------------------
    # Rollback Endpoints
    # ------------------------------------------------------------

    def get_rollback_log(self) -> Dict[str, Any]:
        return {
            "rollback_log": rollback_engine.get_rollback_log()
        }

    # ------------------------------------------------------------
    # Snapshot Endpoints
    # ------------------------------------------------------------

    def list_snapshots(self) -> Dict[str, Any]:
        return {
            "snapshots": snapshot_engine.list_all()
        }

    # ------------------------------------------------------------
    # Restoration Endpoints
    # ------------------------------------------------------------

    def get_restoration_log(self) -> Dict[str, Any]:
        return {
            "restoration_log": restoration_engine.get_restoration_log()
        }

    # ------------------------------------------------------------
    # Validation Endpoints
    # ------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        return integrity_validator.validate()

    def get_validation_log(self) -> Dict[str, Any]:
        return {
            "validation_log": integrity_validator.get_validation_log()
        }

    # ------------------------------------------------------------
    # Integrity Score Endpoints
    # ------------------------------------------------------------

    def get_integrity_score(self) -> Dict[str, Any]:
        return integrity_score_engine.compute()

    def get_integrity_score_history(self) -> Dict[str, Any]:
        return {
            "integrity_score_history": integrity_score_engine.get_score_history()
        }

    # ------------------------------------------------------------
    # Governor Endpoints
    # ------------------------------------------------------------

    def get_governor_state(self) -> Dict[str, Any]:
        return governor.get_state()

    # ------------------------------------------------------------
    # HEM Endpoints
    # ------------------------------------------------------------

    def get_hem_status(self) -> Dict[str, Any]:
        """
        Return current HEM state (and later, session stats/summary).
        """
        return {
            "current_state": hem_get_state().value,
        }


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
dashboard_api = DashboardAPI()
