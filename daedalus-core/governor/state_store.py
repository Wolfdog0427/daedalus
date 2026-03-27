# governor/state_store.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from knowledge._atomic_io import atomic_write_json

STATE_DIR = Path("data")
STATE_PATH = STATE_DIR / "governor_state.json"
PROPOSALS_PATH = STATE_DIR / "governor_proposals.json"


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
    if not STATE_PATH.exists():
        return _default_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
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
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(STATE_PATH, state)


def load_proposals() -> List[Dict[str, Any]]:
    if not PROPOSALS_PATH.exists():
        return []
    try:
        data = json.loads(PROPOSALS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_proposals(proposals: List[Dict[str, Any]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PROPOSALS_PATH, proposals)
