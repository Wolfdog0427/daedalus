# runtime/expression_profiles.py
"""
Expanded expression profiles for each posture.

Defines tone, verbosity, framing style, continuity cues, comfort layer,
operator attunement, and micro-modulation rules.  Purely declarative —
no mutable state, no external calls, no safety bypass.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

_PROFILES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "tone": "warm",
        "verbosity": "medium",
        "framing_style": "relational",
        "continuity_cues": True,
        "comfort_layer": True,
        "operator_attunement": True,
        "micro_modulation_rules": {
            "soften_transitions": True,
            "acknowledge_prior_context": True,
        },
    },
    ARCHITECT: {
        "tone": "analytical",
        "verbosity": "medium",
        "framing_style": "structural",
        "continuity_cues": True,
        "comfort_layer": False,
        "operator_attunement": True,
        "micro_modulation_rules": {
            "explicit_section_markers": True,
            "highlight_dependencies": True,
        },
    },
    ORACLE: {
        "tone": "high-context",
        "verbosity": "medium",
        "framing_style": "integrative",
        "continuity_cues": True,
        "comfort_layer": False,
        "operator_attunement": True,
        "micro_modulation_rules": {
            "pattern_linking": True,
            "cross_reference_cues": True,
        },
    },
    SCRIBE: {
        "tone": "terse",
        "verbosity": "medium",
        "framing_style": "documentary",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {
            "section_headings": True,
            "factual_density": True,
        },
    },
    SENTINEL_QUIET: {
        "tone": "terse",
        "verbosity": "low",
        "framing_style": "status-only",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {},
    },
    CEREMONIAL: {
        "tone": "ceremonial",
        "verbosity": "medium",
        "framing_style": "ritual",
        "continuity_cues": True,
        "comfort_layer": True,
        "operator_attunement": True,
        "micro_modulation_rules": {
            "formal_closure": True,
            "acknowledgement_markers": True,
        },
    },
    VEIL: {
        "tone": "minimal",
        "verbosity": "minimal",
        "framing_style": "constrained",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {},
    },
    SHROUD: {
        "tone": "minimal",
        "verbosity": "low",
        "framing_style": "constrained",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {
            "safety_first_framing": True,
        },
    },
    TALON: {
        "tone": "defensive-calm",
        "verbosity": "medium",
        "framing_style": "constrained",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": True,
        "micro_modulation_rules": {
            "precision_emphasis": True,
            "defensive_framing": True,
        },
    },
    NULL: {
        "tone": "minimal",
        "verbosity": "minimal",
        "framing_style": "constrained",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {},
    },
    DORMANT: {
        "tone": "minimal",
        "verbosity": "minimal",
        "framing_style": "constrained",
        "continuity_cues": False,
        "comfort_layer": False,
        "operator_attunement": False,
        "micro_modulation_rules": {},
    },
}

_DEFAULT_PROFILE: Dict[str, Any] = {
    "tone": "warm",
    "verbosity": "medium",
    "framing_style": "relational",
    "continuity_cues": False,
    "comfort_layer": False,
    "operator_attunement": False,
    "micro_modulation_rules": {},
}


def get_profile(posture_id: str) -> Dict[str, Any]:
    """Return the expanded expression profile for *posture_id*."""
    profile = _PROFILES.get(posture_id, _DEFAULT_PROFILE)
    return {"posture_id": posture_id, **profile}


def list_profiles() -> List[Dict[str, Any]]:
    """Return all expanded expression profiles."""
    return [
        {"posture_id": pid, **prof}
        for pid, prof in _PROFILES.items()
    ]
