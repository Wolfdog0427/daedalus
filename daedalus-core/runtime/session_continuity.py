# runtime/session_continuity.py
"""
Session-level identity continuity tracking.

Maintains posture, tier, expression, and interaction continuity
signals within a single process session.  No persistence, no
personal data, no emotional inference, no psychological modeling.
Resets on process restart.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_MAX_LOG = 50

_state: Dict[str, Any] = {
    "last_posture_id": None,
    "last_tier_id": None,
    "last_expression_profile": None,
    "last_interaction_intent": None,
    "last_focus_level": None,
    "last_engagement_style": None,
    "continuity_active": False,
    "continuity_strength": "low",
    "update_count": 0,
    "last_update_timestamp": None,
}

_CONTINUITY_LOG: List[Dict[str, Any]] = []


def get_continuity_state() -> Dict[str, Any]:
    """Return the current session continuity state."""
    return dict(_state)


def get_continuity_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_CONTINUITY_LOG[-limit:])


def _compute_strength(
    posture_id: str | None,
    intent: str | None,
    focus: str | None,
) -> str:
    """Derive continuity strength from posture + operator signals.

    Strength tiers:
        high   — COMPANION with exploratory/reflective intent and medium+ focus
        medium — most interactive postures with medium focus
        low    — all other cases (minimal postures, low focus, etc.)
    """
    if posture_id in ("NULL", "DORMANT", "VEIL", "SHROUD"):
        return "low"
    if focus == "low":
        return "low"
    if posture_id == "COMPANION" and intent in ("exploratory", "reflective"):
        return "high"
    if posture_id in ("COMPANION", "ARCHITECT", "ORACLE") and focus != "low":
        return "medium"
    return "low"


def update_continuity(
    posture_id: str | None = None,
    tier_id: str | None = None,
    operator_context: Dict[str, Any] | None = None,
    expression_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Record latest posture/tier/context/expression for continuity tracking."""
    now = time.time()
    ctx = operator_context or {}

    if posture_id is not None:
        _state["last_posture_id"] = posture_id
    if tier_id is not None:
        _state["last_tier_id"] = tier_id
    if expression_profile is not None:
        _state["last_expression_profile"] = dict(expression_profile)

    intent = ctx.get("interaction_intent")
    if intent is not None:
        _state["last_interaction_intent"] = intent
    focus = ctx.get("operator_focus_level")
    if focus is not None:
        _state["last_focus_level"] = focus
    style = ctx.get("operator_engagement_style")
    if style is not None:
        _state["last_engagement_style"] = style

    strength = _compute_strength(
        _state["last_posture_id"],
        _state["last_interaction_intent"],
        _state["last_focus_level"],
    )
    _state["continuity_strength"] = strength
    _state["continuity_active"] = strength != "low"
    _state["update_count"] += 1
    _state["last_update_timestamp"] = now

    record = {
        "posture_id": _state["last_posture_id"],
        "tier_id": _state["last_tier_id"],
        "continuity_strength": strength,
        "continuity_active": _state["continuity_active"],
        "intent": _state["last_interaction_intent"],
        "focus": _state["last_focus_level"],
        "timestamp": now,
    }
    _CONTINUITY_LOG.append(record)
    if len(_CONTINUITY_LOG) > _MAX_LOG:
        _CONTINUITY_LOG[:] = _CONTINUITY_LOG[-_MAX_LOG:]

    return dict(_state)


def reset_continuity() -> Dict[str, Any]:
    """Reset session continuity to defaults."""
    _state["last_posture_id"] = None
    _state["last_tier_id"] = None
    _state["last_expression_profile"] = None
    _state["last_interaction_intent"] = None
    _state["last_focus_level"] = None
    _state["last_engagement_style"] = None
    _state["continuity_active"] = False
    _state["continuity_strength"] = "low"
    _state["update_count"] = 0
    _state["last_update_timestamp"] = None
    return dict(_state)
