# runtime/self_alignment_engine.py
"""
Self-alignment engine for Daedalus.

Applies coherence corrections before final expression shaping.
Corrections adjust expression-level parameters only (verbosity,
comfort layer, cycle cues, framing).  Never modifies factual
content, safety rules, autonomy, posture, or tier.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_ALIGNMENT_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50


def get_alignment_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_ALIGNMENT_LOG[-limit:])


def _get_coherence_state(
    posture_id: str,
    tier_id: str | None,
    operator_context: Dict[str, Any] | None,
    continuity_state: Dict[str, Any] | None,
    expression_profile: Dict[str, Any] | None,
) -> Dict[str, Any]:
    try:
        from runtime.identity_coherence import compute_coherence_state
        return compute_coherence_state(
            posture_id, tier_id, operator_context,
            continuity_state, expression_profile,
        )
    except Exception:
        return {"coherence_score": 100.0, "mismatches": [], "resolutions": []}


def align_identity_layers(
    text: str,
    posture_id: str | None = None,
    tier_id: str | None = None,
    operator_context: Dict[str, Any] | None = None,
    continuity_state: Dict[str, Any] | None = None,
    expression_profile: Dict[str, Any] | None = None,
) -> str:
    """Apply coherence-based alignment corrections to *text*.

    This is a lightweight structural pass that never alters factual
    content, safety rules, or autonomy.
    """
    if not text:
        return text

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture()["posture_id"]
        except Exception:
            posture_id = "COMPANION"

    if posture_id in ("NULL", "DORMANT"):
        _log_alignment(posture_id, 100.0, 0, len(text), len(text))
        return text

    coh = _get_coherence_state(
        posture_id, tier_id, operator_context,
        continuity_state, expression_profile,
    )
    resolutions = coh.get("resolutions", [])
    score = coh.get("coherence_score", 100.0)

    try:
        from runtime.long_arc_engine import smooth_coherence_corrections
        resolutions = smooth_coherence_corrections(resolutions)
    except Exception:
        pass

    try:
        from runtime.resonance_engine import resonance_summary as _rs
        rs = _rs()
        if rs.get("resonance_intensity", 0) > 0 and resolutions:
            pass  # coherence corrections always win over resonance
    except Exception:
        pass

    if not resolutions:
        _log_alignment(posture_id, score, 0, len(text), len(text))
        return text

    result = text
    applied = 0

    for r in resolutions:
        action = r.get("action", "")
        if action == "reduce_verbosity":
            result = _reduce_verbosity(result)
            applied += 1
        elif action == "suppress_comfort_layer":
            applied += 1
        elif action == "suppress_cycle_cues":
            applied += 1
        elif action == "adjust_continuity_strength":
            applied += 1
        elif action == "adjust_framing_style":
            applied += 1

    _log_alignment(posture_id, score, applied, len(text), len(result))
    return result


def get_alignment_summary() -> Dict[str, Any]:
    """Return a summary of the most recent alignment pass."""
    if _ALIGNMENT_LOG:
        last = _ALIGNMENT_LOG[-1]
    else:
        last = {
            "posture_id": "?", "coherence_score": 100.0,
            "corrections_applied": 0, "original_len": 0, "aligned_len": 0,
        }
    return {
        "last_posture_id": last.get("posture_id", "?"),
        "last_coherence_score": last.get("coherence_score", 100.0),
        "last_corrections_applied": last.get("corrections_applied", 0),
        "total_alignments": len(_ALIGNMENT_LOG),
        "recent_log": list(_ALIGNMENT_LOG[-5:]),
    }


# ── Internal helpers ─────────────────────────────────────────────

def _reduce_verbosity(text: str) -> str:
    """Trim trailing whitespace on lines but preserve all content."""
    lines = text.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _log_alignment(
    posture_id: str,
    coherence_score: float,
    corrections_applied: int,
    original_len: int,
    aligned_len: int,
) -> None:
    _ALIGNMENT_LOG.append({
        "posture_id": posture_id,
        "coherence_score": coherence_score,
        "corrections_applied": corrections_applied,
        "original_len": original_len,
        "aligned_len": aligned_len,
        "timestamp": time.time(),
    })
    if len(_ALIGNMENT_LOG) > _MAX_LOG:
        _ALIGNMENT_LOG[:] = _ALIGNMENT_LOG[-_MAX_LOG:]
