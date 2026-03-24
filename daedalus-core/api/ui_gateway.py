# api/ui_gateway.py

from __future__ import annotations
from typing import Dict, Any

from api.ui_router import route
from runtime.logging_manager import log_event


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    try:
        log_event("ui_gateway", "Incoming request", request)
        response = route(request)
        log_event("ui_gateway", "Outgoing response", {"command": request.get("command")})
        return response

    except Exception as e:
        log_event("ui_gateway", "Gateway error", {"error": str(e), "request": request})
        return {
            "version": "1.2.0",
            "error": "gateway_error",
            "message": str(e),
        }
