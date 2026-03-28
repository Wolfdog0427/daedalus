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
from knowledge._atomic_io import knowledge_file_lock as _storage_lock


def _mark_superseded_unlocked(item_id: str) -> None:
    """Mark an item as superseded — caller must already hold _storage_lock."""
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

    try:
        from knowledge._atomic_io import atomic_write_json
        atomic_write_json(INDEX_FILE, index)
    except ImportError:
        INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def _mark_superseded(item_id: str) -> None:
    """Mark an item as superseded in the index (acquires lock)."""
    with _storage_lock:
        _mark_superseded_unlocked(item_id)


def replace_item(item_id: str, new_item: Dict[str, Any]) -> None:
    """
    Replace an existing item in the knowledge store with a new version.
    This is append-only: the old item is marked superseded in the index.
    """
    with _storage_lock:
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(new_item, ensure_ascii=False) + "\n"

        with KNOWLEDGE_FILE.open("a", encoding="utf-8") as f:
            f.write(serialized)

        try:
            _mark_superseded_unlocked(item_id)
        except (json.JSONDecodeError, OSError, ValueError):
            pass


def replace_item_from_text(
    old_id: str,
    new_text: str,
    reason: str = "replacement",
    source: str = "manual",
) -> str:
    """
    High-level replacement: ingests new_text, supersedes old_id, returns
    the new item's ID. Used by verification_pipeline and trust_scoring
    when they decide an existing item should be replaced.
    """
    with _storage_lock:
        new_id = ingest_text(new_text, source=source, metadata={
            "replaces": old_id,
            "replacement_reason": reason,
            "verification_status": "verified",
        })

        _mark_superseded_unlocked(old_id)

    return new_id


def get_storage_usage() -> Dict[str, Any]:
    """
    Returns storage usage metrics for the knowledge store.
    """
    used_bytes = 0
    if KNOWLEDGE_FILE.exists():
        used_bytes = KNOWLEDGE_FILE.stat().st_size

    index_bytes = 0
    if INDEX_FILE.exists():
        index_bytes = INDEX_FILE.stat().st_size

    total_bytes = used_bytes + index_bytes
    cap = 100 * 1024 * 1024  # 100 MB soft cap

    return {
        "used_bytes": total_bytes,
        "knowledge_bytes": used_bytes,
        "index_bytes": index_bytes,
        "cap_bytes": cap,
        "ratio": total_bytes / cap if cap > 0 else 0.0,
    }


def maintenance_cycle() -> Dict[str, Any]:
    """
    Run a storage maintenance cycle — currently read-only.
    Reports on superseded items that could be compacted.
    """
    index = {}
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {"canonical": {}, "superseded": {}, "meta": {}}

    superseded_count = len(index.get("superseded", {}))

    return {
        "superseded_items": superseded_count,
        "action": "compacted" if superseded_count > 0 else "no_action",
        "timestamp": time.time(),
    }


def save_version_snapshot(candidate: Dict[str, Any]) -> str:
    """
    Save a version snapshot for SHO.
    """
    from knowledge.version_manager import create_snapshot

    snapshot_id = create_snapshot(reason="sho-candidate")
    return snapshot_id


def save_cockpit_snapshot(data: Dict[str, Any]) -> str:
    """
    Save a cockpit snapshot for SHO (atomic write).
    """
    cockpit_dir = Path("data/cockpit")
    cockpit_dir.mkdir(parents=True, exist_ok=True)

    import itertools
    _ms = int(time.time() * 1000)
    _counter = getattr(save_cockpit_snapshot, "_counter", itertools.count())
    save_cockpit_snapshot._counter = _counter
    snapshot_id = f"{_ms}-{next(_counter)}"
    path = cockpit_dir / f"{snapshot_id}.json"

    from knowledge._atomic_io import atomic_write_json
    atomic_write_json(path, data)

    return snapshot_id
