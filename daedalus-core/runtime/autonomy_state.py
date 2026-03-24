# runtime/autonomy_state.py
"""
Process-local, in-memory autonomy tier state.

Tracks the current tier, previous tier, and a bounded history
of transitions.  Resets on process restart.  No persistence.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from runtime.autonomy_tiers import TIER_1, get_tier

_MAX_HISTORY = 100

_current_tier_id: str = TIER_1
_current_reason: str = "initial default"
_current_metadata: Dict[str, Any] = {}
_current_timestamp: float = time.time()

_previous_tier_id: Optional[str] = None
_previous_reason: Optional[str] = None
_previous_timestamp: Optional[float] = None

_history: List[Dict[str, Any]] = []


def get_current_tier() -> Dict[str, Any]:
    """Return the active tier ID, reason, metadata, and registry info."""
    info = get_tier(_current_tier_id) or {}
    return {
        "tier_id": _current_tier_id,
        "reason": _current_reason,
        "metadata": dict(_current_metadata),
        "timestamp": _current_timestamp,
        **info,
    }


def get_previous_tier() -> Optional[Dict[str, Any]]:
    """Return the tier that was active before the current one."""
    if _previous_tier_id is None:
        return None
    info = get_tier(_previous_tier_id) or {}
    return {
        "tier_id": _previous_tier_id,
        "reason": _previous_reason,
        "timestamp": _previous_timestamp,
        **info,
    }


def get_tier_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent tier transitions."""
    return list(_history[-limit:])


def _set_tier(
    tier_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Internal setter — only to be called by the autonomy engine."""
    global _current_tier_id, _current_reason, _current_metadata
    global _current_timestamp
    global _previous_tier_id, _previous_reason, _previous_timestamp

    now = time.time()
    from_id = _current_tier_id

    _previous_tier_id = from_id
    _previous_reason = _current_reason
    _previous_timestamp = _current_timestamp

    _current_tier_id = tier_id
    _current_reason = reason
    _current_metadata = dict(metadata or {})
    _current_timestamp = now

    record = {
        "from_tier": from_id,
        "to_tier": tier_id,
        "reason": reason,
        "metadata": dict(_current_metadata),
        "timestamp": now,
    }
    _history.append(record)
    if len(_history) > _MAX_HISTORY:
        _history[:] = _history[-_MAX_HISTORY:]

    return record
