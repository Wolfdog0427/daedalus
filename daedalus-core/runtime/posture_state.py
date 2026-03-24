# runtime/posture_state.py
"""
Process-local, in-memory posture state.

Tracks the current posture, previous posture, and a bounded history
of transitions.  Resets on process restart.  No persistence.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from runtime.posture_registry import COMPANION, get_posture

_MAX_HISTORY = 100

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
    info = get_posture(_current_posture_id) or {}
    return {
        "posture_id": _current_posture_id,
        "reason": _current_reason,
        "metadata": dict(_current_metadata),
        "timestamp": _current_timestamp,
        **info,
    }


def get_previous_posture() -> Optional[Dict[str, Any]]:
    """Return the posture that was active before the current one."""
    if _previous_posture_id is None:
        return None
    info = get_posture(_previous_posture_id) or {}
    return {
        "posture_id": _previous_posture_id,
        "reason": _previous_reason,
        "timestamp": _previous_timestamp,
        **info,
    }


def get_posture_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent posture transitions."""
    return list(_history[-limit:])


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
