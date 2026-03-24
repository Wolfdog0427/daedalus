# runtime/reliability_loader.py

from __future__ import annotations

import os
import json
from typing import Dict, Any


LEARNING_ROOT = "data/learning"
SUBSYSTEM_DIR = os.path.join(LEARNING_ROOT, "subsystems")
ACTION_DIR = os.path.join(LEARNING_ROOT, "actions")


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_reliability_dashboard() -> Dict[str, Dict[str, Any]]:
    """
    Loads all subsystem and action reliability profiles.
    Returns:
    {
        "subsystems": { name: profile, ... },
        "actions": { type: profile, ... }
    }
    """

    subsystems: Dict[str, Any] = {}
    actions: Dict[str, Any] = {}

    # Load subsystem reliability
    if os.path.exists(SUBSYSTEM_DIR):
        for fname in os.listdir(SUBSYSTEM_DIR):
            if not fname.endswith(".json"):
                continue
            name = fname[:-5]
            subsystems[name] = _load_json(os.path.join(SUBSYSTEM_DIR, fname))

    # Load action-type reliability
    if os.path.exists(ACTION_DIR):
        for fname in os.listdir(ACTION_DIR):
            if not fname.endswith(".json"):
                continue
            name = fname[:-5]
            actions[name] = _load_json(os.path.join(ACTION_DIR, fname))

    return {
        "subsystems": subsystems,
        "actions": actions,
    }
