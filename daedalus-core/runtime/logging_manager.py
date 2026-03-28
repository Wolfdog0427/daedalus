# runtime/logging_manager.py

"""
Unified Logging Layer

This module provides:
- Append-only event logging
- Structured JSONL log format
- Query and filtering utilities
- A single logging API for the entire system

This module does NOT perform any self-modification.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
import os
import json

_log_lock = threading.Lock()

LOG_DIR = os.path.join("data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "events.jsonl")


def _ensure_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _now_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat()


def log_event(
    category: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Append a structured event to the log.
    """

    _ensure_dir()

    entry = {
        "timestamp": _now_iso(),
        "category": category,
        "message": message,
        "metadata": metadata or {},
    }

    with _log_lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    return entry


def list_logs(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return all logs, or the last N logs if limit is provided.
    """

    _ensure_dir()

    if not os.path.exists(LOG_PATH):
        return []

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries: List[Dict[str, Any]] = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue

    if limit is not None:
        return entries[-limit:]

    return entries


def filter_logs(
    category: Optional[str] = None,
    contains: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Filter logs by category and/or substring match.
    """

    logs = list_logs()

    if category:
        logs = [l for l in logs if l.get("category") == category]

    if contains:
        logs = [l for l in logs if contains.lower() in str(l.get("message", "")).lower()]

    if limit is not None:
        logs = logs[-limit:]

    return logs


def tail(n: int) -> List[Dict[str, Any]]:
    """
    Return the last N log entries.
    """
    return list_logs(limit=n)
