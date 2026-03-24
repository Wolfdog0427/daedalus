# api/dashboard_endpoints.py

from __future__ import annotations
from typing import Dict, Any

from api.ui_gateway import handle_request


def get_dashboard_overview() -> Dict[str, Any]:
    """
    High-level overview for dashboard:
    - drift
    - stability
    - readiness
    - patch history
    """
    resp = handle_request({"command": "health", "args": {}})
    return resp["payload"] if "payload" in resp else resp


def get_dashboard_status() -> Dict[str, Any]:
    """
    Compact status for dashboard header.
    """
    resp = handle_request({"command": "status", "args": {}})
    return resp["payload"] if "payload" in resp else resp
