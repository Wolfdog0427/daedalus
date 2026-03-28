# api/ui_gateway.py

from __future__ import annotations
from typing import Dict, Any

from api.ui_router import route
from runtime.logging_manager import log_event


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    try:
        try:
            log_event("ui_gateway", "Incoming request", request)
        except Exception:
            pass
        response = route(request)
        try:
            log_event("ui_gateway", "Outgoing response", {"command": request.get("command")})
        except Exception:
            pass
        return response

    except Exception as e:
        try:
            log_event("ui_gateway", "Gateway error", {"error": str(e), "request": request})
        except Exception:
            pass
        try:
            from api.ui_contract import UI_VERSION
            version = UI_VERSION
        except ImportError:
            version = "unknown"
        return {
            "ok": False,
            "version": version,
            "error": "gateway_error",
            "message": "An internal error occurred. Check server logs for details.",
        }
