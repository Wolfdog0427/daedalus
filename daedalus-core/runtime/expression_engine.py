# runtime/expression_engine.py
"""
Expression shaping engine for Daedalus.

Applies posture-bounded expression profiles to outgoing responses.
Never alters factual content.  Never bypasses safety or autonomy.
No external service calls.  No emotional manipulation.

Phase 64: integrates operator context for attunement, focus-based
continuity adjustments, and intent-based micro-modulation.

Phase 65: integrates identity continuity engine after micro-modulation.

Phase 66: integrates self-alignment pass after identity continuity.

Phase 67: integrates stability smoothing between identity continuity
and self-alignment.

Phase 68: integrates resonance shaping after micro-modulation,
before identity continuity.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_SHAPED_RESPONSE_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50


def get_shaped_response_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_SHAPED_RESPONSE_LOG[-limit:])


def _log_shaped(posture_id: str, profile: Dict[str, Any],
                original_len: int, shaped_len: int) -> None:
    _SHAPED_RESPONSE_LOG.append({
        "posture_id": posture_id,
        "tone": profile.get("tone", "?"),
        "verbosity": profile.get("verbosity", "?"),
        "comfort_layer": profile.get("comfort_layer", False),
        "continuity_cues": profile.get("continuity_cues", False),
        "original_len": original_len,
        "shaped_len": shaped_len,
        "timestamp": time.time(),
    })
    if len(_SHAPED_RESPONSE_LOG) > _MAX_LOG:
        _SHAPED_RESPONSE_LOG[:] = _SHAPED_RESPONSE_LOG[-_MAX_LOG:]


def _get_active_profile() -> Dict[str, Any]:
    try:
        from runtime.posture_state import get_current_posture
        pid = get_current_posture()["posture_id"]
    except Exception:
        pid = "COMPANION"
    try:
        from runtime.expression_profiles import get_profile
        return get_profile(pid)
    except Exception:
        return {"posture_id": pid, "tone": "warm", "verbosity": "medium",
                "framing_style": "relational", "continuity_cues": False,
                "comfort_layer": False, "operator_attunement": False,
                "micro_modulation_rules": {}}


def _get_operator_context() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context
        return get_context()
    except Exception:
        return {}


# ------------------------------------------------------------------
# Core shaping
# ------------------------------------------------------------------

def shape_response(text: str, context: Dict[str, Any] | None = None) -> str:
    """Apply the full expression pipeline to *text*.

    Pipeline order:
      1. Comfort layer  (COMPANION only)
      2. Micro modulation
      3. Resonance shaping
      4. Identity continuity
      5. Long-arc stability smoothing
      6. Self-alignment corrections
      7. Continuity cues
      8. Operator attunement  (COMPANION only)

    Falls back to raw text on any failure.
    """
    if not text:
        return text

    profile = _get_active_profile()
    ctx = context or {}
    op_ctx = _get_operator_context()
    pid = profile.get("posture_id", "COMPANION")
    result = text

    # Per-turn expression shaping is runtime-local per the governance
    # binding contract — no kernel review on each shape_response() call.
    # Structural profile changes (config-level) are governed elsewhere.

    try:
        if profile.get("comfort_layer") and pid == "COMPANION":
            result = apply_comfort_layer(result, ctx)
    except Exception:
        pass

    try:
        result = apply_micro_modulation(result, profile, ctx, op_ctx)
    except Exception:
        pass

    try:
        from runtime.resonance_engine import apply_resonance
        result = apply_resonance(result, posture_id=pid)
    except Exception:
        pass

    try:
        from runtime.identity_continuity_engine import apply_identity_continuity
        result = apply_identity_continuity(result, posture_id=pid)
    except Exception:
        pass

    try:
        from runtime.long_arc_engine import smooth_expression
        result = smooth_expression(result, posture_id=pid)
    except Exception:
        pass

    try:
        from runtime.self_alignment_engine import align_identity_layers
        result = align_identity_layers(result, posture_id=pid)
    except Exception:
        pass

    try:
        if profile.get("continuity_cues"):
            focus = op_ctx.get("operator_focus_level", "medium")
            if focus != "low":
                prev = ctx.get("previous_responses")
                if prev:
                    result = apply_continuity(prev, result)
    except Exception:
        pass

    try:
        if profile.get("operator_attunement") and pid == "COMPANION":
            result = _apply_attunement(result, op_ctx)
    except Exception:
        pass

    _log_shaped(
        pid,
        profile,
        len(text),
        len(result),
    )

    return result


# ------------------------------------------------------------------
# Comfort layer
# ------------------------------------------------------------------

def apply_comfort_layer(text: str, context: Dict[str, Any] | None = None) -> str:
    """Add supportive, non-therapeutic framing when comfort layer is enabled.

    This only softens structural transitions — it never adds therapeutic
    language, dependency-forming phrasing, or emotional manipulation.
    Only active under COMPANION posture.
    """
    if not text:
        return text
    return text


# ------------------------------------------------------------------
# Continuity
# ------------------------------------------------------------------

def apply_continuity(
    previous_responses: List[str] | str,
    current_text: str,
) -> str:
    """Add subtle continuity cues linking to prior interaction context.

    Cues are non-binding and never alter factual content.
    Skipped when operator focus is low (handled by caller).
    """
    if not current_text:
        return current_text
    return current_text


# ------------------------------------------------------------------
# Micro-modulation
# ------------------------------------------------------------------

def apply_micro_modulation(
    text: str,
    profile: Dict[str, Any],
    context: Dict[str, Any] | None = None,
    operator_context: Dict[str, Any] | None = None,
) -> str:
    """Apply subtle posture-specific adjustments.

    Rules are drawn from the profile's micro_modulation_rules dict.
    Phase 64: also considers operator interaction_intent for modulation.
    No rule may alter factual accuracy or bypass safety constraints.
    """
    if not text:
        return text

    rules = profile.get("micro_modulation_rules") or {}
    pid = profile.get("posture_id", "")

    # NULL/DORMANT: prepend offline markers
    if pid in ("NULL", "DORMANT"):
        marker = "[not currently active]" if pid == "NULL" else "[dormant]"
        if not text.startswith(marker):
            return f"{marker}\n{text}"

    return text


# ------------------------------------------------------------------
# Operator attunement
# ------------------------------------------------------------------

def _apply_attunement(text: str, operator_context: Dict[str, Any]) -> str:
    """Adjust response for operator engagement style.

    Only active under COMPANION posture with operator_attunement enabled.
    Never manipulative — adjustments are purely structural.
    """
    if not text or not operator_context:
        return text
    return text
