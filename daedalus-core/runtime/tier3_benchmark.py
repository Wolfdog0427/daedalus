# runtime/tier3_benchmark.py
"""
Governance benchmarking.

Compares current KPIs, SLAs, risk scores, and scorecards against
historical self-baselines derived from the KPI and scorecard logs.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_BENCHMARK_LOG: List[Dict[str, Any]] = []


def get_benchmark_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_BENCHMARK_LOG[-limit:])


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


def _trend(current: float, historical_avg: float) -> str:
    if historical_avg == 0:
        return "stable"
    delta_pct = ((current - historical_avg) / max(abs(historical_avg), 0.01)) * 100
    if delta_pct > 10:
        return "improving"
    if delta_pct < -10:
        return "declining"
    return "stable"


def _percentile(current: float, values: List[float]) -> float:
    """Compute the percentile rank of *current* within *values*."""
    if not values:
        return 50.0
    below = sum(1 for v in values if v < current)
    return round(below / len(values) * 100, 1)


# ------------------------------------------------------------------
# System benchmark
# ------------------------------------------------------------------

def benchmark_system() -> Dict[str, Any]:
    """Benchmark system-wide governance against historical baselines."""
    # Current KPIs
    kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis().get("kpis", {}),
        default={},
    )

    # Historical KPI log entries for baseline
    hist_kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["get_kpi_log"]
        ).get_kpi_log(100),
        default=[],
    )
    sys_hist = [h for h in hist_kpis if h.get("type") == "system"]

    # Current scorecard
    scorecard = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["generate_system_scorecard"]
        ).generate_system_scorecard(),
        default={},
    )

    # Current SLA
    sla = _safe(
        lambda: __import__(
            "runtime.tier3_sla", fromlist=["evaluate_system_sla"]
        ).evaluate_system_sla(),
        default={},
    )

    # Current risk
    risk = _safe(
        lambda: __import__(
            "runtime.tier3_risk", fromlist=["compute_system_risk"]
        ).compute_system_risk(),
        default={},
    )

    metrics: Dict[str, Dict[str, Any]] = {}
    strengths: List[str] = []
    weaknesses: List[str] = []

    for key in ("drift_stability_index", "anomaly_rate",
                "readiness_trend_score", "policy_lifecycle_health",
                "pack_consistency_score", "lineage_volatility",
                "plan_effectiveness"):
        current = kpis.get(key, 0)
        hist_vals = [h.get(key, 0) for h in sys_hist if key in h]
        avg = round(sum(hist_vals) / len(hist_vals), 2) if hist_vals else current
        t = _trend(current, avg)
        pct = _percentile(current, hist_vals)
        metrics[key] = {
            "current": current, "historical_avg": avg,
            "trend": t, "percentile": pct,
        }
        if t == "improving":
            strengths.append(key)
        elif t == "declining":
            weaknesses.append(key)

    score = scorecard.get("score", 0)
    grade = scorecard.get("grade", "?")

    result = {
        "scope": "system",
        "metrics": metrics,
        "scorecard_grade": grade,
        "scorecard_score": score,
        "sla_passed": sla.get("passed"),
        "risk_score": risk.get("risk_score", 0),
        "risk_tier": risk.get("risk_tier", "?"),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "timestamp": time.time(),
    }

    _BENCHMARK_LOG.append({
        "type": "system", "grade": grade, "score": score,
        "n_strengths": len(strengths), "n_weaknesses": len(weaknesses),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "benchmark_report",
        f"system benchmark: {grade} ({score}/100), "
        f"{len(strengths)} strengths, {len(weaknesses)} weaknesses",
        {"scope": "system", "grade": grade, "score": score},
    )

    return result


# ------------------------------------------------------------------
# Environment benchmark
# ------------------------------------------------------------------

def benchmark_environment(env_id: str) -> Dict[str, Any]:
    """Benchmark a single environment against its history."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis, get_kpi_log
        kpi_r = compute_environment_kpis(env_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        env_name = kpi_r.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    hist = _safe(
        lambda: [h for h in get_kpi_log(100)
                 if h.get("type") == "environment" and h.get("env_id") == env_id],
        default=[],
    )

    metrics: Dict[str, Dict[str, Any]] = {}
    strengths: List[str] = []
    weaknesses: List[str] = []

    for key in ("drift_stability_index", "health_findings",
                "applied_packs", "policy_coverage"):
        current = kpis.get(key, 0)
        if isinstance(current, str):
            continue
        hist_vals = [h.get(key, 0) for h in hist if key in h]
        avg = round(sum(hist_vals) / len(hist_vals), 2) if hist_vals else current
        t = _trend(current, avg)
        pct = _percentile(current, hist_vals)
        metrics[key] = {
            "current": current, "historical_avg": avg,
            "trend": t, "percentile": pct,
        }
        if t == "improving":
            strengths.append(key)
        elif t == "declining":
            weaknesses.append(key)

    scorecard = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["generate_environment_scorecard"]
        ).generate_environment_scorecard(env_id),
        default={},
    )

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "metrics": metrics,
        "scorecard_grade": scorecard.get("grade", "?"),
        "scorecard_score": scorecard.get("score", 0),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "timestamp": time.time(),
    }

    _BENCHMARK_LOG.append({
        "type": "environment", "env_id": env_id,
        "grade": scorecard.get("grade", "?"),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "benchmark_report",
        f"env '{env_name}' benchmark: {scorecard.get('grade', '?')}",
        {"scope": "environment", "env_id": env_id},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy benchmark
# ------------------------------------------------------------------

def benchmark_policy(policy_id: str) -> Dict[str, Any]:
    """Benchmark a single policy against its history."""
    try:
        from runtime.tier3_kpis import compute_policy_kpis, get_kpi_log
        kpi_r = compute_policy_kpis(policy_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        pol_name = kpi_r.get("policy_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute policy KPIs"}

    hist = _safe(
        lambda: [h for h in get_kpi_log(100)
                 if h.get("type") == "policy" and h.get("policy_id") == policy_id],
        default=[],
    )

    metrics: Dict[str, Dict[str, Any]] = {}
    strengths: List[str] = []
    weaknesses: List[str] = []

    for key in ("completeness_score", "environment_presence", "lineage_records"):
        current = kpis.get(key, 0)
        if not isinstance(current, (int, float)):
            continue
        hist_vals = [h.get(key, 0) for h in hist if key in h]
        avg = round(sum(hist_vals) / len(hist_vals), 2) if hist_vals else current
        t = _trend(current, avg)
        pct = _percentile(current, hist_vals)
        metrics[key] = {
            "current": current, "historical_avg": avg,
            "trend": t, "percentile": pct,
        }
        if t == "improving":
            strengths.append(key)
        elif t == "declining":
            weaknesses.append(key)

    scorecard = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["generate_policy_scorecard"]
        ).generate_policy_scorecard(policy_id),
        default={},
    )

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "metrics": metrics,
        "scorecard_grade": scorecard.get("grade", "?"),
        "scorecard_score": scorecard.get("score", 0),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "timestamp": time.time(),
    }

    _BENCHMARK_LOG.append({
        "type": "policy", "policy_id": policy_id,
        "grade": scorecard.get("grade", "?"),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "benchmark_report",
        f"policy '{pol_name}' benchmark: {scorecard.get('grade', '?')}",
        {"scope": "policy", "policy_id": policy_id},
        [policy_id],
    )

    return result
