# knowledge/rollback_manager.py

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict


ROLLBACK_ROOT = os.path.join("data", "rollback")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize_path_component(name: str) -> str:
    """Reject path separators and traversal sequences in user-supplied names."""
    sanitized = name.replace("\x00", "")
    sanitized = sanitized.replace("..", "").replace("/", "_").replace("\\", "_")
    if not sanitized:
        raise ValueError(f"Invalid path component: {name!r}")
    return sanitized


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def begin_transaction(subsystem: str) -> str:
    """
    Create a rollback directory for this subsystem and return its path.
    """
    ts = _now_iso().replace(":", "-")
    safe_subsystem = _sanitize_path_component(subsystem)
    path = os.path.join(ROLLBACK_ROOT, safe_subsystem, ts)
    _ensure_dir(path)
    return path


def _atomic_write(file_path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically using a temp file + rename."""
    import tempfile
    dir_name = os.path.dirname(file_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, file_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def snapshot_file(path: str, label: str, data: Dict[str, Any]) -> None:
    """
    Save a JSON snapshot inside the rollback directory.
    """
    safe_label = _sanitize_path_component(label)
    file_path = os.path.join(path, f"{safe_label}.json")
    _atomic_write(file_path, data)


def load_snapshot(path: str, label: str) -> Dict[str, Any]:
    """
    Load a JSON snapshot from the rollback directory.
    Returns empty dict with an error key if the file is corrupt.
    """
    safe_label = _sanitize_path_component(label)
    file_path = os.path.join(path, f"{safe_label}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"_error": f"Failed to load snapshot: {e}", "_path": file_path}


def write_rollback_log(path: str, details: Dict[str, Any]) -> None:
    """
    Write rollback metadata (success/failure, errors, etc.) into the rollback directory.
    """
    file_path = os.path.join(path, "rollback_log.json")
    _atomic_write(file_path, details)
