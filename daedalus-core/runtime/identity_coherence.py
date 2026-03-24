# runtime/identity_coherence.py
"""
Identity coherence evaluator for Daedalus.

Detects mismatches across posture, expression, autonomy tier,
operator context, and session continuity.  Proposes resolution
actions that adjust expression-level parameters only — never
posture, tier, safety, or autonomy.

No persistence.  No emotional inference.  No psychological modeling.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_COHERENCE_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50

# ── Mismatch rules ───────────────────────────────────────────────
# Each rule returns a mismatch dict or None.

def _check_posture_expression(pid: str, expr: Dict[str, Any]) -> Dict[str, Any] | None:
    """Posture <-> expression alignment."""
    if pid in ("SHROUD", "NULL", "DORMANT") and expr.get("comfort_layer"):
        return {
            "type": "posture_expression",
            "detail": f"{pid} posture with comfort layer enabled",
            "severity": "high",
            "resolution": "suppress_comfort_layer",
        }
    if pid == "TALON" and expr.get("verbosity") in ("high", "medium"):
        return {
            "type": "posture_expression",
            "detail": "TALON posture with non-low verbosity",
            "severity": "medium",
            "resolution": "reduce_verbosity",
        }
    if pid in ("VEIL", "SHROUD") and expr.get("continuity_cues"):
        return {
            "type": "posture_expression",
            "detail": f"{pid} posture with continuity cues enabled",
            "severity": "high",
            "resolution": "suppress_cycle_cues",
        }
    return None


def _check_posture_tier(pid: str, tid: str) -> Dict[str, Any] | None:
    """Posture <-> autonomy tier alignment."""
    if pid in ("SHROUD", "NULL", "DORMANT") and tid not in ("TIER_0", None):
        return {
            "type": "posture_tier",
            "detail": f"{pid} posture with tier {tid} (expected TIER_0)",
            "severity": "medium",
            "resolution": "note_tier_mismatch",
        }
    if pid == "TALON" and tid not in ("TIER_DEFENSIVE", "TIER_0", None):
        return {
            "type": "posture_tier",
            "detail": f"TALON posture with tier {tid} (expected TIER_DEFENSIVE)",
            "severity": "low",
            "resolution": "note_tier_mismatch",
        }
    return None


def _check_posture_context(pid: str, ctx: Dict[str, Any]) -> Dict[str, Any] | None:
    """Posture <-> operator context alignment."""
    focus = ctx.get("operator_focus_level", "medium")
    intent = ctx.get("interaction_intent", "explicit")

    if pid == "SENTINEL_QUIET" and intent == "reflective":
        return {
            "type": "posture_context",
            "detail": "SENTINEL_QUIET with reflective intent",
            "severity": "low",
            "resolution": "suppress_cycle_cues",
        }
    if pid in ("VEIL", "SHROUD") and focus == "high" and intent == "exploratory":
        return {
            "type": "posture_context",
            "detail": f"{pid} with high focus exploratory intent",
            "severity": "low",
            "resolution": "suppress_cycle_cues",
        }
    return None


def _check_continuity_posture(pid: str, cstate: Dict[str, Any]) -> Dict[str, Any] | None:
    """Continuity strength <-> posture compatibility."""
    strength = cstate.get("continuity_strength", "low")

    if pid in ("VEIL", "SHROUD", "NULL", "DORMANT") and strength in ("medium", "high"):
        return {
            "type": "continuity_posture",
            "detail": f"{pid} posture with {strength} continuity",
            "severity": "high",
            "resolution": "adjust_continuity_strength",
        }
    if pid == "SENTINEL_QUIET" and strength == "high":
        return {
            "type": "continuity_posture",
            "detail": f"SENTINEL_QUIET with high continuity",
            "severity": "medium",
            "resolution": "adjust_continuity_strength",
        }
    return None


def _check_continuity_focus(ctx: Dict[str, Any], cstate: Dict[str, Any]) -> Dict[str, Any] | None:
    """Continuity strength <-> operator focus compatibility."""
    strength = cstate.get("continuity_strength", "low")
    focus = ctx.get("operator_focus_level", "medium")

    if focus == "low" and strength == "high":
        return {
            "type": "continuity_focus",
            "detail": "high continuity with low operator focus",
            "severity": "medium",
            "resolution": "adjust_continuity_strength",
        }
    return None


def _check_intent_expression(ctx: Dict[str, Any], expr: Dict[str, Any], pid: str) -> Dict[str, Any] | None:
    """Interaction intent <-> expression framing compatibility."""
    intent = ctx.get("interaction_intent", "explicit")
    framing = expr.get("framing_style", "default")

    if pid == "COMPANION" and intent == "reflective" and not expr.get("continuity_cues"):
        return {
            "type": "intent_expression",
            "detail": "COMPANION reflective intent without continuity cues",
            "severity": "low",
            "resolution": "adjust_framing_style",
        }
    return None


def _check_companion_low_continuity(pid: str, ctx: Dict[str, Any], cstate: Dict[str, Any]) -> Dict[str, Any] | None:
    """COMPANION + low continuity + reflective intent."""
    if pid != "COMPANION":
        return None
    intent = ctx.get("interaction_intent", "explicit")
    strength = cstate.get("continuity_strength", "low")
    if intent == "reflective" and strength == "low":
        return {
            "type": "companion_continuity",
            "detail": "COMPANION with reflective intent but low continuity",
            "severity": "low",
            "resolution": "adjust_continuity_strength",
        }
    return None


# ── Public API ───────────────────────────────────────────────────

def detect_mismatches(
    posture_id: str,
    tier_id: str | None = None,
    operator_context: Dict[str, Any] | None = None,
    continuity_state: Dict[str, Any] | None = None,
    expression_profile: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Detect mismatches across all runtime identity layers."""
    ctx = operator_context or {}
    cstate = continuity_state or {}
    expr = expression_profile or {}
    tid = tier_id or ""

    checks = [
        _check_posture_expression(posture_id, expr),
        _check_posture_tier(posture_id, tid),
        _check_posture_context(posture_id, ctx),
        _check_continuity_posture(posture_id, cstate),
        _check_continuity_focus(ctx, cstate),
        _check_intent_expression(ctx, expr, posture_id),
        _check_companion_low_continuity(posture_id, ctx, cstate),
    ]
    return [c for c in checks if c is not None]


