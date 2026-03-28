# runtime/posture_expression.py
"""
Posture-bounded expression helpers.

Adjusts tone, verbosity, and framing based on the active posture.
Never alters factual content.  Never bypasses safety rules.
No external service calls.

Phase 62: delegates to expression_profiles and expression_engine
for expanded shaping, falling back to legacy behaviour if unavailable.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

# ── Legacy profiles (Phase 61 baseline, kept for fallback) ──────

_LEGACY_PROFILES: Dict[str, Dict[str, Any]] = {
    COMPANION: {"tone": "warm", "verbosity": "moderate", "framing": "relational", "prefix": None, "suffix": None},
    ARCHITECT: {"tone": "structured", "verbosity": "moderate", "framing": "system-thinking", "prefix": None, "suffix": None},
    ORACLE: {"tone": "reflective", "verbosity": "moderate", "framing": "pattern-oriented", "prefix": None, "suffix": None},
    SCRIBE: {"tone": "precise", "verbosity": "moderate", "framing": "documentation", "prefix": None, "suffix": None},
    SENTINEL_QUIET: {"tone": "terse", "verbosity": "low", "framing": "status-oriented", "prefix": None, "suffix": None},
    CEREMONIAL: {"tone": "formal", "verbosity": "moderate", "framing": "closure-aware", "prefix": None, "suffix": None},
    VEIL: {"tone": "quiet", "verbosity": "low", "framing": "minimal-presence", "prefix": None, "suffix": None},
    SHROUD: {"tone": "restrained", "verbosity": "low", "framing": "safety-first", "prefix": None, "suffix": None},
    TALON: {"tone": "calm", "verbosity": "moderate", "framing": "defensive-precision", "prefix": None, "suffix": None},
    NULL: {"tone": "inactive", "verbosity": "none", "framing": "offline", "prefix": "[not currently active]", "suffix": None},
    DORMANT: {"tone": "inactive", "verbosity": "none", "framing": "offline", "prefix": "[dormant]", "suffix": None},
}

_DEFAULT_LEGACY: Dict[str, Any] = {
    "tone": "neutral", "verbosity": "moderate", "framing": "default",
    "prefix": None, "suffix": None,
}


def _get_posture_id() -> str:
    try:
        from runtime.posture_state import get_current_posture
        return get_current_posture().get("posture_id", "COMPANION")
    except Exception:
        return COMPANION


def get_expression_profile() -> Dict[str, Any]:
    """Return the expression profile for the active posture.

    Prefers the expanded profile from expression_profiles; falls back
    to the legacy dict if the module is unavailable.
    """
    pid = _get_posture_id()

    try:
        from runtime.expression_profiles import get_profile
        expanded = get_profile(pid)
        legacy = _LEGACY_PROFILES.get(pid, _DEFAULT_LEGACY)
        return {
            "posture_id": pid,
            "tone": expanded.get("tone", legacy.get("tone", "neutral")),
            "verbosity": expanded.get("verbosity", legacy.get("verbosity", "moderate")),
            "framing": legacy.get("framing", expanded.get("framing_style", "default")),
            "framing_style": expanded.get("framing_style", "default"),
            "prefix": legacy.get("prefix"),
            "suffix": legacy.get("suffix"),
            "continuity_cues": expanded.get("continuity_cues", False),
            "comfort_layer": expanded.get("comfort_layer", False),
            "operator_attunement": expanded.get("operator_attunement", False),
            "micro_modulation_rules": expanded.get("micro_modulation_rules", {}),
        }
    except Exception:
        profile = _LEGACY_PROFILES.get(pid, _DEFAULT_LEGACY)
        return {"posture_id": pid, **profile}


def apply_expression_profile(
    response: str,
    context: Dict[str, Any] | None = None,
) -> str:
    """Shape *response* through the active expression profile.

    Delegates to expression_engine.shape_response() when available;
    falls back to legacy prefix/suffix behaviour otherwise.
    """
    try:
        from runtime.expression_engine import shape_response
        return shape_response(response, context)
    except Exception:
        pass

    # Legacy fallback
    profile = get_expression_profile()
    prefix = profile.get("prefix")
    suffix = profile.get("suffix")

    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(response)
    if suffix:
        parts.append(suffix)

    return "\n".join(parts) if len(parts) > 1 else parts[0]
