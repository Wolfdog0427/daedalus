# runtime/tier3_snapshots.py
"""
Immutable governance snapshots.

A snapshot captures the full governance state at a moment in time.
Snapshots are append-only and operator-triggered — they are never
created automatically and never modified once created.
"""

from __future__ import annotations

import copy
import time
import uuid
from typing import Any, Dict, List, Optional

_SNAPSHOT_REGISTRY: List[Dict[str, Any]] = []


# ------------------------------------------------------------------
# Snapshot creation
# ------------------------------------------------------------------

def create_snapshot(
    label: str,
    description: str = "",
) -> Dict[str, Any]:
    """Capture the current governance state as an immutable snapshot."""
    state = _capture_state()

    snapshot = {
        "snapshot_id": str(uuid.uuid4()),
        "label": label,
        "description": description,
        "state": state,
        "created_at": time.time(),
    }
    _SNAPSHOT_REGISTRY.append(snapshot)
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "label": label,
        "description": description,
        "created_at": snapshot["created_at"],
        "summary": _summarize(state),
    }


def _capture_state() -> Dict[str, Any]:
    """Deep-copy the current governance state from all registries."""
    state: Dict[str, Any] = {}

    try:
        from runtime.tier3_environments import list_environments
        state["environments"] = copy.deepcopy(list_environments())
    except Exception:
        state["environments"] = []

    try:
        from runtime.tier3_profiles import list_profiles
        state["profiles"] = copy.deepcopy(list_profiles())
    except Exception:
        state["profiles"] = []

    try:
        from runtime.tier3_policies import get_policies
        state["policies"] = copy.deepcopy(get_policies())
    except Exception:
        state["policies"] = []

    try:
        from runtime.tier3_runbook_templates import list_templates
        state["templates"] = copy.deepcopy(list_templates())
    except Exception:
        state["templates"] = []

    try:
        from runtime.tier3_runbooks import list_runbooks
        state["runbooks"] = copy.deepcopy(list_runbooks())
    except Exception:
        state["runbooks"] = []

    try:
        from runtime.tier3_envpacks import list_envpacks
        state["packs"] = copy.deepcopy(list_envpacks())
    except Exception:
        state["packs"] = []

    try:
        from runtime.tier3_lineage import get_lineage_log
        state["lineage"] = copy.deepcopy(get_lineage_log(1000))
    except Exception:
        state["lineage"] = []

    return state


def _summarize(state: Dict[str, Any]) -> Dict[str, int]:
    return {
        "environments": len(state.get("environments", [])),
        "profiles": len(state.get("profiles", [])),
        "policies": len(state.get("policies", [])),
        "templates": len(state.get("templates", [])),
        "runbooks": len(state.get("runbooks", [])),
        "packs": len(state.get("packs", [])),
        "lineage": len(state.get("lineage", [])),
    }


# ------------------------------------------------------------------
# Query (read-only)
# ------------------------------------------------------------------

def list_snapshots() -> List[Dict[str, Any]]:
    """Return metadata for all snapshots (without full state)."""
    return [
        {
            "snapshot_id": s["snapshot_id"],
            "label": s["label"],
            "description": s.get("description", ""),
            "created_at": s["created_at"],
            "summary": _summarize(s["state"]),
        }
        for s in _SNAPSHOT_REGISTRY
    ]


def get_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Return a full snapshot including state."""
    for s in _SNAPSHOT_REGISTRY:
        if s["snapshot_id"] == snapshot_id:
            return copy.deepcopy(s)
    return None


def get_snapshot_state(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Return only the state dict from a snapshot."""
    for s in _SNAPSHOT_REGISTRY:
        if s["snapshot_id"] == snapshot_id:
            return copy.deepcopy(s["state"])
    return None


def clear_snapshots() -> None:
    """Reset registry (for testing only)."""
    _SNAPSHOT_REGISTRY.clear()
