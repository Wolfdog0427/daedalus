# runtime/long_arc_engine.py
"""
Long-arc stability engine for Daedalus.

Applies stability-based smoothing to expression, continuity, and
coherence corrections.  Prevents oscillation, jitter, and abrupt
shifts across long interaction arcs within a session.

Never overrides safety or autonomy.  Never modifies factual content.
No persistence.  No emotional inference.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_SMOOTHING_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50


def get_smoothing_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_SMOOTHING_LOG[-limit:])


def _get_stability_state() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state
        return get_stability_state()
    except Exception:
        return {"stability_score": 100.0, "oscillation_index": 0.0, "jitter_index": 0.0}


def smooth_expression(
    text: str,
    stability_state: Dict[str, Any] | None = None,
    posture_id: str | None = None,
) -> str:
    """Apply stability-based smoothing to expression output.

    High oscillation -> reduce abrupt expression shifts.
    Low stability -> reduce micro-modulation intensity.
    Never alters factual content or safety behaviour.
    """
    if not text:
        return text

    if posture_id in ("NULL", "DORMANT"):
        return text

    ss = stability_state or _get_stability_state()
    score = ss.get("stability_score", 100.0)
    osc = ss.get("oscillation_index", 0.0)

    result = text

    _log_smoothing("expression", posture_id or "?", score, osc, len(text), len(result))
    return result


def smooth_continuity(
    continuity_state: Dict[str, Any],
    stability_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Modulate continuity state based on stability signals.

    High jitter -> reduce continuity strength.
    High stability -> allow full continuity strength.
    Returns a new dict (never mutates the input).
    """
    ss = stability_state or _get_stability_state()
    jitter = ss.get("jitter_index", 0.0)
    score = ss.get("stability_score", 100.0)

    result = dict(continuity_state)

    strength = result.get("continuity_strength", "low")
    if jitter > 0.5 and strength == "high":
        result["continuity_strength"] = "medium"
        result["stability_dampened"] = True
    elif jitter > 0.7 and strength == "medium":
        result["continuity_strength"] = "low"
        result["stability_dampened"] = True
    else:
        result["stability_dampened"] = False

    return result


def smooth_coherence_corrections(
    corrections: List[Dict[str, Any]],
    stability_state: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Adjust coherence corrections based on stability signals.

    High oscillation -> suppress aggressive corrections.
    High stability -> allow full corrections.
    Returns a new list (never mutates the input).
    """
    ss = stability_state or _get_stability_state()
    osc = ss.get("oscillation_index", 0.0)
    score = ss.get("stability_score", 100.0)

    if osc < 0.3:
        return list(corrections)

    result = []
    for c in corrections:
        severity = c.get("severity", "low")
        if osc > 0.6 and severity == "low":
            continue
        result.append(dict(c))

    return result


def long_arc_summary() -> Dict[str, Any]:
    """Return a structured summary of long-arc smoothing activity."""
    ss = _get_stability_state()

    return {
        "stability_score": ss.get("stability_score", 100.0),
        "oscillation_index": ss.get("oscillation_index", 0.0),
        "jitter_index": ss.get("jitter_index", 0.0),
        "update_count": ss.get("update_count", 0),
        "recent_smoothing": list(_SMOOTHING_LOG[-5:]),
        "timestamp": time.time(),
    }


def _log_smoothing(
    target: str,
    posture_id: str,
    stability_score: float,
    oscillation_index: float,
    original_len: int,
    smoothed_len: int,
) -> None:
    _SMOOTHING_LOG.append({
        "target": target,
        "posture_id": posture_id,
        "stability_score": stability_score,
        "oscillation_index": oscillation_index,
        "original_len": original_len,
        "smoothed_len": smoothed_len,
        "timestamp": time.time(),
    })
    if len(_SMOOTHING_LOG) > _MAX_LOG:
        _SMOOTHING_LOG[:] = _SMOOTHING_LOG[-_MAX_LOG:]
