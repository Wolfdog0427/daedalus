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

    return {
        "ok": True,
        "version": contract["version"],
        "command": command,
        "schema": schema,
        "payload": payload,
    }


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
        # Build thresholds panel payload
        gov_state = governor.get_state()
        state = status()

        thresholds = {
            "drift_threshold_escalate": governor.drift_threshold_escalate,
            "drift_threshold_deescalate": governor.drift_threshold_deescalate,
            "stability_threshold_escalate": governor.stability_threshold_escalate,
            "stability_threshold_deescalate": governor.stability_threshold_deescalate,
            "readiness_min_for_escalation": governor.readiness_min_for_escalation,
            "readiness_min_for_autonomous": governor.readiness_min_for_autonomous,
        }

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

    return {
        "ok": False,
        "version": get_contract()["version"],
        "error": f"Unknown command: {command}",
        "supported_commands": list(get_contract()["commands"].keys()),
    }
