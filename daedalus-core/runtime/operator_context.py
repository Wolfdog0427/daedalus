# runtime/operator_context.py
"""
Lightweight operator-context tracking.

Captures interaction-level signals (intent, focus, engagement style)
without emotional inference, psychological modelling, or persistence.
All state is process-local and resets on restart.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

_MAX_LOG = 50
_lock = threading.Lock()

_context: Dict[str, Any] = {
    "interaction_intent": "explicit",
    "operator_focus_level": "medium",
    "operator_engagement_style": "direct",
    "last_interaction_timestamp": None,
    "continuity_window_active": False,
}

_CONTEXT_LOG: List[Dict[str, Any]] = []

_VALID_INTENTS = {"explicit", "exploratory", "reflective", "task-driven"}
_VALID_FOCUS = {"high", "medium", "low"}
_VALID_STYLES = {"direct", "conversational", "quiet"}


def get_context() -> Dict[str, Any]:
    """Return the current operator context."""
    with _lock:
        return dict(_context)


def get_context_log(limit: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        return list(_CONTEXT_LOG[-limit:])


def update_context(event: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record an interaction event and update context signals.

    Accepted metadata keys (all optional, ignored if invalid):
        interaction_intent, operator_focus_level,
        operator_engagement_style, continuity_window_active
    """
    now = time.time()
    meta = metadata or {}

    with _lock:
        intent = meta.get("interaction_intent")
        if intent in _VALID_INTENTS:
            _context["interaction_intent"] = intent

        focus = meta.get("operator_focus_level")
        if focus in _VALID_FOCUS:
            _context["operator_focus_level"] = focus

        style = meta.get("operator_engagement_style")
        if style in _VALID_STYLES:
            _context["operator_engagement_style"] = style

        cw = meta.get("continuity_window_active")
        if isinstance(cw, bool):
            _context["continuity_window_active"] = cw

        _context["last_interaction_timestamp"] = now

        record = {
            "event": event,
            "context_snapshot": dict(_context),
            "metadata": dict(meta),
            "timestamp": now,
        }
        _CONTEXT_LOG.append(record)
        if len(_CONTEXT_LOG) > _MAX_LOG:
            _CONTEXT_LOG[:] = _CONTEXT_LOG[-_MAX_LOG:]

        return dict(_context)


def reset_context() -> Dict[str, Any]:
    """Reset operator context to defaults."""
    with _lock:
        _context["interaction_intent"] = "explicit"
        _context["operator_focus_level"] = "medium"
        _context["operator_engagement_style"] = "direct"
        _context["last_interaction_timestamp"] = None
        _context["continuity_window_active"] = False
        return dict(_context)
