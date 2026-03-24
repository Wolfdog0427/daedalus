# knowledge/version_manager.py

"""
Version Manager

This module provides minimal snapshot creation and (optional) application
support so the sandbox and orchestrator can function.

Snapshots are stored in:
    data/versions/<snapshot_id>.json

Each snapshot contains:
- snapshot_id
- timestamp
- reason
- metadata (placeholder for future code/knowledge state)
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime


VERSIONS_DIR = os.path.join("data", "versions")
os.makedirs(VERSIONS_DIR, exist_ok=True)


def _timestamp():
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def create_snapshot(reason: str = "unspecified") -> str:
    """
    Create a minimal snapshot file and return its snapshot_id.

    This is a stub for future real versioning.
    """
    snapshot_id = str(uuid.uuid4())

    snapshot = {
        "snapshot_id": snapshot_id,
        "timestamp": _timestamp(),
        "reason": reason,
        "metadata": {
            "note": "This is a placeholder snapshot. No real code state stored yet."
        },
    }

    path = os.path.join(VERSIONS_DIR, f"{snapshot_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return snapshot_id


def apply_snapshot(snapshot_id: str) -> dict:
    """
    Placeholder for applying a snapshot.

    For now, this just loads the snapshot and returns it.
    """
    path = os.path.join(VERSIONS_DIR, f"{snapshot_id}.json")
    if not os.path.exists(path):
        return {"error": "snapshot not found"}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
