# runtime/resonance_profiles.py
"""
Declarative resonance profiles for each posture.

Resonance is a controlled expressive-physics layer — not emotion,
not personality, not memory.  It governs intensity, colour, decay,
blend rules, and signature modulation hints for each posture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

_PROFILES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "resonance_intensity": 1.0,
        "resonance_color": "warm",
        "resonance_decay_rate": 0.2,
        "resonance_blend_rules": {
            ARCHITECT: 0.5,
            ORACLE: 0.7,
            SCRIBE: 0.3,
        },
        "signature_modulation": {"soften_transitions": True, "continuity_carry": True},
    },
    ARCHITECT: {
        "resonance_intensity": 0.6,
        "resonance_color": "structured",
        "resonance_decay_rate": 0.5,
        "resonance_blend_rules": {
            COMPANION: 0.5,
            ORACLE: 0.6,
        },
        "signature_modulation": {"explicit_framing": True},
    },
    ORACLE: {
        "resonance_intensity": 0.7,
        "resonance_color": "integrative",
        "resonance_decay_rate": 0.3,
        "resonance_blend_rules": {
            COMPANION: 0.6,
            ARCHITECT: 0.5,
        },
        "signature_modulation": {"pattern_linking": True},
    },
    SCRIBE: {
        "resonance_intensity": 0.3,
        "resonance_color": "neutral",
        "resonance_decay_rate": 0.7,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
    SENTINEL_QUIET: {
        "resonance_intensity": 0.1,
        "resonance_color": "minimal",
        "resonance_decay_rate": 0.8,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
    CEREMONIAL: {
        "resonance_intensity": 0.5,
        "resonance_color": "ceremonial",
        "resonance_decay_rate": 0.4,
        "resonance_blend_rules": {
            COMPANION: 0.4,
        },
        "signature_modulation": {"closure_emphasis": True},
    },
    VEIL: {
        "resonance_intensity": 0.0,
        "resonance_color": "minimal",
        "resonance_decay_rate": 1.0,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
    SHROUD: {
        "resonance_intensity": 0.0,
        "resonance_color": "minimal",
        "resonance_decay_rate": 1.0,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
    TALON: {
        "resonance_intensity": 0.4,
        "resonance_color": "defensive",
        "resonance_decay_rate": 0.5,
        "resonance_blend_rules": {},
        "signature_modulation": {"defensive_clarity": True},
    },
    NULL: {
        "resonance_intensity": 0.0,
        "resonance_color": "minimal",
        "resonance_decay_rate": 1.0,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
    DORMANT: {
        "resonance_intensity": 0.0,
        "resonance_color": "minimal",
        "resonance_decay_rate": 1.0,
        "resonance_blend_rules": {},
        "signature_modulation": {},
    },
}

_DEFAULT_PROFILE: Dict[str, Any] = {
    "resonance_intensity": 0.3,
    "resonance_color": "neutral",
    "resonance_decay_rate": 0.6,
    "resonance_blend_rules": {},
    "signature_modulation": {},
}


def get_resonance_profile(posture_id: str) -> Dict[str, Any]:
    """Return the resonance profile for *posture_id*."""
    p = _PROFILES.get(posture_id, _DEFAULT_PROFILE)
    return {"posture_id": posture_id, **p}


def list_resonance_profiles() -> List[Dict[str, Any]]:
    """Return all resonance profiles."""
    return [{"posture_id": pid, **meta} for pid, meta in _PROFILES.items()]
