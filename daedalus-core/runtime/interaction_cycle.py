# runtime/interaction_cycle.py
"""
Posture-aware interaction cycle shaping.

Tracks interaction state and applies per-posture cycle cues
(continuity markers, closure markers, structural transitions)
without altering autonomy or safety behaviour.

Phase 64: integrates operator context for focus-aware verbosity
reduction, reflective continuity, and posture-based suppression.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

# ── Cycle state ──────────────────────────────────────────────────

_cycle_state: Dict[str, Any] = {
    "interaction_count": 0,
    "last_event": None,
    "last_posture_id": None,
    "last_timestamp": None,
}

_CYCLE_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50


def get_cycle_state() -> Dict[str, Any]:
    """Return the current interaction-cycle state."""
    return dict(_cycle_state)


def get_cycle_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_CYCLE_LOG[-limit:])


def update_cycle_state(event: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record an interaction event and advance the cycle counter."""
    now = time.time()
    try:
        from runtime.posture_state import get_current_posture
        pid = get_current_posture().get("posture_id", COMPANION)
    except Exception:
        pid = COMPANION

    _cycle_state["interaction_count"] += 1
    _cycle_state["last_event"] = event
    _cycle_state["last_posture_id"] = pid
    _cycle_state["last_timestamp"] = now

    record = {
        "event": event,
        "posture_id": pid,
        "interaction_count": _cycle_state["interaction_count"],
        "metadata": dict(metadata or {}),
        "timestamp": now,
    }
    _CYCLE_LOG.append(record)
    if len(_CYCLE_LOG) > _MAX_LOG:
        _CYCLE_LOG[:] = _CYCLE_LOG[-_MAX_LOG:]

    return dict(_cycle_state)


# ── Per-posture cycle cue templates ──────────────────────────────

_CYCLE_CUES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "continuity_style": "gentle",
        "closure_style": "relational",
        "transition_marker": None,
    },
    ARCHITECT: {
        "continuity_style": "structured",
        "closure_style": "explicit",
        "transition_marker": None,
    },
    ORACLE: {
        "continuity_style": "integrative",
        "closure_style": "pattern-linking",
        "transition_marker": None,
    },
    SCRIBE: {
        "continuity_style": "documentary",
        "closure_style": "documentation",
        "transition_marker": None,
    },
    SENTINEL_QUIET: {
        "continuity_style": "none",
        "closure_style": "status-only",
        "transition_marker": None,
    },
    CEREMONIAL: {
        "continuity_style": "formal",
        "closure_style": "ritual",
        "transition_marker": None,
    },
    VEIL: {
        "continuity_style": "none",
        "closure_style": "none",
        "transition_marker": None,
    },
    SHROUD: {
        "continuity_style": "none",
        "closure_style": "constrained",
        "transition_marker": None,
    },
    TALON: {
        "continuity_style": "none",
        "closure_style": "defensive-precise",
        "transition_marker": None,
    },
    NULL: {
        "continuity_style": "none",
        "closure_style": "none",
        "transition_marker": None,
    },
    DORMANT: {
        "continuity_style": "none",
        "closure_style": "none",
        "transition_marker": None,
    },
}

_DEFAULT_CUES: Dict[str, Any] = {
    "continuity_style": "none",
    "closure_style": "none",
    "transition_marker": None,
}


def get_cycle_cues(posture_id: str) -> Dict[str, Any]:
    """Return the cycle cue configuration for *posture_id*."""
    cues = _CYCLE_CUES.get(posture_id, _DEFAULT_CUES)
    return {"posture_id": posture_id, **cues}


# ── Interaction shaping ──────────────────────────────────────────

def _get_operator_context_safe() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context
        return get_context()
    except Exception:
        return {}


def shape_interaction(
    text: str,
    posture_id: str | None = None,
    context: Dict[str, Any] | None = None,
) -> str:
    """Apply posture-aware interaction-cycle shaping to *text*.

    This is a lightweight pass that adds structural cycle markers
    when the posture defines them.  It never alters factual content,
    autonomy, or safety behaviour.

    Phase 64: suppresses cycle cues for VEIL/SHROUD, adjusts for
    operator focus level and interaction intent.
    """
    if not text:
        return text

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture().get("posture_id", COMPANION)
        except Exception:
            posture_id = COMPANION

    cues = _CYCLE_CUES.get(posture_id, _DEFAULT_CUES)

    # NULL/DORMANT: no cycle shaping at all
    if posture_id in (NULL, DORMANT):
        return text

    # VEIL/SHROUD: suppress cycle cues entirely
    if posture_id in (VEIL, SHROUD):
        update_cycle_state("response_shaped", {"posture_id": posture_id, "suppressed": True})
        return text

    # Operator-context adjustments
    op_ctx = _get_operator_context_safe()
    focus = op_ctx.get("operator_focus_level", "medium")
    intent = op_ctx.get("interaction_intent", "explicit")

    # Low focus: skip transition markers to reduce noise
    if focus == "low":
        update_cycle_state("response_shaped", {"posture_id": posture_id, "low_focus": True})
        return text

    marker = cues.get("transition_marker")
    if marker and not text.startswith(marker):
        return f"{marker}\n{text}"

    update_cycle_state("response_shaped", {
        "posture_id": posture_id,
        "intent": intent,
        "focus": focus,
    })

    return text
