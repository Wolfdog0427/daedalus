# runtime/patch_history_manager.py

"""
Patch History Manager (Rewritten)

Tracks:
- Patch successes and failures
- Tier-specific failure counts
- Reverted patches
- Rollback metadata
- Recent failure details

Provides clean interfaces for:
- SHO Patch Flow
- Autonomy Governor
- Diagnostics
- SystemHealth integration
"""

from __future__ import annotations

import threading
from typing import Any, Dict
from datetime import datetime, timezone
import os
import json

from runtime.notification_hooks import (
    notify_patch_reverted,
    notify_patch_failure,
)
from runtime.logging_manager import log_event


HISTORY_DIR = os.path.join("data", "patch_history")
HISTORY_PATH = os.path.join(HISTORY_DIR, "history.json")
_MAX_RECENT_FAILURES = 200
_history_lock = threading.Lock()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _ensure_dir() -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_history() -> Dict[str, Any]:
    return {
        "total_cycles": 0,
        "successful_patches": 0,
        "failed_patches": 0,
        "reverted_patches": 0,
        "failed_high_level_cycles": 0,
        "failed_tier2_cycles": 0,
        "recent_failures": [],
    }


# ------------------------------------------------------------
# Load / Save
# ------------------------------------------------------------

def load_patch_history() -> Dict[str, Any]:
    """
    Load patch history from disk.
    Creates a default history file if missing.
    """
    _ensure_dir()

    if not os.path.exists(HISTORY_PATH):
        history = _default_history()
        save_patch_history(history)
        return history

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt file → reset
        history = _default_history()
        save_patch_history(history)
        return history


def save_patch_history(history: Dict[str, Any]) -> None:
    _ensure_dir()
    rf = history.get("recent_failures")
    if isinstance(rf, list) and len(rf) > _MAX_RECENT_FAILURES:
        history["recent_failures"] = rf[-_MAX_RECENT_FAILURES:]
    try:
        from knowledge._atomic_io import atomic_write_json
        from pathlib import Path
        atomic_write_json(Path(HISTORY_PATH), history)
    except ImportError:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)


# ------------------------------------------------------------
# Recording Patch Results
# ------------------------------------------------------------

def record_patch_result(
    cycle_id: str,
    tier: int,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Record the outcome of a patch attempt.

    result = {
        "status": "success" | "failed" | "not_implemented",
        "details": {...}
    }
    """
    with _history_lock:
        return _record_patch_result_unlocked(cycle_id, tier, result)


def _record_patch_result_unlocked(
    cycle_id: str,
    tier: int,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    history = load_patch_history()
    history["total_cycles"] += 1

    status = result.get("status")
    details = result.get("details", {})

    # -----------------------------
    # Success
    # -----------------------------
    if status == "success":
        history["successful_patches"] += 1

        log_event(
            "patch_success",
            f"Patch succeeded in cycle {cycle_id}",
            {"tier": tier},
        )

    # -----------------------------
    # Failure
    # -----------------------------
    elif status == "failed":
        history["failed_patches"] += 1

        failure_entry = {
            "cycle_id": cycle_id,
            "tier": tier,
            "timestamp": _now_iso(),
            "details": details,
        }
        history["recent_failures"].append(failure_entry)

        log_event(
            "patch_failure",
            f"Patch FAILED in cycle {cycle_id}",
            {"tier": tier, "details": details},
        )

        notify_patch_failure(cycle_id, tier, details)

        # Tier-specific counters
        if tier == 1:
            history["failed_high_level_cycles"] += 1
        elif tier == 2:
            history["failed_tier2_cycles"] += 1

    # -----------------------------
    # Not Implemented
    # -----------------------------
    elif status == "not_implemented":
        log_event(
            "patch_not_implemented",
            f"Patch not implemented in cycle {cycle_id}",
            {"tier": tier},
        )

    save_patch_history(history)
    return history


# ------------------------------------------------------------
# Rollback Recording
# ------------------------------------------------------------

def record_rollback(
    cycle_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Record that a patch was reverted.
    """
    with _history_lock:
        return _record_rollback_unlocked(cycle_id, reason, metadata)


def _record_rollback_unlocked(
    cycle_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    history = load_patch_history()
    history["reverted_patches"] += 1

    entry = {
        "cycle_id": cycle_id,
        "tier": "unknown",
        "timestamp": _now_iso(),
        "details": {
            "reverted": True,
            "reason": reason,
            "metadata": metadata or {},
        },
    }

    history["recent_failures"].append(entry)
    save_patch_history(history)

    log_event(
        "patch_reverted",
        f"Patch reverted in cycle {cycle_id}",
        {"reason": reason, "metadata": metadata},
    )

    notify_patch_reverted(cycle_id, reason)

    return history
