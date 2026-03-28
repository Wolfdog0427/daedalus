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
    except (json.JSONDecodeError, OSError, ValueError):
        return None
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

    try:
        while True:
            status = handle_request({"command": "status", "args": {}})
            readiness = handle_request({"command": "readiness", "args": {}})

            os.system("cls" if os.name == "nt" else "clear")

            print("=== ASSISTANT WATCH MODE ===")
            print(f"Interval: {interval}s")
            print("")

            print("System Status")
            print("-------------")
            if status.get("ok") is False:
                print(f"ERROR: {status.get('error', 'unknown')}")
            else:
                print(json.dumps(status.get("payload", {}), indent=2))
            print("")

            print("Readiness")
            print("---------")
            if readiness.get("ok") is False:
                print(f"ERROR: {readiness.get('error', 'unknown')}")
            else:
                print(json.dumps(readiness.get("payload", {}), indent=2))
            print("")

            print(_render_thresholds_panel())
            print("")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")


def watch_telemetry(interval: float = 1.0) -> None:
    """Stream raw SHO cycle telemetry via the runtime WatchMode."""
    try:
        from runtime.watch_mode import watch_mode as _wm
        _wm.interval = interval
        _wm.start()
    except ImportError:
        print("WatchMode module not available. Falling back to standard watch.")
        watch(interval=interval)
