# knowledge/version_manager.py

"""
Version Manager

Creates and restores system snapshots that capture the full recoverable
state of Daedalus:
- Knowledge graph (graph.json, entities.json)
- Governor state (governor_state.json)
- Knowledge store index (index.json)
- Knowledge goals (goals.json)
- Self-model confidence snapshot

Snapshots are stored in:
    data/versions/<snapshot_id>/
        manifest.json    — metadata + confidence snapshot
        graph.json       — knowledge graph adjacency
        entities.json    — entity registry
        governor.json    — governor state
        index.json       — knowledge store index
        goals.json       — knowledge goals

Restore copies snapshot files back to their canonical locations,
using atomic writes to prevent mid-restore corruption.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from knowledge._atomic_io import atomic_write_json

VERSIONS_DIR = Path("data/versions")

_CAPTURABLE_FILES = {
    "graph": Path("data/knowledge_graph/graph.json"),
    "entities": Path("data/knowledge_graph/entities.json"),
    "governor": Path("data/governor_state.json"),
    "index": Path("data/knowledge/index.json"),
    "goals": Path("data/knowledge_goals/goals.json"),
}


def _ensure_dir():
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp():
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def _safe_load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _confidence_snapshot() -> Dict[str, float]:
    """Capture current self-model confidence metrics."""
    try:
        from knowledge.self_model import get_self_model
        sm = get_self_model()
        conf = sm.get("confidence", {})
        return {
            "consistency": conf.get("consistency", 0.0),
            "coherence": conf.get("graph_coherence", 0.0),
            "quality": conf.get("knowledge_quality", 0.0),
        }
    except Exception:
        return {}


def create_snapshot(reason: str = "unspecified") -> str:
    """
    Create a full system snapshot capturing graph, governor state,
    knowledge index, and goals. Returns the snapshot_id.
    """
    _ensure_dir()
    snapshot_id = str(uuid.uuid4())
    snap_dir = VERSIONS_DIR / snapshot_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    captured = {}
    for name, src_path in _CAPTURABLE_FILES.items():
        data = _safe_load_json(src_path)
        if data is not None:
            dest = snap_dir / f"{name}.json"
            atomic_write_json(dest, data)
            captured[name] = True
        else:
            captured[name] = False

    manifest = {
        "snapshot_id": snapshot_id,
        "timestamp": _timestamp(),
        "epoch_time": time.time(),
        "reason": reason,
        "captured": captured,
        "confidence": _confidence_snapshot(),
    }
    atomic_write_json(snap_dir / "manifest.json", manifest)

    return snapshot_id


def apply_snapshot(snapshot_id: str) -> Dict[str, Any]:
    """
    Restore system state from a snapshot. Copies captured files back
    to their canonical locations using atomic writes.

    Returns a report of what was restored and what was skipped.
    """
    snap_dir = VERSIONS_DIR / snapshot_id
    manifest_path = snap_dir / "manifest.json"

    if not manifest_path.exists():
        return {"status": "error", "reason": "snapshot_not_found", "snapshot_id": snapshot_id}

    manifest = _safe_load_json(manifest_path)
    if manifest is None:
        return {"status": "error", "reason": "corrupt_manifest"}

    restored = {}
    errors = {}
    for name, dest_path in _CAPTURABLE_FILES.items():
        src = snap_dir / f"{name}.json"
        if not src.exists():
            restored[name] = "skipped_not_in_snapshot"
            continue
        try:
            data = _safe_load_json(src)
            if data is not None:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_json(dest_path, data)
                restored[name] = "restored"
            else:
                restored[name] = "skipped_corrupt"
        except Exception as exc:
            restored[name] = "error"
            errors[name] = str(exc)

    return {
        "status": "restored" if not errors else "partial",
        "snapshot_id": snapshot_id,
        "timestamp": manifest.get("timestamp"),
        "reason": manifest.get("reason"),
        "restored": restored,
        "errors": errors if errors else None,
        "confidence_at_snapshot": manifest.get("confidence", {}),
    }


def list_snapshots(limit: int = 20) -> list:
    """Return metadata from recent snapshots, newest first."""
    _ensure_dir()
    snapshots = []
    for snap_dir in VERSIONS_DIR.iterdir():
        if not snap_dir.is_dir():
            continue
        manifest = _safe_load_json(snap_dir / "manifest.json")
        if manifest:
            snapshots.append({
                "snapshot_id": manifest.get("snapshot_id"),
                "timestamp": manifest.get("timestamp"),
                "epoch_time": manifest.get("epoch_time", 0),
                "reason": manifest.get("reason"),
                "confidence": manifest.get("confidence", {}),
            })
    snapshots.sort(key=lambda s: s.get("epoch_time", 0), reverse=True)
    return snapshots[:limit]


def get_latest_snapshot_id() -> Optional[str]:
    """Return the ID of the most recent snapshot, or None."""
    snaps = list_snapshots(limit=1)
    return snaps[0]["snapshot_id"] if snaps else None
