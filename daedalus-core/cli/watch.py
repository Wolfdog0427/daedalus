# cli/watch.py

from __future__ import annotations
import time
import json
import os
from typing import Dict, Any

from api.ui_gateway import handle_request
from governor.singleton import governor


CONFIG_PATH = "config/governor_thresholds.json"


def _load_persisted_thresholds() -> Dict[str, Any] | None:
    if not os.path.exists(CONFIG_PATH):
        return None

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("thresholds")
    except Exception:
        return None


def _detect_unsaved_changes(current: Dict[str, Any], persisted: Dict[str, Any] | None) -> bool:
    if persisted is None:
        return True  # nothing saved yet
    return current != persisted


def _render_thresholds_panel() -> str:
    current = {
        "drift_threshold_escalate": governor.drift_threshold_escalate,
        "drift_threshold_deescalate": governor.drift_threshold_deescalate,
        "stability_threshold_escalate": governor.stability_threshold_escalate,
        "stability_threshold_deescalate": governor.stability_threshold_deescalate,
        "readiness_min_for_escalation": governor.readiness_min_for_escalation,
        "readiness_min_for_autonomous": governor.readiness_min_for_autonomous,
    }

    persisted = _load_persisted_thresholds()
    unsaved = _detect_unsaved_changes(current, persisted)

    lines = []
    lines.append("Governor Thresholds")
    lines.append("-------------------")

    for k, v in current.items():
        lines.append(f"{k}: {v}")

    lines.append("")
    lines.append("Persistence Status")
    lines.append("------------------")

    if persisted is None:
        lines.append("No persisted thresholds found")
    else:
        lines.append("Persisted thresholds loaded")

    if unsaved:
        lines.append("⚠ Unsaved changes detected")
    else:
        lines.append("✓ All changes saved")

    return "\n".join(lines)


def watch(interval: float = 2.0) -> None:
    """
    Live dashboard showing system status, thresholds, and governor state.
    """

    while True:
        status = handle_request({"command": "status", "args": {}})
        readiness = handle_request({"command": "readiness", "args": {}})

        os.system("cls" if os.name == "nt" else "clear")

        print("=== ASSISTANT WATCH MODE ===")
        print(f"Interval: {interval}s")
        print("")

        # ------------------------------------------------------------
        # Status Panel
        # ------------------------------------------------------------
        print("System Status")
        print("-------------")
        print(json.dumps(status.get("payload", {}), indent=2))
        print("")

        # ------------------------------------------------------------
        # Readiness Panel
        # ------------------------------------------------------------
        print("Readiness")
        print("---------")
        print(json.dumps(readiness.get("payload", {}), indent=2))
        print("")

        # ------------------------------------------------------------
        # Governor Thresholds Panel (unified — live + persistence)
        # ------------------------------------------------------------
        print(_render_thresholds_panel())
        print("")

        time.sleep(interval)
