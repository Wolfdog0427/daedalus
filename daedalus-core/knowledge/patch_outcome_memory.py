# knowledge/patch_outcome_memory.py

from __future__ import annotations

import os
import json
import tempfile
from datetime import datetime
from typing import Any, Dict, List


MEMORY_ROOT = os.path.join("data", "learning")
SUBSYSTEM_MEMORY = os.path.join(MEMORY_ROOT, "subsystems")
ACTION_MEMORY = os.path.join(MEMORY_ROOT, "actions")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure(path: str) -> None:
    os.makedirs(path, exist_ok=True)


_MAX_HISTORY = 500


def _safe_name(name: str) -> str:
    """Reject path separators and traversal sequences."""
    sanitized = name.replace("\x00", "")
    sanitized = sanitized.replace("..", "").replace("/", "_").replace("\\", "_")
    if not sanitized:
        raise ValueError(f"Invalid name: {name!r}")
    return sanitized


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError, ValueError):
        return {}


def _save(path: str, data: Dict[str, Any]) -> None:
    _ensure(os.path.dirname(path))
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(path), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------
# Outcome Scoring
# ---------------------------------------------------------

def score_outcome(patch_result: Dict[str, Any]) -> int:
    """
    Assign a numeric score to the patch outcome.
    """
    status = patch_result.get("status")
    details = patch_result.get("details", {})

    if status == "success":
        return +2

    # Failure cases
    if details.get("phase") == "validation":
        return -3
    if details.get("rolled_back"):
        return -2
    return -1


# ---------------------------------------------------------
# Subsystem Learning
# ---------------------------------------------------------

def update_subsystem_memory(
    subsystem: str,
    plan: Dict[str, Any],
    patch_result: Dict[str, Any],
    validation: Dict[str, Any],
) -> None:
    """
    Update subsystem reliability profile.
    """
    safe_subsystem = _safe_name(subsystem)
    path = os.path.join(SUBSYSTEM_MEMORY, f"{safe_subsystem}.json")
    data = _load(path)

    score = score_outcome(patch_result)

    history = data.get("history", [])
    history.append(
        {
            "timestamp": _now_iso(),
            "tier": plan.get("tier"),
            "actions": plan.get("planned_actions", []),
            "patch_result": patch_result,
            "validation": validation,
            "score": score,
        }
    )

    data["history"] = history[-_MAX_HISTORY:]
    data["success_rate"] = _compute_success_rate(history)
    data["avg_score"] = _compute_avg_score(history)
    data["rollback_rate"] = _compute_rollback_rate(history)

    _save(path, data)


# ---------------------------------------------------------
# Action-Type Learning
# ---------------------------------------------------------

def update_action_memory(
    action_type: str,
    plan: Dict[str, Any],
    patch_result: Dict[str, Any],
    validation: Dict[str, Any],
) -> None:
    """
    Update action-type reliability profile.
    """
    safe_action_type = _safe_name(action_type)
    path = os.path.join(ACTION_MEMORY, f"{safe_action_type}.json")
    data = _load(path)

    score = score_outcome(patch_result)

    history = data.get("history", [])
    history.append(
        {
            "timestamp": _now_iso(),
            "tier": plan.get("tier"),
            "patch_result": patch_result,
            "validation": validation,
            "score": score,
        }
    )

    data["history"] = history[-_MAX_HISTORY:]
    data["success_rate"] = _compute_success_rate(history)
    data["avg_score"] = _compute_avg_score(history)
    data["rollback_rate"] = _compute_rollback_rate(history)

    _save(path, data)


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def _compute_success_rate(history: List[Dict[str, Any]]) -> float:
    if not history:
        return 0.0
    successes = sum(1 for h in history if h["patch_result"]["status"] == "success")
    return successes / len(history)


def _compute_avg_score(history: List[Dict[str, Any]]) -> float:
    if not history:
        return 0.0
    return sum(h["score"] for h in history) / len(history)


def _compute_rollback_rate(history: List[Dict[str, Any]]) -> float:
    if not history:
        return 0.0
    rollbacks = sum(
        1
        for h in history
        if h.get("patch_result", {}).get("details", {}).get("rolled_back")
    )
    return rollbacks / len(history)


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def record_outcome(
    plan: Dict[str, Any],
    patch_result: Dict[str, Any],
) -> None:
    """
    Record the outcome of a patch attempt into subsystem and action memory.
    """
    validation = patch_result.get("details", {}).get("validation", {})

    for action in plan.get("planned_actions", []):
        subsystem = action.get("target")
        action_type = action.get("type")

        if subsystem:
            update_subsystem_memory(subsystem, plan, patch_result, validation)

        if action_type:
            update_action_memory(action_type, plan, patch_result, validation)
