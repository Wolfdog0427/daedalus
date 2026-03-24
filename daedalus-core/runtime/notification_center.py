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
import os
import json

from runtime.logging_manager import log_event


NOTIFY_DIR = os.path.join("data", "notifications")
NOTIFY_PATH = os.path.join(NOTIFY_DIR, "notifications.json")


def _ensure_dir() -> None:
    os.makedirs(NOTIFY_DIR, exist_ok=True)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def load_notifications() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not os.path.exists(NOTIFY_PATH):
        with open(NOTIFY_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    with open(NOTIFY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_notifications(notifications: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    with open(NOTIFY_PATH, "w", encoding="utf-8") as f:
        json.dump(notifications, f, indent=2)


def push_notification(
    category: str,
    message: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Add a new notification to the queue.
    """

    notifications = load_notifications()

    entry = {
        "id": f"note-{len(notifications) + 1}",
        "timestamp": _now_iso(),
        "category": category,  # e.g., "tier3", "drift", "stability", "patch_failure"
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
    notifications = load_notifications()
    updated = False

    for n in notifications:
        if n.get("id") == notification_id:
            n["read"] = True
            updated = True
            break

    if updated:
        save_notifications(notifications)
        log_event(
            "notification_read",
            f"Notification {notification_id} marked as read",
        )

    return updated
