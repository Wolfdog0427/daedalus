# knowledge/stability_engine.py

"""
Stability Engine

Evaluates and enforces system stability for the Self-Healing Orchestrator (SHO).

Computes a composite stability score from:
- consistency (weight 0.30)
- coherence (weight 0.25)
- knowledge quality (weight 0.25)
- subsystem health (weight 0.10)
- regression detector state (weight 0.10)

Patch-specific assessment overlays the patch's risk and scope
onto the baseline system stability to determine approval risk.
"""

from __future__ import annotations

from typing import Dict, Any, Optional


# -------------------------------------------------------------------
# RISK CLASSIFICATION
# -------------------------------------------------------------------

def _classify_risk(score: float) -> str:
    if score >= 0.85:
        return "low"
    if score >= 0.65:
        return "medium"
    if score >= 0.40:
        return "high"
    return "critical"


# -------------------------------------------------------------------
# SUBSYSTEM HEALTH SCORE
# -------------------------------------------------------------------

def _health_score(health: Dict[str, str]) -> float:
    """Convert subsystem health map to a 0-1 score."""
    if not health:
        return 0.5
    values = {"ok": 1.0, "degraded": 0.5, "down": 0.0}
    scores = [values.get(v, 0.5) for v in health.values()]
    return sum(scores) / len(scores)


# -------------------------------------------------------------------
# CORE STABILITY EVALUATION
# -------------------------------------------------------------------

def evaluate_stability(patch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluate current system stability, optionally in the context of
    a proposed patch. Returns a composite stability score (0-1),
    risk classification, and breakdown.
    """
    try:
        from knowledge.self_model import get_self_model
        sm = get_self_model()
    except Exception:
        sm = {"confidence": {}, "subsystem_health": {}}

    conf = sm.get("confidence", {})
    consistency = conf.get("consistency", 0.5)
    coherence = conf.get("graph_coherence", 0.5)
    quality = conf.get("knowledge_quality", 0.5)
    health = sm.get("subsystem_health", {})

    h_score = _health_score(health)

    regression_penalty = 0.0
    try:
        from knowledge.meta_reasoner import get_regression_detector
        rd = get_regression_detector()
        if rd.defensive_active:
            regression_penalty = 0.15
    except (ImportError, Exception):
        pass

    composite = (
        consistency * 0.30
        + coherence * 0.25
        + quality * 0.25
        + h_score * 0.10
        + (1.0 - regression_penalty) * 0.10
    )
    composite = max(0.0, min(1.0, composite))

    risk = _classify_risk(composite)

    result: Dict[str, Any] = {
        "stability_score": round(composite, 4),
        "risk": risk,
        "breakdown": {
            "consistency": round(consistency, 4),
            "coherence": round(coherence, 4),
            "quality": round(quality, 4),
            "subsystem_health": round(h_score, 4),
            "regression_penalty": round(regression_penalty, 4),
        },
    }

    if patch is not None:
        patch_risk = _assess_patch_risk(patch, composite)
        result["patch_assessment"] = patch_risk

    return result


def _assess_patch_risk(patch: Dict[str, Any], baseline: float) -> Dict[str, Any]:
    """Overlay patch-specific risk onto the system's baseline stability."""
    scope = patch.get("scope", "unknown")
    scope_weight = {"global": 0.20, "subsystem": 0.10, "local": 0.05}.get(scope, 0.10)

    risk_level = patch.get("risk_level", "medium")
    risk_weight = {"low": 0.05, "medium": 0.10, "high": 0.20, "critical": 0.30}.get(risk_level, 0.10)

    adjusted = max(0.0, baseline - scope_weight - risk_weight)
    recommendation = "approve" if adjusted >= 0.55 else ("review" if adjusted >= 0.35 else "reject")

    return {
        "adjusted_score": round(adjusted, 4),
        "risk_classification": _classify_risk(adjusted),
        "recommendation": recommendation,
        "scope_impact": round(scope_weight, 4),
        "risk_impact": round(risk_weight, 4),
    }


# -------------------------------------------------------------------
# BACKWARD-COMPATIBILITY WRAPPER
# -------------------------------------------------------------------

def enforce_stability(patch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Backward-compatible alias for evaluate_stability()."""
    return evaluate_stability(patch)
