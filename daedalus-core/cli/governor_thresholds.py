# cli/governor_thresholds.py

from __future__ import annotations
import json
from api.ui_gateway import handle_request


def fetch_signals() -> dict:
    resp = handle_request({"command": "status", "args": {}})
    payload = resp.get("payload", {})
    return {
        "drift": payload.get("drift", {}),
        "stability": payload.get("stability", {}),
    }


def render_governor_thresholds(governor) -> str:
    state_resp = handle_request({"command": "status", "args": {}})
    gov_state = state_resp.get("payload", {}).get("governor", {})
    signals = fetch_signals()

    thresholds = {
        "drift_threshold_escalate": governor.drift_threshold_escalate,
        "drift_threshold_deescalate": governor.drift_threshold_deescalate,
        "stability_threshold_escalate": governor.stability_threshold_escalate,
        "stability_threshold_deescalate": governor.stability_threshold_deescalate,
        "readiness_min_for_escalation": governor.readiness_min_for_escalation,
        "readiness_min_for_autonomous": governor.readiness_min_for_autonomous,
    }

    panel = {
        "current_tier": gov_state.get("tier"),
        "strict_mode": gov_state.get("strict_mode"),
        "thresholds": thresholds,
        "current_signals": signals,
    }

    pretty = json.dumps(panel, indent=2)
    return f"=== GOVERNOR THRESHOLDS ===\n{pretty}\n"
