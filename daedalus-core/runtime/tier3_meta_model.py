# runtime/tier3_meta_model.py
"""
Meta-governance modeling.

Projects whether governance objectives are achievable within a
given horizon and identifies structural blockers.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_META_MODEL_LOG: List[Dict[str, Any]] = []

_MATURITY_ORDER = {"Emerging": 0, "Developing": 1, "Mature": 2, "Advanced": 3}
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def get_meta_model_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_META_MODEL_LOG[-limit:])


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


# ------------------------------------------------------------------
# Objective trajectory
# ------------------------------------------------------------------

def model_objective_trajectory(
    objective_id: str,
    horizon: str = "30d",
) -> Dict[str, Any]:
    """Project governance trajectory toward an objective."""
    from runtime.tier3_objectives import get_objective
    obj = get_objective(objective_id)
    if obj is None:
        return {"error": True, "reason": f"objective '{objective_id}' not found"}

    # Current alignment
    alignment = _safe(
        lambda: __import__(
            "runtime.tier3_alignment", fromlist=["evaluate_system_alignment"]
        ).evaluate_system_alignment(objective_id),
        default={},
    )
    current_score = alignment.get("alignment_score", 0)
    gaps = alignment.get("blocking_gaps", [])

    # Benchmark trend data
    bench = _safe(
        lambda: __import__(
            "runtime.tier3_benchmark", fromlist=["benchmark_system"]
        ).benchmark_system(),
        default={},
    )
    strengths = bench.get("strengths", [])
    weaknesses = bench.get("weaknesses", [])

    # Forecast signals
    forecasts = _safe(
        lambda: __import__(
            "runtime.tier3_forecast", fromlist=["get_forecast_log"]
        ).get_forecast_log(20),
        default=[],
    )
    improving_signals = sum(
        1 for f in forecasts if f.get("trend") == "improving"
    )
    declining_signals = sum(
        1 for f in forecasts if f.get("trend") == "declining"
    )

    # Estimate trajectory
    if current_score >= 100:
        trajectory = "achieved"
        confidence = "high"
    elif improving_signals > declining_signals and len(gaps) <= 2:
        trajectory = "on_track"
        confidence = "medium"
    elif improving_signals > declining_signals:
        trajectory = "progressing"
        confidence = "low"
    elif declining_signals > improving_signals:
        trajectory = "at_risk"
        confidence = "medium"
    else:
        trajectory = "stalled"
        confidence = "low"

    blockers: List[str] = []
    for g in gaps:
        metric = g.get("metric", "?")
        blockers.append(f"{metric}: current={g.get('current')}, target={g.get('target')}")

    result = {
        "objective_id": objective_id,
        "objective_name": obj["name"],
        "horizon": horizon,
        "current_alignment": current_score,
        "trajectory": trajectory,
        "confidence": confidence,
        "improving_signals": improving_signals,
        "declining_signals": declining_signals,
        "structural_blockers": blockers,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "timestamp": time.time(),
    }

    _META_MODEL_LOG.append({
        "type": "trajectory", "objective_id": objective_id,
        "trajectory": trajectory, "score": current_score,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "meta_model",
        f"objective '{obj['name']}' trajectory: {trajectory} "
        f"(alignment {current_score}/100, {horizon})",
        {"objective_id": objective_id, "trajectory": trajectory,
         "score": current_score, "horizon": horizon},
        [objective_id],
    )

    return result


# ------------------------------------------------------------------
# Objective feasibility
# ------------------------------------------------------------------

def model_objective_feasibility(objective_id: str) -> Dict[str, Any]:
    """Assess whether an objective is structurally achievable."""
    from runtime.tier3_objectives import get_objective
    obj = get_objective(objective_id)
    if obj is None:
        return {"error": True, "reason": f"objective '{objective_id}' not found"}

    issues: List[str] = []
    strengths: List[str] = []

    # Check maturity tier feasibility
    tgt_mat = obj.get("target_maturity_tier")
    if tgt_mat:
        mat = _safe(
            lambda: __import__(
                "runtime.tier3_maturity", fromlist=["compute_system_maturity"]
            ).compute_system_maturity(),
            default={},
        )
        cur_tier = mat.get("maturity_tier", "Emerging")
        cur_ord = _MATURITY_ORDER.get(cur_tier, 0)
        tgt_ord = _MATURITY_ORDER.get(tgt_mat, 0)
        gap = tgt_ord - cur_ord
        if gap <= 0:
            strengths.append(f"maturity already at or above {tgt_mat}")
        elif gap == 1:
            strengths.append(f"maturity gap is one tier ({cur_tier} → {tgt_mat})")
        else:
            issues.append(f"maturity gap is {gap} tiers ({cur_tier} → {tgt_mat})")

    # Check risk tier feasibility
    tgt_risk = obj.get("target_risk_tier")
    if tgt_risk:
        risk = _safe(
            lambda: __import__(
                "runtime.tier3_risk", fromlist=["compute_system_risk"]
            ).compute_system_risk(),
            default={},
        )
        cur_risk = risk.get("risk_tier", "critical")
        cur_ord = _RISK_ORDER.get(cur_risk, 3)
        tgt_ord = _RISK_ORDER.get(tgt_risk, 0)
        gap = cur_ord - tgt_ord
        if gap <= 0:
            strengths.append(f"risk already at or below {tgt_risk}")
        elif gap == 1:
            strengths.append(f"risk gap is one tier ({cur_risk} → {tgt_risk})")
        else:
            issues.append(f"risk gap is {gap} tiers ({cur_risk} → {tgt_risk})")

    # Check target metrics reachability using anomaly signals
    anomalies = _safe(
        lambda: __import__(
            "runtime.tier3_anomaly", fromlist=["get_anomaly_registry"]
        ).get_anomaly_registry(50),
        default=[],
    )
    if len(anomalies) > 10:
        issues.append(f"high anomaly volume ({len(anomalies)}) may impede progress")
    elif len(anomalies) <= 2:
        strengths.append("low anomaly volume")

    # Check KPI-metric target count
    n_targets = len(obj.get("target_metrics", {}))
    if n_targets > 5:
        issues.append(f"objective has {n_targets} KPI targets — consider narrowing scope")
    elif n_targets <= 2:
        strengths.append("focused objective with few targets")

    if obj.get("target_sla_pass_rate") is not None:
        sla = _safe(
            lambda: __import__(
                "runtime.tier3_sla", fromlist=["evaluate_system_sla"]
            ).evaluate_system_sla(),
            default={},
        )
        if sla.get("passed"):
            strengths.append("system SLA currently passing")
        else:
            issues.append("system SLA currently failing")

    feasible = len(issues) == 0
    feasibility = "feasible" if feasible else ("challenging" if len(issues) <= 2 else "unlikely")

    result = {
        "objective_id": objective_id,
        "objective_name": obj["name"],
        "feasibility": feasibility,
        "structural_issues": issues,
        "structural_strengths": strengths,
        "timestamp": time.time(),
    }

    _META_MODEL_LOG.append({
        "type": "feasibility", "objective_id": objective_id,
        "feasibility": feasibility,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "meta_model",
        f"objective '{obj['name']}' feasibility: {feasibility} "
        f"({len(issues)} issues, {len(strengths)} strengths)",
        {"objective_id": objective_id, "feasibility": feasibility},
        [objective_id],
    )

    return result
