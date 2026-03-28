# governance/audit_log.py
"""
Append-only, session-local governance audit log for Daedalus.

Logs all governance events: proposals, patches, approvals, rejections,
rollbacks, kernel decisions, persona/mode changes, invariant checks,
and drift reports.  Read-only to all external modules.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

_AUDIT_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 500
_audit_lock = threading.Lock()


def log_event(
    event_type: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Append a governance event to the audit log."""
    entry = {
        "event_type": event_type,
        "details": dict(details) if details else {},
        "timestamp": time.time(),
    }
    with _audit_lock:
        _AUDIT_LOG.append(entry)
        if len(_AUDIT_LOG) > _MAX_LOG:
            _AUDIT_LOG[:] = _AUDIT_LOG[-_MAX_LOG:]
    return dict(entry)


def get_log(limit: int = 50) -> List[Dict[str, Any]]:
    n = max(0, int(limit))
    with _audit_lock:
        return [dict(e) for e in _AUDIT_LOG[-n:]] if n > 0 else []


def get_log_summary() -> Dict[str, Any]:
    """Return a summary of the audit log."""
    with _audit_lock:
        type_counts: Dict[str, int] = {}
        for e in _AUDIT_LOG:
            t = e.get("event_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_events": len(_AUDIT_LOG),
            "event_types": type_counts,
            "oldest": _AUDIT_LOG[0]["timestamp"] if _AUDIT_LOG else None,
            "newest": _AUDIT_LOG[-1]["timestamp"] if _AUDIT_LOG else None,
        }


