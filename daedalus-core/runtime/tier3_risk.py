# runtime/tier3_risk.py
"""
Governance risk scoring.

Computes numeric risk scores (0–100) and risk tiers at system,
environment, and policy levels.  All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_RISK_LOG: List[Dict[str, Any]] = []


def get_risk_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_RISK_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def _tier(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


# ------------------------------------------------------------------
# System risk
# ------------------------------------------------------------------

def compute_system_risk() -> Dict[str, Any]:
    """Compute an aggregate risk score for the governance system."""
    factors: List[str] = []
    risk = 0.0

    kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis().get("kpis", {}),
        default={},
    )

    drift = kpis.get("drift_stability_index", 100.0)
    if drift < 70:
        contrib = (70 - drift) * 0.5
        risk += contrib
        factors.append(f"drift instability ({drift}%)")

    anomaly_rate = kpis.get("anomaly_rate", 0.0)
    if anomaly_rate > 10:
        contrib = min(anomaly_rate * 0.4, 30)
        risk += contrib
        factors.append(f"elevated anomaly rate ({anomaly_rate}%)")

    readiness = kpis.get("readiness_trend_score", 0.0)
    if readiness < 50 and readiness > 0:
        contrib = (50 - readiness) * 0.3
        risk += contrib
        factors.append(f"low readiness ({readiness})")

    pol_health = kpis.get("policy_lifecycle_health", 100.0)
    if pol_health < 60:
        contrib = (60 - pol_health) * 0.3
        risk += contrib
        factors.append(f"policy health low ({pol_health}%)")

    lineage_vol = kpis.get("lineage_volatility", 0.0)
    if lineage_vol > 3:
        contrib = min((lineage_vol - 3) * 3, 15)
        risk += contrib
        factors.append(f"lineage volatility ({lineage_vol})")

    forecasts = _safe(
        lambda: __import__(
            "runtime.tier3_forecast", fromlist=["get_forecast_log"]
        ).get_forecast_log(20),
        default=[],
    )
    negative_fc = sum(
        1 for f in forecasts
        if "increase" in f.get("prediction", "") or "declining" in f.get("prediction", "")
    )
    if negative_fc > len(forecasts) * 0.5 and forecasts:
        risk += 10
        factors.append(f"negative forecast trends ({negative_fc}/{len(forecasts)})")

    score = round(max(0, min(100, risk)), 1)
    tier = _tier(score)

    if not factors:
        factors.append("no significant risk signals")

    result = {
        "scope": "system",
        "risk_score": score,
        "risk_tier": tier,
        "factors": factors,
        "timestamp": time.time(),
    }

    _RISK_LOG.append({
        "type": "system", "risk_score": score, "risk_tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "risk_report",
        f"system risk: {tier} ({score}/100)",
        {"scope": "system", "risk_score": score, "risk_tier": tier},
    )

    return result


# ------------------------------------------------------------------
# Environment risk
# ------------------------------------------------------------------

def compute_environment_risk(env_id: str) -> Dict[str, Any]:
    """Compute risk for a single environment."""
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
    risk = 0.0

    drift = kpis.get("drift_stability_index", 100.0)
    if drift < 70:
        risk += (70 - drift) * 0.6
        factors.append(f"drift instability ({drift}%)")

    health_grade = kpis.get("health_grade", "unknown")
    grade_risk = {
        "needs_attention": 25, "drift_detected": 15,
        "minor_issues": 5, "unknown": 10,
    }
    g_risk = grade_risk.get(health_grade, 0)
    if g_risk:
        risk += g_risk
        factors.append(f"health: {health_grade}")

    packs = kpis.get("applied_packs", 0)
    if packs == 0:
        risk += 10
        factors.append("no governance packs applied")

    readiness = kpis.get("promotion_readiness")
    if readiness is not None and readiness < 50:
        risk += (50 - readiness) * 0.3
        factors.append(f"low promotion readiness ({readiness})")

    score = round(max(0, min(100, risk)), 1)
    tier = _tier(score)

    if not factors:
        factors.append("no significant risk signals")

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "risk_score": score,
        "risk_tier": tier,
        "factors": factors,
        "timestamp": time.time(),
    }

    _RISK_LOG.append({
        "type": "environment", "env_id": env_id,
        "risk_score": score, "risk_tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "risk_report",
        f"env '{env_name}' risk: {tier} ({score}/100)",
        {"scope": "environment", "env_id": env_id,
         "risk_score": score, "risk_tier": tier},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy risk
# ------------------------------------------------------------------

def compute_policy_risk(policy_id: str) -> Dict[str, Any]:
    """Compute risk for a single policy."""
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
    risk = 0.0

    if kpis.get("retired"):
        risk += 15
        factors.append("policy is retired")

    completeness = kpis.get("completeness_score", 0)
    if completeness < 100:
        risk += (100 - completeness) * 0.3
        factors.append(f"completeness {completeness}%")

    if kpis.get("enabled") and not kpis.get("has_conditions"):
        risk += 20
        factors.append("enabled without conditions")

    if kpis.get("environment_presence", 0) == 0:
        risk += 10
        factors.append("not in any environment")

    if not kpis.get("has_interval"):
        risk += 5
        factors.append("no evaluation interval")

    score = round(max(0, min(100, risk)), 1)
    tier = _tier(score)

    if not factors:
        factors.append("no significant risk signals")

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "risk_score": score,
        "risk_tier": tier,
        "factors": factors,
        "timestamp": time.time(),
    }

    _RISK_LOG.append({
        "type": "policy", "policy_id": policy_id,
        "risk_score": score, "risk_tier": tier,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "risk_report",
        f"policy '{pol_name}' risk: {tier} ({score}/100)",
        {"scope": "policy", "policy_id": policy_id,
         "risk_score": score, "risk_tier": tier},
        [policy_id],
    )

    return result
