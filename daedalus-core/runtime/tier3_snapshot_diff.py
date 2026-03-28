# runtime/tier3_snapshot_diff.py
"""
Time-travel diffing between governance snapshots.

Compares two snapshots or a snapshot against the current live state.
All functions are side-effect-free — they never mutate state.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_DIFF_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 200


def get_diff_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_DIFF_LOG[-limit:])


def clear_diff_log() -> None:
    _DIFF_LOG.clear()


# ------------------------------------------------------------------
# Core diff engine
# ------------------------------------------------------------------

def _diff_lists(
    a_items: List[Dict[str, Any]],
    b_items: List[Dict[str, Any]],
    key: str,
) -> Dict[str, Any]:
    """Diff two lists of dicts keyed by *key*."""
    a_map = {item[key]: item for item in a_items if key in item}
    b_map = {item[key]: item for item in b_items if key in item}

    a_keys = set(a_map)
    b_keys = set(b_map)

    added = sorted(b_keys - a_keys)
    removed = sorted(a_keys - b_keys)

    changed: List[Dict[str, Any]] = []
    for k in sorted(a_keys & b_keys):
        if a_map[k] != b_map[k]:
            changed.append({"id": k, "a": a_map[k], "b": b_map[k]})

    return {
        "added": added,
        "removed": removed,
        "changed_count": len(changed),
        "unchanged_count": len(a_keys & b_keys) - len(changed),
    }


_DIMENSION_KEYS = {
    "environments": "env_id",
    "profiles": "profile_id",
    "policies": "policy_id",
    "templates": "template_id",
    "runbooks": "runbook_id",
    "packs": "pack_id",
}


def _diff_states(
    state_a: Dict[str, Any],
    state_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Diff two state dicts across all governance dimensions."""
    dimensions: Dict[str, Any] = {}
    for dim, key in _DIMENSION_KEYS.items():
        a_list = state_a.get(dim, [])
        b_list = state_b.get(dim, [])
        dimensions[dim] = _diff_lists(a_list, b_list, key)

    lin_a = state_a.get("lineage", [])
    lin_b = state_b.get("lineage", [])
    dimensions["lineage"] = {
        "count_a": len(lin_a),
        "count_b": len(lin_b),
        "new_entries": len(lin_b) - len(lin_a) if len(lin_b) >= len(lin_a) else 0,
    }

    has_changes = any(
        d.get("added") or d.get("removed") or d.get("changed_count", 0) > 0
        for d in dimensions.values()
        if isinstance(d.get("added"), list)
    )
    if dimensions["lineage"].get("new_entries", 0) > 0:
        has_changes = True

    return {
        "dimensions": dimensions,
        "has_changes": has_changes,
    }


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def diff_snapshots(
    snapshot_id_a: str,
    snapshot_id_b: str,
) -> Dict[str, Any]:
    """Diff two snapshots by ID.  Read-only."""
    from runtime.tier3_snapshots import get_snapshot_state

    state_a = get_snapshot_state(snapshot_id_a)
    if state_a is None:
        return {"error": True, "reason": f"snapshot '{snapshot_id_a}' not found"}

    state_b = get_snapshot_state(snapshot_id_b)
    if state_b is None:
        return {"error": True, "reason": f"snapshot '{snapshot_id_b}' not found"}

    result = _diff_states(state_a, state_b)
    result["snapshot_a"] = snapshot_id_a
    result["snapshot_b"] = snapshot_id_b
    result["timestamp"] = time.time()

    _DIFF_LOG.append({
        "type": "snapshot_vs_snapshot",
        "snapshot_a": snapshot_id_a,
        "snapshot_b": snapshot_id_b,
        "has_changes": result["has_changes"],
        "timestamp": result["timestamp"],
    })
    if len(_DIFF_LOG) > _MAX_LOG:
        _DIFF_LOG[:] = _DIFF_LOG[-_MAX_LOG:]

    return result


def diff_snapshot_to_current(snapshot_id: str) -> Dict[str, Any]:
    """Diff a snapshot against the current live state.  Read-only."""
    from runtime.tier3_snapshots import get_snapshot_state, _capture_state

    state_old = get_snapshot_state(snapshot_id)
    if state_old is None:
        return {"error": True, "reason": f"snapshot '{snapshot_id}' not found"}

    state_now = _capture_state()

    result = _diff_states(state_old, state_now)
    result["snapshot"] = snapshot_id
    result["compared_to"] = "current"
    result["timestamp"] = time.time()

    _DIFF_LOG.append({
        "type": "snapshot_vs_current",
        "snapshot": snapshot_id,
        "has_changes": result["has_changes"],
        "timestamp": result["timestamp"],
    })
    if len(_DIFF_LOG) > _MAX_LOG:
        _DIFF_LOG[:] = _DIFF_LOG[-_MAX_LOG:]

    return result
