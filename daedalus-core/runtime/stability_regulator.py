# runtime/stability_regulator.py
"""
Expressive stability regulator for Daedalus.

Tracks short-term and long-arc stability signals across posture,
tier, continuity, and coherence.  Detects oscillation (rapid
posture/tier switching) and jitter (rapid continuity/coherence
fluctuations).  Session-local only — no persistence, no personal
data, no emotional inference.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict, List

_WINDOW = 20
_MAX_LOG = 50

_lock = threading.Lock()

_recent_postures: deque = deque(maxlen=_WINDOW)
_recent_tiers: deque = deque(maxlen=_WINDOW)
_recent_expression_profiles: deque = deque(maxlen=_WINDOW)
_recent_continuity_strengths: deque = deque(maxlen=_WINDOW)
_recent_coherence_scores: deque = deque(maxlen=_WINDOW)

_stability_score: float = 100.0
_oscillation_index: float = 0.0
_jitter_index: float = 0.0
_update_count: int = 0

_STABILITY_LOG: List[Dict[str, Any]] = []


def get_stability_state() -> Dict[str, Any]:
    """Return the current stability state."""
    with _lock:
        return {
            "stability_score": round(_stability_score, 2),
            "oscillation_index": round(_oscillation_index, 3),
            "jitter_index": round(_jitter_index, 3),
            "update_count": _update_count,
            "recent_postures": list(_recent_postures),
            "recent_tiers": list(_recent_tiers),
            "recent_continuity_strengths": list(_recent_continuity_strengths),
            "recent_coherence_scores": list(_recent_coherence_scores),
        }


def get_stability_log(limit: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        return list(_STABILITY_LOG[-limit:])


def _transition_rate(seq: deque) -> float:
    """Fraction of consecutive entries that differ."""
    if len(seq) < 2:
        return 0.0
    items = list(seq)
    transitions = sum(1 for a, b in zip(items, items[1:]) if a != b)
    return transitions / (len(items) - 1)


def _variance_index(seq: deque) -> float:
    """Normalized variance for numeric sequences (0-1 scale)."""
    vals = [v for v in seq if isinstance(v, (int, float))]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    max_possible = 2500.0  # score range 0-100 squared / 4
    return min(1.0, var / max_possible) if max_possible > 0 else 0.0


def update_stability(
    posture_id: str | None = None,
    tier_id: str | None = None,
    continuity_state: Dict[str, Any] | None = None,
    coherence_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Record latest signals and recompute stability metrics."""
    global _update_count

    with _lock:
        if posture_id is not None:
            _recent_postures.append(posture_id)
        if tier_id is not None:
            _recent_tiers.append(tier_id)

        cstate = continuity_state or {}
        strength = cstate.get("continuity_strength", "low")
        _recent_continuity_strengths.append(strength)

        cohstate = coherence_state or {}
        cscore = cohstate.get("coherence_score", 100.0)
        _recent_coherence_scores.append(cscore)

        _update_count += 1

    return _compute_stability_metrics_locked()


def _compute_stability_metrics_locked() -> Dict[str, Any]:
    """Recompute oscillation, jitter, and stability from recent history."""
    global _stability_score, _oscillation_index, _jitter_index

    with _lock:
        posture_rate = _transition_rate(_recent_postures)
        tier_rate = _transition_rate(_recent_tiers)
        _oscillation_index = round(max(posture_rate, tier_rate), 3)

        continuity_rate = _transition_rate(_recent_continuity_strengths)
        coherence_var = _variance_index(_recent_coherence_scores)
        _jitter_index = round(max(continuity_rate, coherence_var), 3)

        penalty = (_oscillation_index * 40.0) + (_jitter_index * 30.0)
        _stability_score = round(max(0.0, min(100.0, 100.0 - penalty)), 2)

        record = {
            "stability_score": _stability_score,
            "oscillation_index": _oscillation_index,
            "jitter_index": _jitter_index,
            "update_count": _update_count,
            "timestamp": time.time(),
        }
        _STABILITY_LOG.append(record)
        if len(_STABILITY_LOG) > _MAX_LOG:
            _STABILITY_LOG[:] = _STABILITY_LOG[-_MAX_LOG:]

    return get_stability_state()


def compute_stability_metrics() -> Dict[str, Any]:
    """Recompute oscillation, jitter, and stability from recent history."""
    return _compute_stability_metrics_locked()


def reset_stability() -> Dict[str, Any]:
    """Reset all stability state to defaults."""
    global _stability_score, _oscillation_index, _jitter_index, _update_count

    with _lock:
        _recent_postures.clear()
        _recent_tiers.clear()
        _recent_expression_profiles.clear()
        _recent_continuity_strengths.clear()
        _recent_coherence_scores.clear()
        _stability_score = 100.0
        _oscillation_index = 0.0
        _jitter_index = 0.0
        _update_count = 0

    return get_stability_state()
