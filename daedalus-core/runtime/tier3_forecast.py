# runtime/tier3_forecast.py
"""
Governance forecasting.

Produces read-only predictions about future drift, policy activity,
and promotion readiness by analysing historical snapshots, lineage,
drift logs, and health scores.  All functions are side-effect-free
and operator-triggered.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_FORECAST_LOG: List[Dict[str, Any]] = []


def get_forecast_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_FORECAST_LOG[-limit:])


def clear_forecast_log() -> None:
    _FORECAST_LOG.clear()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _trend(values: List[float]) -> str:
    if len(values) < 2:
        return "stable"
    delta = values[-1] - values[0]
    if delta > 0:
        return "increasing"
    elif delta < 0:
        return "decreasing"
    return "stable"


def _confidence(n_samples: int) -> str:
    if n_samples >= 5:
        return "high"
    if n_samples >= 2:
        return "medium"
    return "low"


# ------------------------------------------------------------------
# Environment drift forecast
# ------------------------------------------------------------------

def forecast_environment_drift(
    env_id: str,
    horizon: int = 5,
) -> Dict[str, Any]:
    """
    Forecast future drift for an environment based on historical
    drift logs and health scores.
    """
    factors: List[str] = []

    drift_entries: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_env_drift import get_drift_log
        for entry in get_drift_log(100):
            if entry.get("env_a") == env_id or entry.get("env_b") == env_id:
                drift_entries.append(entry)
    except Exception:
        pass

    health_entries: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_env_health import get_health_log
        for entry in get_health_log(100):
            if entry.get("env_id") == env_id:
                health_entries.append(entry)
    except Exception:
        pass

    drift_values = [1.0 if e.get("has_drift") else 0.0 for e in drift_entries]
    drift_trend = _trend(drift_values)
    if drift_trend == "increasing":
        factors.append("drift frequency increasing over time")

    health_values = [e.get("findings_count", 0) for e in health_entries]
    health_trend = _trend(health_values)
    if health_trend == "increasing":
        factors.append("health findings growing")

    lineage_count = 0
    try:
        from runtime.tier3_lineage import get_lineage_for_env
        lineage_count = len(get_lineage_for_env(env_id))
        if lineage_count > 5:
            factors.append(f"high lineage activity ({lineage_count} records)")
    except Exception:
        pass

    n_samples = len(drift_entries) + len(health_entries)

    if drift_trend == "increasing" or health_trend == "increasing":
        prediction = "drift_likely_to_increase"
    elif drift_trend == "decreasing" and health_trend != "increasing":
        prediction = "drift_likely_to_decrease"
    else:
        prediction = "drift_stable"

    if not factors:
        factors.append("no significant signals detected")

    result = {
        "env_id": env_id,
        "horizon": horizon,
        "prediction": prediction,
        "drift_trend": drift_trend,
        "health_trend": health_trend,
        "confidence": _confidence(n_samples),
        "factors": factors,
        "samples": n_samples,
        "timestamp": time.time(),
    }

    _FORECAST_LOG.append({
        "type": "environment_drift",
        "env_id": env_id,
        "prediction": prediction,
        "confidence": result["confidence"],
        "timestamp": result["timestamp"],
    })

    return result


# ------------------------------------------------------------------
# Policy activity forecast
# ------------------------------------------------------------------

def forecast_policy_activity(
    policy_id: str,
    horizon: int = 5,
) -> Dict[str, Any]:
    """
    Forecast future evaluation/trigger activity for a policy based
    on evaluation logs and change history.
    """
    factors: List[str] = []

    eval_entries: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_policies import get_policy_eval_log
        for entry in get_policy_eval_log(100):
            for pr in entry.get("policy_results", []):
                if pr.get("policy_id") == policy_id:
                    eval_entries.append(pr)
    except Exception:
        pass

    change_entries: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_policies import get_policy_change_log
        for entry in get_policy_change_log(100):
            if entry.get("policy_id") == policy_id:
                change_entries.append(entry)
    except Exception:
        pass

    trigger_values = [
        1.0 if e.get("result") == "triggered" else 0.0
        for e in eval_entries
    ]
    trigger_trend = _trend(trigger_values)
    trigger_rate = (
        sum(trigger_values) / len(trigger_values)
        if trigger_values else 0.0
    )

    if trigger_trend == "increasing":
        factors.append("trigger frequency increasing")
    if trigger_rate > 0.5:
        factors.append(f"high trigger rate ({trigger_rate:.0%})")
    if change_entries:
        factors.append(f"{len(change_entries)} recent change(s) to policy")

    n_samples = len(eval_entries) + len(change_entries)

    if trigger_trend == "increasing":
        prediction = "activity_increasing"
    elif trigger_trend == "decreasing":
        prediction = "activity_decreasing"
    else:
        prediction = "activity_stable"

    if not factors:
        factors.append("no significant signals detected")

    result = {
        "policy_id": policy_id,
        "horizon": horizon,
        "prediction": prediction,
        "trigger_trend": trigger_trend,
        "trigger_rate": round(trigger_rate, 3),
        "confidence": _confidence(n_samples),
        "factors": factors,
        "samples": n_samples,
        "timestamp": time.time(),
    }

    _FORECAST_LOG.append({
        "type": "policy_activity",
        "policy_id": policy_id,
        "prediction": prediction,
        "confidence": result["confidence"],
        "timestamp": result["timestamp"],
    })

    return result


# ------------------------------------------------------------------
# Promotion readiness forecast
# ------------------------------------------------------------------

def forecast_promotion_readiness(
    source_env_id: str,
    target_env_id: str,
    horizon: int = 5,
) -> Dict[str, Any]:
    """
    Forecast how promotion readiness between two environments is
    likely to evolve, based on historical readiness scores and drift.
    """
    factors: List[str] = []

    readiness_entries: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_env_health import get_readiness_log
        for entry in get_readiness_log(100):
            if (entry.get("source_env_id") == source_env_id
                    and entry.get("target_env_id") == target_env_id):
                readiness_entries.append(entry)
    except Exception:
        pass

    scores = [e.get("readiness_score", 0) for e in readiness_entries]
    score_trend = _trend(scores)
    current_score = scores[-1] if scores else None

    if score_trend == "increasing":
        factors.append("readiness scores improving")
    elif score_trend == "decreasing":
        factors.append("readiness scores declining")

    blocker_counts = [e.get("n_blockers", 0) for e in readiness_entries]
    blocker_trend = _trend(blocker_counts)
    if blocker_trend == "increasing":
        factors.append("blocker count rising")

    n_samples = len(readiness_entries)

    if score_trend == "increasing" and blocker_trend != "increasing":
        prediction = "readiness_improving"
    elif score_trend == "decreasing" or blocker_trend == "increasing":
        prediction = "readiness_declining"
    else:
        prediction = "readiness_stable"

    if not factors:
        factors.append("no significant signals detected")

    result = {
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "horizon": horizon,
        "prediction": prediction,
        "score_trend": score_trend,
        "blocker_trend": blocker_trend,
        "current_score": current_score,
        "confidence": _confidence(n_samples),
        "factors": factors,
        "samples": n_samples,
        "timestamp": time.time(),
    }

    _FORECAST_LOG.append({
        "type": "promotion_readiness",
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "prediction": prediction,
        "confidence": result["confidence"],
        "timestamp": result["timestamp"],
    })

    return result
