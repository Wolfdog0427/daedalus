# governor/state_store.py

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

STATE_PATH = os.path.join("data", "governor_state.json")
PROPOSALS_PATH = os.path.join("data", "governor_proposals.json")


def _default_state() -> Dict[str, Any]:
    return {
        "autonomy_mode": "strict",
        "locked": False,
        "current_tier": 1,
        "drift": {},
        "stability": {},
        "patch_history": {
            "total_cycles": 0,
            "successful_patches": 0,
            "failed_patches": 0,
            "reverted_patches": 0,
            "failed_high_level_cycles": 0,
            "failed_tier2_cycles": 0,
            "recent_failures": [],
        },
        "escalation": {},
        "proposals": {
            "pending": [],
            "recent_decisions": [],
        },
    }


def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return _default_state()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _default_state()
    # Merge with defaults to avoid missing keys
    base = _default_state()
    base.update(data)
    proposals = base.get("proposals")
    if not isinstance(proposals, dict):
        base["proposals"] = {"pending": [], "recent_decisions": []}
    else:
        proposals.setdefault("pending", [])
        proposals.setdefault("recent_decisions", [])
    return base


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_proposals() -> List[Dict[str, Any]]:
    if not os.path.exists(PROPOSALS_PATH):
        return []
    try:
        with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_proposals(proposals: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(PROPOSALS_PATH), exist_ok=True)
    with open(PROPOSALS_PATH, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)
