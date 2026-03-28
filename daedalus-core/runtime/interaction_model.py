# runtime/interaction_model.py
"""
Unified operator-centric interaction model.

Brings together posture, expression, autonomy tier, and operator
context into a single shaping pass.  Never overrides safety or
autonomy rules.  Degrades gracefully when components are unavailable.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

_INTERACTION_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50

# ── Per-posture interaction flow rules ───────────────────────────

_FLOW_RULES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "comfort_layer": True,
        "continuity_cues": True,
        "soft_transitions": True,
        "verbosity_adjustment": "none",
    },
    ARCHITECT: {
        "comfort_layer": False,
        "continuity_cues": True,
        "soft_transitions": False,
        "verbosity_adjustment": "none",
    },
    ORACLE: {
        "comfort_layer": False,
        "continuity_cues": True,
        "soft_transitions": True,
        "verbosity_adjustment": "none",
    },
    SCRIBE: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "none",
    },
    SENTINEL_QUIET: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "reduce",
    },
    CEREMONIAL: {
        "comfort_layer": False,
        "continuity_cues": True,
        "soft_transitions": False,
        "verbosity_adjustment": "none",
    },
    VEIL: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "reduce",
    },
    SHROUD: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "reduce",
    },
    TALON: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "none",
    },
    NULL: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "suppress",
    },
    DORMANT: {
        "comfort_layer": False,
        "continuity_cues": False,
        "soft_transitions": False,
        "verbosity_adjustment": "suppress",
    },
}

_DEFAULT_FLOW: Dict[str, Any] = {
    "comfort_layer": False,
    "continuity_cues": False,
    "soft_transitions": False,
    "verbosity_adjustment": "none",
}

# ── Intent heuristic ─────────────────────────────────────────────

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "exploratory": ["how", "what", "why", "explain", "explore", "tell me about"],
    "reflective": ["think", "consider", "reflect", "wonder", "ponder"],
    "task-driven": ["do", "run", "execute", "create", "update", "fix", "build", "deploy"],
}


def determine_interaction_intent(
    raw_input: str,
    posture_id: str | None = None,
) -> str:
    """Derive a lightweight interaction intent from raw input text.

    Returns one of: explicit, exploratory, reflective, task-driven.
    This is a surface-level heuristic — no psychological inference.
    """
    if not raw_input:
        return "explicit"

    lower = raw_input.lower().strip()
    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if lower.startswith(kw) or f" {kw} " in f" {lower} ":
                return intent

    return "explicit"


def _derive_focus_level(raw_input: str) -> str:
    """Heuristic: short inputs suggest high focus; very long suggest low."""
    length = len(raw_input.strip()) if raw_input else 0
    if length < 20:
        return "high"
    if length > 300:
        return "low"
    return "medium"


def _derive_engagement_style(raw_input: str) -> str:
    """Heuristic: questions → conversational; short commands → direct."""
    if not raw_input:
        return "direct"
    stripped = raw_input.strip()
    if stripped.endswith("?"):
        return "conversational"
    if len(stripped) < 30:
        return "direct"
    return "conversational"


def update_operator_context(
    raw_input: str,
    posture_id: str | None = None,
) -> Dict[str, Any]:
    """Derive and apply operator context from raw input.

    Phase 65: also notifies session_continuity with latest signals.
    """
    try:
        from runtime.operator_context import update_context
        intent = determine_interaction_intent(raw_input, posture_id)
        focus = _derive_focus_level(raw_input)
        style = _derive_engagement_style(raw_input)

        ctx = update_context("input_received", {
            "interaction_intent": intent,
            "operator_focus_level": focus,
            "operator_engagement_style": style,
            "continuity_window_active": intent in ("exploratory", "reflective"),
        })

        try:
            from runtime.session_continuity import update_continuity
            update_continuity(
                posture_id=posture_id,
                operator_context=ctx,
            )
        except Exception:
            pass

        return ctx
    except Exception:
        return {}


def shape_interaction_flow(
    text: str,
    posture_id: str | None = None,
    tier_id: str | None = None,
    operator_context: Dict[str, Any] | None = None,
) -> str:
    """Apply unified interaction-flow shaping to *text*.

    Combines posture flow rules with operator context to adjust the
    response without altering factual content, safety, or autonomy.

    Phase 65: also considers session continuity strength -- reflective
    intent increases continuity, task-driven reduces it, low focus
    suppresses it.

    Phase 66: considers coherence corrections -- mismatches may further
    reduce verbosity, suppress transitions, or adjust framing.

    Phase 68: integrates resonance -- reflective intent allows stronger
    resonance, task-driven reduces it, quiet suppresses it.
    """
    if not text:
        return text

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture().get("posture_id", COMPANION)
        except Exception:
            posture_id = COMPANION

    if posture_id in (NULL, DORMANT):
        _log_interaction(posture_id, "suppress", len(text), len(text))
        return text

    rules = _FLOW_RULES.get(posture_id, _DEFAULT_FLOW)
    ctx = operator_context or _get_operator_context_safe()

    result = text

    # Operator-focus verbosity adjustment
    focus = ctx.get("operator_focus_level", "medium")
    intent = ctx.get("interaction_intent", "explicit")
    vadj = rules.get("verbosity_adjustment", "none")
    if focus == "low" or vadj == "reduce":
        result = _reduce_verbosity(result)

    # Coherence-aware adjustments
    try:
        from runtime.identity_coherence import detect_mismatches, resolve_mismatches
        mismatches = detect_mismatches(posture_id, operator_context=ctx)
        if mismatches:
            resolutions = resolve_mismatches(mismatches)
            res_actions = {r["action"] for r in resolutions}
            if "reduce_verbosity" in res_actions and intent == "task-driven":
                result = _reduce_verbosity(result)
    except Exception:
        pass

    # Resonance shaping
    try:
        from runtime.resonance_engine import apply_resonance
        style = ctx.get("operator_engagement_style", "direct")
        if style == "quiet" or intent == "task-driven":
            pass  # suppress/reduce resonance for quiet/task-driven
        else:
            result = apply_resonance(result, posture_id=posture_id)
    except Exception:
        pass

    # Session continuity shaping
    try:
        from runtime.identity_continuity_engine import apply_identity_continuity
        result = apply_identity_continuity(result, posture_id=posture_id)
    except Exception:
        pass

    _log_interaction(posture_id, "shaped", len(text), len(result))
    return result


def get_interaction_summary() -> Dict[str, Any]:
    """Return a unified summary of posture, tier, expression, and context."""
    posture_id = "COMPANION"
    try:
        from runtime.posture_state import get_current_posture
        posture_id = get_current_posture().get("posture_id", posture_id)
    except Exception:
        pass

    tier_id = "TIER_1"
    try:
        from runtime.autonomy_engine import get_effective_tier
        tier_id = get_effective_tier().get("tier_id", "TIER_1")
    except Exception:
        pass

    ctx = _get_operator_context_safe()
    rules = _FLOW_RULES.get(posture_id, _DEFAULT_FLOW)

    return {
        "posture_id": posture_id,
        "tier_id": tier_id,
        "operator_context": ctx,
        "flow_rules": rules,
        "recent_interactions": list(_INTERACTION_LOG[-5:]),
        "timestamp": time.time(),
    }


def get_interaction_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_INTERACTION_LOG[-limit:])


# ── Internal helpers ─────────────────────────────────────────────

def _get_operator_context_safe() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context
        return get_context()
    except Exception:
        return {
            "interaction_intent": "explicit",
            "operator_focus_level": "medium",
            "operator_engagement_style": "direct",
            "continuity_window_active": False,
        }


def _reduce_verbosity(text: str) -> str:
    """Trim trailing whitespace on lines but preserve all content."""
    lines = text.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _log_interaction(
    posture_id: str,
    action: str,
    original_len: int,
    shaped_len: int,
) -> None:
    _INTERACTION_LOG.append({
        "posture_id": posture_id,
        "action": action,
        "original_len": original_len,
        "shaped_len": shaped_len,
        "timestamp": time.time(),
    })
    if len(_INTERACTION_LOG) > _MAX_LOG:
        _INTERACTION_LOG[:] = _INTERACTION_LOG[-_MAX_LOG:]
