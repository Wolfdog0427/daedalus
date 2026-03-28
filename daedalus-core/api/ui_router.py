# api/ui_router.py

from __future__ import annotations
from typing import Dict, Any

from api.ui_contract import get_contract
from runtime.system_console import (
    run_cycle,
    run_scheduler,
    health,
    status,
)
from runtime.readiness_score import compute_readiness_score
from governor.governor_trace import get_governor_trace

# FIXED
from governor.singleton import governor

# NEW: tuning module imports
from governor.governor_tuning import (
    set_thresholds,
    save_thresholds,
    load_thresholds,
    reset_thresholds,
)


def _wrap(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    contract = get_contract()
    schema = contract["commands"].get(command)

    ok = payload.get("ok", True) if isinstance(payload, dict) else True

    result: Dict[str, Any] = {
        "ok": ok,
        "version": contract["version"],
        "command": command,
        "schema": schema,
        "payload": payload,
    }
    if not ok and isinstance(payload, dict) and "error" in payload:
        result["error"] = payload["error"]
    return result


def route(request: Dict[str, Any]) -> Dict[str, Any]:
    command = request.get("command")
    args = request.get("args", {}) or {}

    # ------------------------------------------------------------
    # Existing Commands
    # ------------------------------------------------------------

    if command == "status":
        return _wrap("status", status())

    if command == "health":
        return _wrap("health", health())

    if command == "run_cycle":
        return _wrap("run_cycle", run_cycle())

    if command == "run_scheduler":
        return _wrap("run_scheduler", run_scheduler())

    if command == "readiness":
        return _wrap("readiness", compute_readiness_score())

    if command == "governor_trace":
        return _wrap("governor_trace", {"trace": get_governor_trace()})

    if command == "governor_thresholds":
        gov_state = governor.get_state()
        state = status()

        thresholds = gov_state.get("thresholds", {})

        current_signals = {
            "drift": state.get("drift", {}),
            "stability": state.get("stability", {}),
        }

        payload = {
            "current_tier": gov_state.get("tier"),
            "strict_mode": gov_state.get("strict_mode"),
            "thresholds": thresholds,
            "current_signals": current_signals,
        }

        return _wrap("governor_thresholds", payload)

    # ------------------------------------------------------------
    # NEW: Governor Tuning Commands
    # ------------------------------------------------------------

    if command == "governor_set_thresholds":
        if not isinstance(args, dict):
            return _wrap("governor_set_thresholds", {"error": "args must be a JSON object"})
        result = set_thresholds(args)
        return _wrap("governor_set_thresholds", result)

    if command == "governor_save_thresholds":
        result = save_thresholds()
        return _wrap("governor_save_thresholds", result)

    if command == "governor_load_thresholds":
        result = load_thresholds()
        return _wrap("governor_load_thresholds", result)

    if command == "governor_reset_thresholds":
        result = reset_thresholds()
        return _wrap("governor_reset_thresholds", result)

    # ------------------------------------------------------------
    # Unknown Command
    # ------------------------------------------------------------

    return _wrap(command or "unknown", {
        "ok": False,
        "error": f"Unknown command: {command}",
        "supported_commands": list(get_contract()["commands"].keys()),
    })
