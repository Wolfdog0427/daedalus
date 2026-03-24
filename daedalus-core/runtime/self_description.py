# runtime/self_description.py
"""
Introspection layer for Daedalus.

Provides a unified, operator-safe, governance-aware surface for
describing the current identity state.  This is a PRESENTATION
layer only — it introduces no new behaviour, no new autonomy,
no new shaping.  It consumes existing runtime and governance
signals and returns structured, read-only summaries.

Guarantees:
  - Never modifies posture, tier, expression, continuity,
    coherence, stability, resonance, or governance state.
  - Never triggers governance review (kernel.evaluate_change).
  - Never includes raw content or personal data.
  - Returns valid, minimal state even under suppressed postures
    (SHROUD, VEIL, NULL, DORMANT).
"""

from __future__ import annotations

import time
from typing import Any, Dict

_SUPPRESSED_POSTURES = {"NULL", "DORMANT", "VEIL", "SHROUD"}


def describe_current_state() -> Dict[str, Any]:
    """Return a unified, operator-safe summary of all identity layers."""
    pid = _safe_posture_id()
    suppressed = pid in _SUPPRESSED_POSTURES

    return {
        "posture_id": pid,
        "autonomy_tier": _safe_tier_id(),
        "operator_context": _safe_operator_context(),
        "continuity_state": _safe_continuity_state(suppressed),
        "coherence_state": _safe_coherence_state(suppressed),
        "stability_state": _safe_stability_state(),
        "resonance_state": _safe_resonance_state(suppressed),
        "governance_state": _safe_governance_state(),
        "suppressed": suppressed,
        "timestamp": time.time(),
    }


def describe_posture() -> Dict[str, Any]:
    """Return posture metadata from the posture engine."""
    try:
        from runtime.posture_engine import get_active_posture, explain_posture
        active = get_active_posture()
        explanation = explain_posture()
        return {
            "posture_id": active.get("posture_id", "?"),
            "name": explanation.get("name", "?"),
            "category": explanation.get("category", "?"),
            "expression_level": explanation.get("expression_level", "?"),
            "autonomy_level": explanation.get("autonomy_level", "?"),
            "safety_flags": explanation.get("safety_flags", []),
            "reason": active.get("reason", "?"),
        }
    except Exception:
        return {"posture_id": "unavailable", "error": "posture modules unavailable"}


def describe_autonomy() -> Dict[str, Any]:
    """Return current autonomy tier and constraints."""
    try:
        from runtime.autonomy_engine import get_effective_tier, explain_tier
        effective = get_effective_tier()
        explanation = explain_tier()
        return {
            "tier_id": effective.get("tier_id", "?"),
            "tier_name": explanation.get("tier_name", "?"),
            "allowed_action_categories": explanation.get("allowed_action_categories", []),
            "disallowed_action_categories": explanation.get("disallowed_action_categories", []),
            "posture_forced_tier": explanation.get("posture_forced_tier"),
            "operator_override": explanation.get("operator_override", False),
            "safety_flags": explanation.get("safety_flags", []),
        }
    except Exception:
        return {"tier_id": "unavailable", "error": "autonomy modules unavailable"}


def describe_governance() -> Dict[str, Any]:
    """Return governance-safe signals only (filtered through binding)."""
    try:
        from governance.kernel import get_kernel_state, compute_governance_health
        ks = get_kernel_state()
        health = compute_governance_health()

        persona = ks.get("persona", {})
        mode = ks.get("mode", {})
        envelope = ks.get("envelope", {})

        drift_summary = {}
        try:
            from governance.drift_detector import compute_drift_report
            dr = compute_drift_report()
            drift_summary = {
                "total_drift_score": dr.get("total_drift_score", 0),
                "average_drift_score": dr.get("average_drift_score", 0),
                "alert": dr.get("alert", False),
            }
        except Exception:
            pass

        return {
            "persona_id": persona.get("persona_id", "?"),
            "persona_name": persona.get("name", "?"),
            "mode_id": mode.get("mode_id", "?"),
            "mode_name": mode.get("name", "?"),
            "risk_ceiling": envelope.get("risk_ceiling", "?"),
            "patch_approval_threshold": envelope.get("patch_approval_threshold", "?"),
            "governance_score": health.get("governance_score", "?"),
            "kill_switch": ks.get("kill_switch", False),
            "circuit_breaker": ks.get("circuit_breaker", False),
            "stabilise_mode": ks.get("stabilise_mode", False),
            "drift": drift_summary,
        }
    except Exception:
        return {"governance_score": "unavailable", "error": "governance modules unavailable"}


