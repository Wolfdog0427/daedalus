# runtime/notification_center.py

"""
Notification Center

This module provides:
- A persistent notification queue
- A simple API for adding and retrieving notifications
- A way for the UI to mark notifications as read
- A unified channel for system alerts

This module does NOT perform any self-modification.
"""

from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path
import json
import threading

from runtime.logging_manager import log_event

_notify_lock = threading.Lock()


NOTIFY_DIR = Path("data") / "notifications"
NOTIFY_PATH = NOTIFY_DIR / "notifications.json"


def _ensure_dir() -> None:
    NOTIFY_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, data: Any) -> None:
    """Crash-safe JSON write using the knowledge-layer atomic helper."""
    try:
        from knowledge._atomic_io import atomic_write_json
        atomic_write_json(path, data)
    except ImportError:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_notifications() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not NOTIFY_PATH.exists():
        _atomic_write(NOTIFY_PATH, [])
        return []
    try:
        return json.loads(NOTIFY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_notifications(notifications: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    _atomic_write(NOTIFY_PATH, notifications)


def push_notification(
    category: str,
    message: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Add a new notification to the queue.
    Thread-safe — serializes load/modify/save via _notify_lock.
    """
    with _notify_lock:
        notifications = load_notifications()

        max_id = 0
        for n in notifications:
            nid = n.get("id", "")
            if nid.startswith("note-"):
                try:
                    max_id = max(max_id, int(nid.split("-", 1)[1]))
                except (ValueError, IndexError):
                    pass
        entry = {
            "id": f"note-{max_id + 1}",
            "timestamp": _now_iso(),
            "category": category,
            "message": message,
            "metadata": metadata or {},
            "read": False,
        }

        notifications.append(entry)
        save_notifications(notifications)

    log_event(
        "notification",
        f"Notification pushed: {category}",
        {"message": message, "metadata": metadata},
    )

    return entry


def list_unread() -> List[Dict[str, Any]]:
    return [n for n in load_notifications() if not n.get("read")]


def list_all() -> List[Dict[str, Any]]:
    return load_notifications()


def mark_read(notification_id: str) -> bool:
    with _notify_lock:
        notifications = load_notifications()
        updated = False

        for n in notifications:
            if n.get("id") == notification_id:
                n["read"] = True
                updated = True
                break

        if updated:
            save_notifications(notifications)

    if updated:
        log_event(
            "notification_read",
            f"Notification {notification_id} marked as read",
        )

    return updated
