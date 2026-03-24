# runtime/mobile_ui_command_bindings.py

from __future__ import annotations
from typing import Dict, Any, Optional
import requests


class MobileUICommandBindings:
    """
    Mobile UI Command Bindings 1.0

    Responsibilities:
      - Map UI action commands to HTTP calls to the Web Router
      - Provide a clean, declarative command interface for the mobile app
      - Keep networking logic separate from UI rendering logic
      - Ensure all commands return structured JSON responses
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

        # Command → handler mapping
        self.command_map = {
            "approve_proposal": self.approve_proposal,
            "reject_proposal": self.reject_proposal,
            "restore_snapshot": self.restore_snapshot,
            "validate": self.run_validation,
            "compute_integrity": self.compute_integrity,
        }

    # ------------------------------------------------------------
    # Command Dispatcher
    # ------------------------------------------------------------

    def dispatch(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a UI command to the appropriate handler.
        """
        handler = self.command_map.get(command)
        if not handler:
            return {"error": f"Unknown command: {command}"}

        return handler(payload)

    # ------------------------------------------------------------
    # Command Handlers
    # ------------------------------------------------------------

    def approve_proposal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pid = payload.get("proposal_id")
        if not pid:
            return {"error": "Missing proposal_id"}

        url = f"{self.base_url}/proposal/{pid}/approve"
        return requests.post(url).json()

    def reject_proposal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pid = payload.get("proposal_id")
        if not pid:
            return {"error": "Missing proposal_id"}

        url = f"{self.base_url}/proposal/{pid}/reject"
        return requests.post(url).json()

    def restore_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sid = payload.get("snapshot_id")
        keys = payload.get("keys")

        if not sid:
            return {"error": "Missing snapshot_id"}

        url = f"{self.base_url}/restore/{sid}"
        return requests.post(url, json={"keys": keys}).json()

    def run_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/validate"
        return requests.post(url).json()

    def compute_integrity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/integrity/compute"
        return requests.post(url).json()


# ------------------------------------------------------------
# Factory helper
# ------------------------------------------------------------

def create_mobile_command_bindings(base_url: str) -> MobileUICommandBindings:
    return MobileUICommandBindings(base_url)
