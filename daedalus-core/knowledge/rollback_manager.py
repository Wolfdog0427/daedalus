# knowledge/rollback_manager.py

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict


ROLLBACK_ROOT = os.path.join("data", "rollback")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def begin_transaction(subsystem: str) -> str:
    """
    Create a rollback directory for this subsystem and return its path.
    """
    ts = _now_iso().replace(":", "-")
    path = os.path.join(ROLLBACK_ROOT, subsystem, ts)
    _ensure_dir(path)
    return path


def snapshot_file(path: str, label: str, data: Dict[str, Any]) -> None:
    """
    Save a JSON snapshot inside the rollback directory.
    """
    file_path = os.path.join(path, f"{label}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_snapshot(path: str, label: str) -> Dict[str, Any]:
    """
    Load a JSON snapshot from the rollback directory.
    """
    file_path = os.path.join(path, f"{label}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_rollback_log(path: str, details: Dict[str, Any]) -> None:
    """
    Write rollback metadata (success/failure, errors, etc.) into the rollback directory.
    """
    file_path = os.path.join(path, "rollback_log.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2)
