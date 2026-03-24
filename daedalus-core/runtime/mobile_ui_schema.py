# runtime/mobile_ui_schema.py

from __future__ import annotations
from typing import Dict, Any, List

from runtime.dashboard_api import dashboard_api
# FIXED
from governor.singleton import governor


class MobileUISchema:
    """
    Mobile UI Schema 1.0

    Responsibilities:
      - Provide a declarative JSON schema describing:
          - dashboard layout
          - cards
          - panels
          - metrics
          - logs
          - proposal review UI
          - execution controls
          - governor controls
      - Serve as the UI contract for the mobile app
      - Keep UI logic separate from system logic
    """

    # ------------------------------------------------------------
    # Core Schema
    # ------------------------------------------------------------

    def get_schema(self) -> Dict[str, Any]:
        """
        Returns the full UI schema describing the mobile dashboard.
        """

        return {
            "version": "1.0",
            "layout": [
                self._card_system_health(),
                self._card_integrity_score(),
                self._card_governor_state(),
                self._panel_proposals(),
                self._panel_execution_log(),
                self._panel_snapshots(),
                self._panel_restoration_log(),
                self._panel_integrity_validation(),
                self._panel_integrity_history(),
            ],
        }

    # ------------------------------------------------------------
    # Cards (top-level summary)
    # ------------------------------------------------------------

    def _card_system_health(self) -> Dict[str, Any]:
        health = dashboard_api.get_health()
        return {
            "type": "card",
            "title": "System Health",
            "style": "status",
            "metrics": [
                {"label": "Drift", "value": health["drift"]["level"]},
                {"label": "Stability", "value": health["stability"]["level"]},
                {"label": "Readiness", "value": health["readiness"]},
            ],
        }

    def _card_integrity_score(self) -> Dict[str, Any]:
        score = dashboard_api.get_integrity_score()
        return {
            "type": "card",
            "title": "Integrity Score",
            "style": "score",
            "score": score["score"],
            "components": score["components"],
        }

    def _card_governor_state(self) -> Dict[str, Any]:
        state = governor.get_state()
        return {
            "type": "card",
            "title": "Governor",
            "style": "governor",
            "tier": state["tier"],
            "strict_mode": state["strict_mode"],
        }

    # ------------------------------------------------------------
    # Panels (expandable sections)
    # ------------------------------------------------------------

    def _panel_proposals(self) -> Dict[str, Any]:
        proposals = dashboard_api.list_proposals()["proposals"]
        return {
            "type": "panel",
            "title": "Proposals",
            "items": [
                {
                    "id": p["id"],
                    "status": p["status"],
                    "action": p.get("action"),
                    "metadata": p.get("metadata", {}),
                }
                for p in proposals
            ],
            "actions": [
                {"label": "Approve", "command": "approve_proposal"},
                {"label": "Reject", "command": "reject_proposal"},
            ],
        }

    def _panel_execution_log(self) -> Dict[str, Any]:
        log = dashboard_api.get_execution_log()["execution_log"]
        return {
            "type": "panel",
            "title": "Execution Log",
            "items": log,
        }

    def _panel_snapshots(self) -> Dict[str, Any]:
        snaps = dashboard_api.list_snapshots()["snapshots"]
        return {
            "type": "panel",
            "title": "Snapshots",
            "items": snaps,
            "actions": [
                {"label": "Restore", "command": "restore_snapshot"},
            ],
        }

    def _panel_restoration_log(self) -> Dict[str, Any]:
        log = dashboard_api.get_restoration_log()["restoration_log"]
        return {
            "type": "panel",
            "title": "Restoration Log",
            "items": log,
        }

    def _panel_integrity_validation(self) -> Dict[str, Any]:
        log = dashboard_api.get_validation_log()["validation_log"]
        return {
            "type": "panel",
            "title": "Integrity Validation",
            "items": log,
            "actions": [
                {"label": "Run Validation", "command": "validate"},
            ],
        }

    def _panel_integrity_history(self) -> Dict[str, Any]:
        history = dashboard_api.get_integrity_score_history()["integrity_score_history"]
        return {
            "type": "panel",
            "title": "Integrity Score History",
            "items": history,
        }


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
mobile_ui_schema = MobileUISchema()