def describe_expression_stack() -> Dict[str, Any]:
    """Return a summary of the active expression shaping stack."""
    pid = _safe_posture_id()
    suppressed = pid in _SUPPRESSED_POSTURES

    result: Dict[str, Any] = {"posture_id": pid, "suppressed": suppressed}

    try:
        from runtime.expression_profiles import get_profile
        prof = get_profile(pid)
        result["expression_profile"] = {
            "tone": prof.get("tone", "?"),
            "verbosity": prof.get("verbosity", "?"),
            "framing_style": prof.get("framing_style", "?"),
            "comfort_layer": prof.get("comfort_layer", False),
            "continuity_cues": prof.get("continuity_cues", False),
            "operator_attunement": prof.get("operator_attunement", False),
        }
    except Exception:
        result["expression_profile"] = {"error": "unavailable"}

    try:
        from runtime.resonance_profiles import get_resonance_profile
        rp = get_resonance_profile(pid)
        result["resonance_profile"] = {
            "intensity": rp.get("resonance_intensity", 0),
            "color": rp.get("resonance_color", "neutral"),
            "decay_rate": rp.get("resonance_decay_rate", 0),
        }
    except Exception:
        result["resonance_profile"] = {"error": "unavailable"}

    if not suppressed:
        try:
            from runtime.identity_continuity_engine import compute_continuity_weight
            result["continuity_weight"] = compute_continuity_weight(pid, {})
        except Exception:
            result["continuity_weight"] = None

        try:
            from runtime.long_arc_engine import long_arc_summary
            las = long_arc_summary()
            result["long_arc_smoothing"] = {
                "stability_score": las.get("stability_score", "?"),
                "recent_events": len(las.get("recent_smoothing", [])),
            }
        except Exception:
            result["long_arc_smoothing"] = {"error": "unavailable"}

        try:
            from runtime.self_alignment_engine import get_alignment_summary
            als = get_alignment_summary()
            result["alignment_corrections"] = {
                "recent_score": als.get("last_coherence_score", "?"),
                "recent_applied": als.get("last_applied_count", 0),
            }
        except Exception:
            result["alignment_corrections"] = {"error": "unavailable"}
    else:
        result["continuity_weight"] = 0.0
        result["long_arc_smoothing"] = {"suppressed": True}
        result["alignment_corrections"] = {"suppressed": True}

    return result


# ── Internal safe‑access helpers ─────────────────────────────────

def _safe_posture_id() -> str:
    try:
        from runtime.posture_state import get_current_posture
        return get_current_posture()["posture_id"]
    except Exception:
        return "COMPANION"


def _safe_tier_id() -> str:
    try:
        from runtime.autonomy_engine import get_effective_tier
        return get_effective_tier().get("tier_id", "TIER_1")
    except Exception:
        return "TIER_1"


def _safe_operator_context() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context
        ctx = get_context()
        return {
            "interaction_intent": ctx.get("interaction_intent", "explicit"),
            "operator_focus_level": ctx.get("operator_focus_level", "medium"),
            "operator_engagement_style": ctx.get("operator_engagement_style", "direct"),
        }
    except Exception:
        return {
            "interaction_intent": "explicit",
            "operator_focus_level": "medium",
            "operator_engagement_style": "direct",
        }


def _safe_continuity_state(suppressed: bool = False) -> Dict[str, Any]:
    if suppressed:
        return {"continuity_strength": "low", "continuity_active": False, "suppressed": True}
    try:
        from runtime.session_continuity import get_continuity_state
        cs = get_continuity_state()
        return {
            "continuity_strength": cs.get("continuity_strength", "low"),
            "continuity_active": cs.get("continuity_active", False),
        }
    except Exception:
        return {"continuity_strength": "low", "continuity_active": False}


def _safe_coherence_state(suppressed: bool = False) -> Dict[str, Any]:
    if suppressed:
        return {"coherence_score": 100.0, "mismatches": 0, "suppressed": True}
    try:
        from runtime.identity_coherence import get_coherence_summary
        cs = get_coherence_summary()
        return {
            "coherence_score": cs.get("coherence_score", 100.0),
            "mismatches": cs.get("n_mismatches", 0),
        }
    except Exception:
        return {"coherence_score": 100.0, "mismatches": 0}


def _safe_stability_state() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state
        ss = get_stability_state()
        return {
            "stability_score": ss.get("stability_score", 100.0),
            "oscillation_index": ss.get("oscillation_index", 0.0),
            "jitter_index": ss.get("jitter_index", 0.0),
        }
    except Exception:
        return {"stability_score": 100.0, "oscillation_index": 0.0, "jitter_index": 0.0}


def _safe_resonance_state(suppressed: bool = False) -> Dict[str, Any]:
    if suppressed:
        return {"intensity": 0.0, "color": "minimal", "decay_rate": 1.0,
                "blend_factor": 0.0, "suppressed": True}
    try:
        from runtime.resonance_engine import resonance_summary
        rs = resonance_summary()
        return {
            "intensity": rs.get("resonance_intensity", 0.0),
            "color": rs.get("resonance_color", "neutral"),
            "decay_rate": rs.get("resonance_decay_rate", 0.6),
            "blend_factor": rs.get("blend_factor", 1.0),
        }
    except Exception:
        return {"intensity": 0.0, "color": "neutral", "decay_rate": 0.6, "blend_factor": 1.0}


def _safe_governance_state() -> Dict[str, Any]:
    try:
        from governance.runtime_binding import get_governance_view
        from governance.kernel import get_kernel_state, compute_governance_health

        ks = get_kernel_state()
        health = compute_governance_health()
        persona = ks.get("persona", {})
        mode = ks.get("mode", {})

        return get_governance_view({
            "governance_score": health.get("governance_score", 100.0),
            "persona_id": persona.get("persona_id", "?"),
            "mode_id": mode.get("mode_id", "?"),
            "kill_switch": ks.get("kill_switch", False),
            "circuit_breaker": ks.get("circuit_breaker", False),
            "stabilise_mode": ks.get("stabilise_mode", False),
        })
    except Exception:
        return {"governance_score": "unavailable"}
