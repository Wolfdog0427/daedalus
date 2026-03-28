# runtime/posture_state.py
"""
Process-local, in-memory posture state.

Tracks the current posture, previous posture, and a bounded history
of transitions.  Resets on process restart.  No persistence.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from runtime.posture_registry import COMPANION, get_posture

_MAX_HISTORY = 100
_state_lock = threading.Lock()

_current_posture_id: str = COMPANION
_current_reason: str = "initial default"
_current_metadata: Dict[str, Any] = {}
_current_timestamp: float = time.time()

_previous_posture_id: Optional[str] = None
_previous_reason: Optional[str] = None
_previous_timestamp: Optional[float] = None

_history: List[Dict[str, Any]] = []


def get_current_posture() -> Dict[str, Any]:
    """Return the active posture ID, reason, metadata, and registry info."""
    with _state_lock:
        pid = _current_posture_id
        reason = _current_reason
        meta = dict(_current_metadata)
        ts = _current_timestamp
    info = get_posture(pid) or {}
    return {
        "posture_id": pid,
        "reason": reason,
        "metadata": meta,
        "timestamp": ts,
        **info,
    }


def get_previous_posture() -> Optional[Dict[str, Any]]:
    """Return the posture that was active before the current one."""
    with _state_lock:
        pid = _previous_posture_id
        preason = _previous_reason
        pts = _previous_timestamp
    if pid is None:
        return None
    info = get_posture(pid) or {}
    return {
        "posture_id": pid,
        "reason": preason,
        "timestamp": pts,
        **info,
    }


def get_posture_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent posture transitions."""
    n = max(0, int(limit))
    with _state_lock:
        return [dict(e) for e in _history[-n:]] if n > 0 else []


def _set_posture(
    posture_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Internal setter — only to be called by the posture engine.

    Records the transition and updates current/previous state.
    Returns a transition record.
    """
    global _current_posture_id, _current_reason, _current_metadata
    global _current_timestamp
    global _previous_posture_id, _previous_reason, _previous_timestamp

    with _state_lock:
        now = time.time()
        from_id = _current_posture_id
        from_reason = _current_reason

        _previous_posture_id = from_id
        _previous_reason = from_reason
        _previous_timestamp = _current_timestamp

        _current_posture_id = posture_id
        _current_reason = reason
        _current_metadata = dict(metadata or {})
        _current_timestamp = now

        record = {
            "from_posture": from_id,
            "to_posture": posture_id,
            "reason": reason,
            "metadata": dict(_current_metadata),
            "timestamp": now,
        }
        _history.append(record)
        if len(_history) > _MAX_HISTORY:
            _history[:] = _history[-_MAX_HISTORY:]

    return record
