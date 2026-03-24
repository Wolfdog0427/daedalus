# runtime/tier3_maturity.py
"""
Governance maturity evaluators.

Scores governance maturity at system, environment, and policy levels
and assigns a maturity tier: Emerging / Developing / Mature / Advanced.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_MATURITY_LOG: List[Dict[str, Any]] = []


def get_maturity_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_MATURITY_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _maturity_tier(score: float) -> str:
    if score >= 80:
        return "Advanced"
    if score >= 60:
        return "Mature"
    if score >= 35:
        return "Developing"
    return "Emerging"


# ------------------------------------------------------------------
# System maturity
# ------------------------------------------------------------------

def compute_system_maturity() -> Dict[str, Any]:
    """Compute governance maturity for the entire system."""
    factors: List[str] = []
    focus: List[str] = []
    scores: Dict[str, float] = {}

    kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis().get("kpis", {}),
        default={},
    )

    # Drift control (0-100)
    drift = kpis.get("drift_stability_index", 0)
    scores["drift_control"] = drift
    if drift >= 80:
        factors.append("strong drift control")
    elif drift < 50:
        focus.append("improve drift containment")

    # Anomaly management (invert anomaly rate)
    anomaly_rate = kpis.get("anomaly_rate", 0)
    scores["anomaly_management"] = max(0, 100 - anomaly_rate)
    if anomaly_rate > 20:
        focus.append("reduce anomaly rate")
    elif anomaly_rate <= 5:
        factors.append("low anomaly rate")

    # Readiness stability
    readiness = kpis.get("readiness_trend_score", 0)
    scores["readiness_stability"] = readiness
    if readiness >= 70:
        factors.append("strong readiness")
    elif readiness < 30:
        focus.append("improve promotion readiness")

    # Policy lifecycle completeness
    pol_health = kpis.get("policy_lifecycle_health", 0)
    scores["policy_completeness"] = pol_health
    if pol_health >= 80:
        factors.append("mature policy lifecycle")
    elif pol_health < 50:
        focus.append("complete policy definitions")

    # Pack consistency
    pack_score = kpis.get("pack_consistency_score", 0)
    scores["pack_consistency"] = pack_score
    if pack_score >= 90:
        factors.append("consistent packs")

    # Lineage clarity (invert volatility, cap at 100)
    lineage_vol = kpis.get("lineage_volatility", 0)
    lineage_clarity = max(0, min(100, 100 - lineage_vol * 10))
    scores["lineage_clarity"] = lineage_clarity
    if lineage_vol > 5:
        focus.append("stabilise lineage")
    elif lineage_vol <= 1:
        factors.append("stable lineage")

    # Strategic planning adoption
    plans = _safe(
        lambda: __import__(
            "runtime.tier3_planning", fromlist=["get_plan_registry"]
        ).get_plan_registry(50),
        default=[],
    )
    plan_score = min(len(plans) * 20, 100)
    scores["strategic_planning"] = plan_score
    if plan_score >= 60:
        factors.append("active strategic planning")
    elif plan_score == 0:
        focus.append("adopt strategic planning")

    raw = sum(scores.values()) / max(len(scores), 1)
    overall = round(max(0, min(100, raw)), 1)
    tier = _maturity_tier(overall)

    if not factors:
        factors.append("governance framework in early stages")
    if not focus:
        focus.append("maintain current trajectory")

    result = {
        "scope": "system",
        "maturity_score": overall,
        "maturity_tier": tier,
        "dimension_scores": scores,
        "contributing_factors": factors,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _MATURITY_LOG.append({
        "type": "system", "score": overall, "tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "maturity_report",
        f"system maturity: {tier} ({overall}/100)",
        {"scope": "system", "score": overall, "tier": tier},
    )

    return result


# ------------------------------------------------------------------
# Environment maturity
# ------------------------------------------------------------------

def compute_environment_maturity(env_id: str) -> Dict[str, Any]:
    """Compute maturity for a single environment."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_r = compute_environment_kpis(env_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        env_name = kpi_r.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    factors: List[str] = []
    focus: List[str] = []
    scores: Dict[str, float] = {}

    drift = kpis.get("drift_stability_index", 0)
    scores["drift_control"] = drift
    if drift >= 80:
        factors.append("strong drift control")
    elif drift < 50:
        focus.append("improve drift containment")

    health_map = {"healthy": 100, "minor_issues": 75, "drift_detected": 50,
                  "needs_attention": 25, "unknown": 40}
    health_grade = kpis.get("health_grade", "unknown")
    scores["health"] = health_map.get(health_grade, 40)
    if health_grade == "healthy":
        factors.append("healthy environment")
    elif health_grade in ("needs_attention", "drift_detected"):
        focus.append("address health findings")

    packs = kpis.get("applied_packs", 0)
    scores["pack_adoption"] = min(packs * 50, 100)
    if packs == 0:
        focus.append("apply governance packs")
    else:
        factors.append(f"{packs} pack(s) applied")

    pol_cov = kpis.get("policy_coverage", 0)
    scores["policy_coverage"] = min(pol_cov * 15, 100)
    if pol_cov == 0:
        focus.append("add policies")

    readiness = kpis.get("promotion_readiness")
    if readiness is not None:
        scores["promotion_readiness"] = readiness
        if readiness >= 70:
            factors.append("promotion-ready")
        elif readiness < 40:
            focus.append("improve promotion readiness")
    else:
        scores["promotion_readiness"] = 50

    raw = sum(scores.values()) / max(len(scores), 1)
    overall = round(max(0, min(100, raw)), 1)
    tier = _maturity_tier(overall)

    if not factors:
        factors.append("environment governance in early stages")
    if not focus:
        focus.append("maintain current trajectory")

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "maturity_score": overall,
        "maturity_tier": tier,
        "dimension_scores": scores,
        "contributing_factors": factors,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _MATURITY_LOG.append({
        "type": "environment", "env_id": env_id,
        "score": overall, "tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "maturity_report",
        f"env '{env_name}' maturity: {tier} ({overall}/100)",
        {"scope": "environment", "env_id": env_id, "score": overall, "tier": tier},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy maturity
# ------------------------------------------------------------------

def compute_policy_maturity(policy_id: str) -> Dict[str, Any]:
    """Compute maturity for a single policy."""
    try:
        from runtime.tier3_kpis import compute_policy_kpis
        kpi_r = compute_policy_kpis(policy_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        pol_name = kpi_r.get("policy_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute policy KPIs"}

    factors: List[str] = []
    focus: List[str] = []
    scores: Dict[str, float] = {}

    completeness = kpis.get("completeness_score", 0)
    scores["completeness"] = completeness
    if completeness == 100:
        factors.append("fully defined")
    elif completeness < 50:
        focus.append("add conditions and actions")

    scores["enabled"] = 100 if kpis.get("enabled") else 0
    if not kpis.get("enabled"):
        focus.append("enable the policy")

    env_presence = kpis.get("environment_presence", 0)
    scores["environment_adoption"] = min(env_presence * 30, 100)
    if env_presence == 0:
        focus.append("add to at least one environment")
    else:
        factors.append(f"present in {env_presence} environment(s)")

    scores["scheduling"] = 100 if kpis.get("has_interval") else 0
    if not kpis.get("has_interval"):
        focus.append("configure evaluation interval")

    lineage = kpis.get("lineage_records", 0)
    scores["lineage_maturity"] = min(lineage * 25, 100)
    if lineage >= 2:
        factors.append("active lineage history")

    if kpis.get("retired"):
        scores["lifecycle"] = 20
        focus.append("policy is retired — consider archiving")
    else:
        scores["lifecycle"] = 80
        factors.append("policy is active")

    raw = sum(scores.values()) / max(len(scores), 1)
    overall = round(max(0, min(100, raw)), 1)
    tier = _maturity_tier(overall)

    if not factors:
        factors.append("policy governance in early stages")
    if not focus:
        focus.append("maintain current configuration")

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "maturity_score": overall,
        "maturity_tier": tier,
        "dimension_scores": scores,
        "contributing_factors": factors,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _MATURITY_LOG.append({
        "type": "policy", "policy_id": policy_id,
        "score": overall, "tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "maturity_report",
        f"policy '{pol_name}' maturity: {tier} ({overall}/100)",
        {"scope": "policy", "policy_id": policy_id,
         "score": overall, "tier": tier},
        [policy_id],
    )

    return result
