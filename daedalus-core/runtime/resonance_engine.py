# runtime/resonance_engine.py
"""
Resonance engine for Daedalus.

Applies posture-aware, stability-aware resonance shaping to text.
Resonance is a controlled expressive-physics layer that enhances
fluidity and identity cohesion.  It is NOT emotion, NOT personality,
NOT memory, and NOT autonomy expansion.

Never alters factual content.  Never overrides safety or autonomy.
No persistence.  No emotional inference.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_RESONANCE_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50

_last_posture_id: str | None = None


def get_resonance_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_RESONANCE_LOG[-limit:])


def _get_profile(posture_id: str) -> Dict[str, Any]:
    try:
        from runtime.resonance_profiles import get_resonance_profile
        return get_resonance_profile(posture_id)
    except Exception:
        return {
            "posture_id": posture_id,
            "resonance_intensity": 0.3,
            "resonance_color": "neutral",
            "resonance_decay_rate": 0.6,
            "resonance_blend_rules": {},
            "signature_modulation": {},
        }


def blend_resonance(
    previous_posture: str | None,
    current_posture: str,
) -> float:
    """Compute the blend factor when transitioning between postures.

    Returns 0.0 (no carry-over) to 1.0 (full carry-over).
    """
    if previous_posture is None or previous_posture == current_posture:
        return 1.0

    profile = _get_profile(current_posture)
    blend_rules = profile.get("resonance_blend_rules") or {}
    return blend_rules.get(previous_posture, 0.2)


def apply_resonance(
    text: str,
    posture_id: str | None = None,
    stability_state: Dict[str, Any] | None = None,
    continuity_state: Dict[str, Any] | None = None,
) -> str:
    """Apply resonance shaping to *text*.

    Resonance intensity is reduced when stability is low.  Decay rate
    governs how much previous resonance carries into the current turn.
    Never alters factual content, safety, or autonomy.
    """
    global _last_posture_id

    if not text:
        return text

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture().get("posture_id", "COMPANION")
        except Exception:
            posture_id = "COMPANION"

    profile = _get_profile(posture_id)
    intensity = profile.get("resonance_intensity", 0.0)

    if abs(intensity) < 1e-9 or posture_id in ("NULL", "DORMANT", "VEIL", "SHROUD"):
        _log_resonance(posture_id, 0.0, 0.0, len(text), len(text), "suppressed")
        _last_posture_id = posture_id
        return text

    ss = stability_state or _get_stability_safe()
    stability_score = ss.get("stability_score", 100.0)

    if stability_score < 50.0:
        intensity *= (stability_score / 100.0)

    bf = blend_resonance(_last_posture_id, posture_id)
    effective_intensity = round(intensity * bf, 3)

    result = text

    _log_resonance(posture_id, effective_intensity, bf, len(text), len(result), "applied")
    _last_posture_id = posture_id
    return result


def resonance_summary() -> Dict[str, Any]:
    """Return a structured summary of current resonance state."""
    posture_id = "COMPANION"
    try:
        from runtime.posture_state import get_current_posture
        posture_id = get_current_posture().get("posture_id", posture_id)
    except Exception:
        pass

    profile = _get_profile(posture_id)
    ss = _get_stability_safe()
    bf = blend_resonance(_last_posture_id, posture_id)

    return {
        "posture_id": posture_id,
        "previous_posture_id": _last_posture_id,
        "resonance_intensity": profile.get("resonance_intensity", 0.0),
        "resonance_color": profile.get("resonance_color", "neutral"),
        "resonance_decay_rate": profile.get("resonance_decay_rate", 0.6),
        "blend_factor": bf,
        "stability_score": ss.get("stability_score", 100.0),
        "signature_modulation": profile.get("signature_modulation", {}),
        "recent_log": list(_RESONANCE_LOG[-5:]),
        "timestamp": time.time(),
    }


# ── Internal helpers ─────────────────────────────────────────────

def _get_stability_safe() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state
        return get_stability_state()
    except Exception:
        return {"stability_score": 100.0, "oscillation_index": 0.0, "jitter_index": 0.0}


def _log_resonance(
    posture_id: str,
    effective_intensity: float,
    blend_factor: float,
    original_len: int,
    shaped_len: int,
    action: str,
) -> None:
    _RESONANCE_LOG.append({
        "posture_id": posture_id,
        "effective_intensity": effective_intensity,
        "blend_factor": blend_factor,
        "original_len": original_len,
        "shaped_len": shaped_len,
        "action": action,
        "timestamp": time.time(),
    })
    if len(_RESONANCE_LOG) > _MAX_LOG:
        _RESONANCE_LOG[:] = _RESONANCE_LOG[-_MAX_LOG:]
