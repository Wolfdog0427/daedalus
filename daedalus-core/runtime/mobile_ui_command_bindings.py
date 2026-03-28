# runtime/mobile_ui_command_bindings.py

from __future__ import annotations
from typing import Dict, Any, Optional
import requests


_DEFAULT_TIMEOUT = 10  # seconds


class MobileUICommandBindings:
    """
    Mobile UI Command Bindings 1.2

    Responsibilities:
      - Map UI action commands to HTTP calls to the Web Router
      - Provide a clean, declarative command interface for the mobile app
      - Authenticate every request with the X-Daedalus-Key header
      - Keep networking logic separate from UI rendering logic
      - Ensure all commands return structured JSON responses

    Note: ``base_url`` should include the ``/api`` prefix when connecting
    through the kernel HTTP server (e.g. ``http://host:8000/api``).
    """

    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        verify_tls: bool = True,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        self._verify_tls = verify_tls
        self._timeout = timeout

        self.command_map = {
            "approve_proposal": self.approve_proposal,
            "reject_proposal": self.reject_proposal,
            "restore_snapshot": self.restore_snapshot,
            "validate": self.run_validation,
            "compute_integrity": self.compute_integrity,
            "mark_notification_read": self.mark_notification_read,
        }

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_token:
            h["X-Daedalus-Key"] = self._auth_token
        return h

    def _post(self, url: str, json_body: Any = None) -> Dict[str, Any]:
        resp = requests.post(
            url,
            json=json_body,
            headers=self._headers(),
            verify=self._verify_tls,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------
    # Command Dispatcher
    # ------------------------------------------------------------

    def dispatch(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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
        return self._post(f"{self.base_url}/proposal/{pid}/approve")

    def reject_proposal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pid = payload.get("proposal_id")
        if not pid:
            return {"error": "Missing proposal_id"}
        return self._post(f"{self.base_url}/proposal/{pid}/reject")

    def restore_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sid = payload.get("snapshot_id")
        if not sid:
            return {"error": "Missing snapshot_id"}
        return self._post(
            f"{self.base_url}/restore/{sid}",
            json_body={"keys": payload.get("keys")},
        )

    def run_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"{self.base_url}/validate")

    def compute_integrity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"{self.base_url}/integrity/compute")

    def mark_notification_read(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        nid = payload.get("notification_id")
        if not nid:
            return {"error": "Missing notification_id"}
        return self._post(
            f"{self.base_url}/notifications/{nid}/read",
        )


# ------------------------------------------------------------
# Factory helper
# ------------------------------------------------------------

def create_mobile_command_bindings(
    base_url: str,
    auth_token: Optional[str] = None,
    verify_tls: bool = True,
) -> MobileUICommandBindings:
    """Create command bindings.

    ``base_url`` should include ``/api`` when connecting through the
    kernel server (e.g. ``http://host:8000/api``).
    """
    return MobileUICommandBindings(
        base_url, auth_token=auth_token, verify_tls=verify_tls,
    )
