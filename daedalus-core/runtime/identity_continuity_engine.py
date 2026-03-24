# runtime/identity_continuity_engine.py
"""
Identity continuity engine for Daedalus.

Determines how session continuity influences expression shaping.
Never alters factual content.  Never overrides safety or autonomy.
No emotional inference.  No psychological modeling.  No persistence.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

# ── Per-posture continuity weight table ──────────────────────────

_WEIGHT_TABLE: Dict[str, float] = {
    "COMPANION": 1.0,
    "ARCHITECT": 0.6,
    "ORACLE": 0.7,
    "SCRIBE": 0.2,
    "SENTINEL_QUIET": 0.0,
    "CEREMONIAL": 0.3,
    "VEIL": 0.0,
    "SHROUD": 0.0,
    "TALON": 0.1,
    "NULL": 0.0,
    "DORMANT": 0.0,
}

_CONTINUITY_SHAPED_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50


def get_continuity_shaped_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_CONTINUITY_SHAPED_LOG[-limit:])


def compute_continuity_weight(
    posture_id: str,
    operator_context: Dict[str, Any] | None = None,
) -> float:
    """Return the continuity weight for the given posture and context.

    Weight is 0.0 – 1.0.  Higher means more continuity influence.
    Adjusted downward for low focus or task-driven intent.
    """
    base = _WEIGHT_TABLE.get(posture_id, 0.3)
    ctx = operator_context or {}

    focus = ctx.get("operator_focus_level", "medium")
    intent = ctx.get("interaction_intent", "explicit")

    if focus == "low":
        base *= 0.3
    elif focus == "high":
        base *= 1.0

    if intent == "reflective":
        base = min(1.0, base * 1.3)
    elif intent == "task-driven":
        base *= 0.5

    return round(max(0.0, min(1.0, base)), 2)


def apply_identity_continuity(
    text: str,
    continuity_state: Dict[str, Any] | None = None,
    posture_id: str | None = None,
) -> str:
    """Apply identity-continuity shaping to *text*.

    Shaping is subtle and structural — it never alters factual content,
    never overrides safety, and never bypasses autonomy restrictions.
    The continuity_state determines whether and how strongly continuity
    applies.
    """
    if not text:
        return text

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture()["posture_id"]
        except Exception:
            posture_id = "COMPANION"

    if posture_id in ("NULL", "DORMANT", "VEIL", "SHROUD"):
        _log_shaped(posture_id, 0.0, len(text), len(text), "suppressed")
        return text

    state = continuity_state or _get_continuity_state_safe()

    try:
        from runtime.long_arc_engine import smooth_continuity
        state = smooth_continuity(state)
    except Exception:
        pass

    if not state.get("continuity_active", False):
        _log_shaped(posture_id, 0.0, len(text), len(text), "inactive")
        return text

    op_ctx = _get_operator_context_safe()
    weight = compute_continuity_weight(posture_id, op_ctx)

    try:
        from runtime.resonance_profiles import get_resonance_profile
        decay = get_resonance_profile(posture_id).get("resonance_decay_rate", 0.5)
        weight *= (1.0 - decay * 0.3)
        weight = round(max(0.0, min(1.0, weight)), 2)
    except Exception:
        pass

    if weight < 0.1:
        _log_shaped(posture_id, weight, len(text), len(text), "below_threshold")
        return text

    result = text
    _log_shaped(posture_id, weight, len(text), len(result), "applied")
    return result


def continuity_summary() -> Dict[str, Any]:
    """Return a structured summary of the continuity engine state."""
    state = _get_continuity_state_safe()

    posture_id = "COMPANION"
    try:
        from runtime.posture_state import get_current_posture
        posture_id = get_current_posture()["posture_id"]
    except Exception:
        pass

    op_ctx = _get_operator_context_safe()
    weight = compute_continuity_weight(posture_id, op_ctx)

    return {
        "posture_id": posture_id,
        "continuity_active": state.get("continuity_active", False),
        "continuity_strength": state.get("continuity_strength", "low"),
        "continuity_weight": weight,
        "last_posture_id": state.get("last_posture_id"),
        "last_tier_id": state.get("last_tier_id"),
        "last_interaction_intent": state.get("last_interaction_intent"),
        "last_focus_level": state.get("last_focus_level"),
        "recent_shaped": list(_CONTINUITY_SHAPED_LOG[-5:]),
        "timestamp": time.time(),
    }


# ── Internal helpers ─────────────────────────────────────────────

def _get_continuity_state_safe() -> Dict[str, Any]:
    try:
        from runtime.session_continuity import get_continuity_state
        return get_continuity_state()
    except Exception:
        return {"continuity_active": False, "continuity_strength": "low"}


def _get_operator_context_safe() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context
        return get_context()
    except Exception:
        return {}


def _log_shaped(
    posture_id: str,
    weight: float,
    original_len: int,
    shaped_len: int,
    action: str,
) -> None:
    _CONTINUITY_SHAPED_LOG.append({
        "posture_id": posture_id,
        "weight": weight,
        "original_len": original_len,
        "shaped_len": shaped_len,
        "action": action,
        "timestamp": time.time(),
    })
    if len(_CONTINUITY_SHAPED_LOG) > _MAX_LOG:
        _CONTINUITY_SHAPED_LOG[:] = _CONTINUITY_SHAPED_LOG[-_MAX_LOG:]
