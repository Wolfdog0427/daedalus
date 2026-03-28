# runtime/startup_diagnostics.py

from __future__ import annotations
from typing import Any, Dict
import os
import json

from runtime.logging_manager import log_event
from runtime.state_sources import fetch_state


REQUIRED_DIRS = [
    "data",
    "data/audit",
    "data/cockpit",
    "data/patch_history",
]

REQUIRED_FILES = [
    "data/patch_history/history.json",
]


def check_directories() -> Dict[str, Any]:
    results = {}
    for d in REQUIRED_DIRS:
        exists = os.path.isdir(d)
        results[d] = exists
    return results


def check_files() -> Dict[str, Any]:
    results = {}
    for f in REQUIRED_FILES:
        exists = os.path.isfile(f)
        results[f] = exists
    return results


def check_json_integrity(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _bootstrap_required_dirs() -> None:
    """Create required data directories and seed files on first launch."""
    for d in REQUIRED_DIRS:
        os.makedirs(d, exist_ok=True)
    for f in REQUIRED_FILES:
        if not os.path.isfile(f):
            os.makedirs(os.path.dirname(f), exist_ok=True)
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(_seed_content(f), fh, indent=2)


def _seed_content(path: str) -> Any:
    if path.endswith("history.json"):
        return {
            "total_cycles": 0,
            "successful_patches": 0,
            "failed_patches": 0,
            "reverted_patches": 0,
            "failed_high_level_cycles": 0,
            "failed_tier2_cycles": 0,
            "recent_failures": [],
        }
    return {}


def check_patch_history_integrity() -> bool:
    path = "data/patch_history/history.json"
    return check_json_integrity(path)


def check_state_sources() -> Dict[str, Any]:
    try:
        state = fetch_state()
        return {"ok": True, "state": state}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_startup_diagnostics() -> Dict[str, Any]:
    """
    Perform a full system readiness check.
    """

    log_event("startup", "Running startup diagnostics", {})

    _bootstrap_required_dirs()

    dirs = check_directories()
    files = check_files()
    patch_history_ok = check_patch_history_integrity()
    state_ok = check_state_sources()

    readiness = {
        "directories": dirs,
        "files": files,
        "patch_history_integrity": patch_history_ok,
        "state_sources_ok": state_ok["ok"],
        "state_error": state_ok.get("error"),
    }

    log_event("startup", "Startup diagnostics complete", readiness)
    return readiness
