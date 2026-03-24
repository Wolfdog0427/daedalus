# runtime/tier3_scorecards.py
"""
Governance scorecards.

Combines KPIs, forecasts, anomalies, and planning signals into
graded scorecards at system, environment, and policy levels.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_SCORECARD_LOG: List[Dict[str, Any]] = []


def get_scorecard_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_SCORECARD_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ------------------------------------------------------------------
# System scorecard
# ------------------------------------------------------------------

def generate_system_scorecard() -> Dict[str, Any]:
    """Generate a graded scorecard for the entire governance system."""
    factors: List[str] = []

    try:
        from runtime.tier3_kpis import compute_system_kpis
        kpi_report = compute_system_kpis()
        kpis = kpi_report.get("kpis", {})
    except Exception:
        kpis = {}

    drift = kpis.get("drift_stability_index", 100.0)
    anomaly_rate = kpis.get("anomaly_rate", 0.0)
    readiness = kpis.get("readiness_trend_score", 0.0)
    pol_health = kpis.get("policy_lifecycle_health", 100.0)
    plan_eff = kpis.get("plan_effectiveness", 0.0)

    raw = (drift * 0.25
           + (100 - anomaly_rate) * 0.20
           + readiness * 0.15
           + pol_health * 0.25
           + min(plan_eff, 100) * 0.15)
    score = round(max(0, min(100, raw)), 1)
    grade = _grade_from_score(score)

    if drift < 70:
        factors.append(f"drift stability low ({drift}%)")
    if anomaly_rate > 30:
        factors.append(f"anomaly rate high ({anomaly_rate}%)")
    if pol_health < 60:
        factors.append(f"policy lifecycle health low ({pol_health}%)")
    if not factors:
        factors.append("all indicators within acceptable ranges")

    result = {
        "scope": "system",
        "score": score,
        "grade": grade,
        "kpis": kpis,
        "factors": factors,
        "timestamp": time.time(),
    }

    _SCORECARD_LOG.append({
        "type": "system", "score": score, "grade": grade,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scorecard",
        f"system scorecard: {grade} ({score}/100)",
        {"scope": "system", "score": score, "grade": grade},
    )

    return result


# ------------------------------------------------------------------
# Environment scorecard
# ------------------------------------------------------------------

def generate_environment_scorecard(env_id: str) -> Dict[str, Any]:
    """Generate a graded scorecard for a single environment."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_report = compute_environment_kpis(env_id)
        if kpi_report.get("error"):
            return kpi_report
        kpis = kpi_report.get("kpis", {})
        env_name = kpi_report.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    factors: List[str] = []

    drift = kpis.get("drift_stability_index", 100.0)
    health_grade = kpis.get("health_grade", "unknown")
    health_findings = kpis.get("health_findings", 0)
    packs = kpis.get("applied_packs", 0)
    pol_cov = kpis.get("policy_coverage", 0)
    readiness = kpis.get("promotion_readiness")

    health_score_map = {
        "healthy": 100, "minor_issues": 75,
        "drift_detected": 50, "needs_attention": 25, "unknown": 50,
    }
    health_num = health_score_map.get(health_grade, 50)

    raw = drift * 0.30 + health_num * 0.30
    if readiness is not None:
        raw += readiness * 0.20
        raw += min(pol_cov * 5, 100) * 0.10
        raw += (100 if packs > 0 else 0) * 0.10
    else:
        raw += min(pol_cov * 5, 100) * 0.20
        raw += (100 if packs > 0 else 0) * 0.20

    score = round(max(0, min(100, raw)), 1)
    grade = _grade_from_score(score)

    if drift < 70:
        factors.append(f"drift stability low ({drift}%)")
    if health_grade in ("needs_attention", "drift_detected"):
        factors.append(f"health: {health_grade} ({health_findings} findings)")
    if packs == 0:
        factors.append("no governance packs applied")
    if not factors:
        factors.append("environment is well-governed")

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "score": score,
        "grade": grade,
        "kpis": kpis,
        "factors": factors,
        "timestamp": time.time(),
    }

    _SCORECARD_LOG.append({
        "type": "environment", "env_id": env_id,
        "score": score, "grade": grade,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scorecard",
        f"env '{env_name}' scorecard: {grade} ({score}/100)",
        {"scope": "environment", "env_id": env_id,
         "score": score, "grade": grade},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy scorecard
# ------------------------------------------------------------------

def generate_policy_scorecard(policy_id: str) -> Dict[str, Any]:
    """Generate a graded scorecard for a single policy."""
    try:
        from runtime.tier3_kpis import compute_policy_kpis
        kpi_report = compute_policy_kpis(policy_id)
        if kpi_report.get("error"):
            return kpi_report
        kpis = kpi_report.get("kpis", {})
        pol_name = kpi_report.get("policy_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute policy KPIs"}

    factors: List[str] = []

    completeness = kpis.get("completeness_score", 0)
    enabled = kpis.get("enabled", False)
    retired = kpis.get("retired", False)
    env_presence = kpis.get("environment_presence", 0)
    has_interval = kpis.get("has_interval", False)

    if retired:
        score = 20.0
        grade = "F"
        factors.append("policy is retired")
    else:
        raw = completeness * 0.40
        raw += (100 if enabled else 0) * 0.20
        raw += min(env_presence * 25, 100) * 0.20
        raw += (100 if has_interval else 0) * 0.20
        score = round(max(0, min(100, raw)), 1)
        grade = _grade_from_score(score)

        if completeness < 100:
            factors.append(f"completeness: {completeness}%")
        if not enabled:
            factors.append("policy is disabled")
        if env_presence == 0:
            factors.append("not present in any environment")
        if not has_interval:
            factors.append("no evaluation interval configured")

    if not factors:
        factors.append("policy is well-configured")

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "score": score,
        "grade": grade,
        "kpis": kpis,
        "factors": factors,
        "timestamp": time.time(),
    }

    _SCORECARD_LOG.append({
        "type": "policy", "policy_id": policy_id,
        "score": score, "grade": grade,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scorecard",
        f"policy '{pol_name}' scorecard: {grade} ({score}/100)",
        {"scope": "policy", "policy_id": policy_id,
         "score": score, "grade": grade},
        [policy_id],
    )

    return result
