# knowledge/patch_actions/subsystem_improvement.py

from __future__ import annotations

from typing import Any, Dict, List
import os
import json
from datetime import datetime


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_name(name: str) -> str:
    """Reject path separators and traversal sequences."""
    sanitized = name.replace("\x00", "")
    sanitized = sanitized.replace("..", "").replace("/", "_").replace("\\", "_")
    if not sanitized:
        raise ValueError(f"Invalid name: {name!r}")
    return sanitized


def sandbox_subsystem_improvement(
    action: Dict[str, Any],
    sandbox_root: str,
    context: Dict[str, Any],
) -> List[str]:
    """
    Sandbox handler for subsystem_improvement.

    For now:
    - Writes a sandbox-only JSON file describing the intended change.
    """
    errors: List[str] = []

    target = action.get("target")
    tier = action.get("tier")
    if not target:
        return ["subsystem_improvement: missing 'target'"]

    subsystem_dir = os.path.join(sandbox_root, "subsystems")
    os.makedirs(subsystem_dir, exist_ok=True)

    target = _safe_name(target)
    note_path = os.path.join(subsystem_dir, f"{target}.sandbox.json")
    payload = {
        "timestamp": _now_iso(),
        "action": "subsystem_improvement",
        "target": target,
        "tier": tier,
        "context": context,
        "notes": "Sandbox-only preview of subsystem improvement.",
    }

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        errors.append(f"subsystem_improvement: failed to write sandbox file: {e}")

    return errors


def live_subsystem_improvement(
    action: Dict[str, Any],
    context: Dict[str, Any],
) -> List[str]:
    """
    Live handler for subsystem_improvement.

    For now:
    - Writes/updates data/subsystems/<target>.json with tuning metadata.
    """
    errors: List[str] = []

    target = action.get("target")
    tier = action.get("tier")
    if not target:
        return ["subsystem_improvement: missing 'target'"]

    base_dir = os.path.join("data", "subsystems")
    os.makedirs(base_dir, exist_ok=True)

    target = _safe_name(target)
    config_path = os.path.join(base_dir, f"{target}.json")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}
    else:
        config = {}

    tuning = config.get("tuning", {})
    tuning["last_tier"] = tier
    tuning["last_updated"] = _now_iso()
    tuning["last_cycle_id"] = context.get("cycle_id")
    tuning["last_proposal_id"] = context.get("proposal_id")
    tuning["note"] = "Automatic subsystem improvement placeholder."

    config["tuning"] = tuning

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        errors.append(f"subsystem_improvement: failed to write live config: {e}")

    return errors


def rollback_subsystem_improvement(
    action: Dict[str, Any],
    context: Dict[str, Any],
) -> List[str]:
    """
    Action-specific rollback hook.

    Central rollback (restoring 'before' snapshots) is already handled
    in patch_applier; this is here for any extra cleanup if needed.
    For now, it does nothing and always succeeds.
    """
    return []
