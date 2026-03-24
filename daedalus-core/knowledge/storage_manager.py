# knowledge/storage_manager.py

"""
Storage Manager

Handles:
- replacing items in the knowledge store
- writing new items
- updating index structures
- snapshot/cockpit saving helpers
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any

# Correct imports
from knowledge.ingestion import KNOWLEDGE_DIR, KNOWLEDGE_FILE, ingest_text
from knowledge.retrieval import INDEX_FILE


def replace_item(item_id: str, new_item: Dict[str, Any]) -> None:
    """
    Replace an existing item in the knowledge store with a new version.
    This is append-only: the old item is marked superseded in the index.
    """

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    # Append new item
    with KNOWLEDGE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(new_item, ensure_ascii=False) + "\n")

    # Update index
    index = {}
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {"canonical": {}, "superseded": {}, "meta": {}}

    index.setdefault("superseded", {})[item_id] = {
        "reason": "replaced",
        "timestamp": time.time(),
    }

    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def save_version_snapshot(candidate: Dict[str, Any]) -> str:
    """
    Save a version snapshot for SHO.
    """
    from knowledge.version_manager import create_snapshot

    snapshot_id = create_snapshot(reason="sho-candidate")
    return snapshot_id


def save_cockpit_snapshot(data: Dict[str, Any]) -> str:
    """
    Save a cockpit snapshot for SHO.
    """
    cockpit_dir = Path("data/cockpit")
    cockpit_dir.mkdir(parents=True, exist_ok=True)

    snapshot_id = str(int(time.time() * 1000))
    path = cockpit_dir / f"{snapshot_id}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return snapshot_id