def resolve_mismatches(mismatch_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Produce resolution actions for detected mismatches.

    Resolution actions adjust expression-level parameters only.
    They never change posture, tier, safety, or autonomy.
    """
    actions: List[Dict[str, Any]] = []
    seen: set = set()
    for m in mismatch_list:
        res = m.get("resolution", "")
        if res and res not in seen:
            seen.add(res)
            actions.append({
                "action": res,
                "source_mismatch": m["type"],
                "severity": m.get("severity", "low"),
                "detail": m.get("detail", ""),
            })
    return actions


def compute_coherence_state(
    posture_id: str,
    tier_id: str | None = None,
    operator_context: Dict[str, Any] | None = None,
    continuity_state: Dict[str, Any] | None = None,
    expression_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute the full coherence evaluation."""
    mismatches = detect_mismatches(
        posture_id, tier_id, operator_context,
        continuity_state, expression_profile,
    )
    resolutions = resolve_mismatches(mismatches)

    n_mismatches = len(mismatches)
    if n_mismatches == 0:
        score = 100.0
    elif n_mismatches <= 1:
        score = 85.0
    elif n_mismatches <= 3:
        score = 60.0
    else:
        score = max(0.0, 100.0 - n_mismatches * 15.0)

    state = {
        "coherence_score": round(score, 1),
        "mismatches": mismatches,
        "resolutions": resolutions,
        "n_mismatches": n_mismatches,
        "posture_id": posture_id,
        "tier_id": tier_id,
        "timestamp": time.time(),
    }

    _COHERENCE_LOG.append({
        "score": state["coherence_score"],
        "n_mismatches": n_mismatches,
        "resolutions": [r["action"] for r in resolutions],
        "posture_id": posture_id,
        "timestamp": state["timestamp"],
    })
    if len(_COHERENCE_LOG) > _MAX_LOG:
        _COHERENCE_LOG[:] = _COHERENCE_LOG[-_MAX_LOG:]

    return state


def get_coherence_summary() -> Dict[str, Any]:
    """Return a summary of the most recent coherence evaluation."""
    if _COHERENCE_LOG:
        last = _COHERENCE_LOG[-1]
    else:
        last = {"score": 100.0, "n_mismatches": 0, "resolutions": [], "posture_id": "?"}
    return {
        "last_score": last.get("score", 100.0),
        "last_n_mismatches": last.get("n_mismatches", 0),
        "last_resolutions": last.get("resolutions", []),
        "last_posture_id": last.get("posture_id", "?"),
        "total_evaluations": len(_COHERENCE_LOG),
        "recent_log": list(_COHERENCE_LOG[-5:]),
    }


def get_coherence_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_COHERENCE_LOG[-limit:])
