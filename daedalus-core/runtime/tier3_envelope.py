# runtime/tier3_envelope.py
"""
Strategic governance envelope.

Unifies persona weighting, mode constraints, objectives, and the full
analytics stack into a single read-only governance context object.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_ENVELOPE_LOG: List[Dict[str, Any]] = []


def get_envelope_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_ENVELOPE_LOG[-limit:])


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


def _weighted_score(raw: float, weight: float) -> float:
    return round(raw * weight, 2)


def build_governance_envelope(
    persona_id: str,
    mode_id: str,
) -> Dict[str, Any]:
    """Build a unified governance envelope contextualised by persona + mode."""

    # Resolve persona
    from runtime.tier3_personas import get_persona
    persona = get_persona(persona_id)
    if persona is None:
        return {"error": True, "reason": f"persona '{persona_id}' not found"}

    # Resolve mode
    from runtime.tier3_modes import get_mode
    mode = get_mode(mode_id)
    if mode is None:
        return {"error": True, "reason": f"mode '{mode_id}' not found"}

    weights = persona.get("weighting_profile", {})
    constraints = mode.get("constraints", {})

    # ---- Gather analytics (all read-only) ----

    kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis().get("kpis", {}),
        default={},
    )

    sla = _safe(
        lambda: __import__(
            "runtime.tier3_sla", fromlist=["evaluate_system_sla"]
        ).evaluate_system_sla(),
        default={},
    )

    risk = _safe(
        lambda: __import__(
            "runtime.tier3_risk", fromlist=["compute_system_risk"]
        ).compute_system_risk(),
        default={},
    )

    maturity = _safe(
        lambda: __import__(
            "runtime.tier3_maturity", fromlist=["compute_system_maturity"]
        ).compute_system_maturity(),
        default={},
    )

    forecasts = _safe(
        lambda: __import__(
            "runtime.tier3_forecast", fromlist=["get_forecast_log"]
        ).get_forecast_log(10),
        default=[],
    )

    anomalies = _safe(
        lambda: __import__(
            "runtime.tier3_anomaly", fromlist=["get_anomaly_registry"]
        ).get_anomaly_registry(20),
        default=[],
    )

    plans = _safe(
        lambda: __import__(
            "runtime.tier3_planning", fromlist=["get_plan_registry"]
        ).get_plan_registry(10),
        default=[],
    )

    # ---- Compute weighted dimension scores ----

    drift_raw = kpis.get("drift_stability_index", 50)
    anomaly_rate_raw = kpis.get("anomaly_rate", 0)
    readiness_raw = kpis.get("readiness_trend_score", 50)
    maturity_score = maturity.get("maturity_score", 50)
    risk_score = risk.get("risk_score", 50)
    sla_score = 100.0 if sla.get("passed") else 0.0

    dimension_scores = {
        "kpis": _weighted_score(
            (drift_raw + readiness_raw) / 2, weights.get("kpis", 1.0)),
        "sla": _weighted_score(sla_score, weights.get("sla", 1.0)),
        "risk": _weighted_score(
            max(0, 100 - risk_score), weights.get("risk", 1.0)),
        "maturity": _weighted_score(
            maturity_score, weights.get("maturity", 1.0)),
        "readiness": _weighted_score(
            readiness_raw, weights.get("readiness", 1.0)),
        "drift": _weighted_score(drift_raw, weights.get("drift", 1.0)),
        "anomalies": _weighted_score(
            max(0, 100 - anomaly_rate_raw), weights.get("anomalies", 1.0)),
    }

    total_weight = sum(weights.get(k, 1.0) for k in dimension_scores)
    composite = round(
        sum(dimension_scores.values()) / max(total_weight, 0.01), 1)

    # ---- Constraint evaluation ----

    constraint_results: List[Dict[str, Any]] = []
    pressure_points: List[str] = []

    if "max_drift" in constraints:
        actual = 100 - drift_raw
        met = actual <= constraints["max_drift"]
        constraint_results.append({
            "constraint": "max_drift",
            "threshold": constraints["max_drift"],
            "actual": actual, "met": met,
        })
        if not met:
            pressure_points.append(
                f"drift ({actual}) exceeds max_drift ({constraints['max_drift']})")

    if "min_readiness" in constraints:
        met = readiness_raw >= constraints["min_readiness"]
        constraint_results.append({
            "constraint": "min_readiness",
            "threshold": constraints["min_readiness"],
            "actual": readiness_raw, "met": met,
        })
        if not met:
            pressure_points.append(
                f"readiness ({readiness_raw}) below min_readiness "
                f"({constraints['min_readiness']})")

    if "max_risk" in constraints:
        met = risk_score <= constraints["max_risk"]
        constraint_results.append({
            "constraint": "max_risk",
            "threshold": constraints["max_risk"],
            "actual": risk_score, "met": met,
        })
        if not met:
            pressure_points.append(
                f"risk ({risk_score}) exceeds max_risk ({constraints['max_risk']})")

    if "max_anomaly_rate" in constraints:
        met = anomaly_rate_raw <= constraints["max_anomaly_rate"]
        constraint_results.append({
            "constraint": "max_anomaly_rate",
            "threshold": constraints["max_anomaly_rate"],
            "actual": anomaly_rate_raw, "met": met,
        })
        if not met:
            pressure_points.append(
                f"anomaly rate ({anomaly_rate_raw}) exceeds "
                f"max_anomaly_rate ({constraints['max_anomaly_rate']})")

    if "min_maturity_score" in constraints:
        met = maturity_score >= constraints["min_maturity_score"]
        constraint_results.append({
            "constraint": "min_maturity_score",
            "threshold": constraints["min_maturity_score"],
            "actual": maturity_score, "met": met,
        })
        if not met:
            pressure_points.append(
                f"maturity ({maturity_score}) below min_maturity_score "
                f"({constraints['min_maturity_score']})")

    constraints_met = sum(1 for c in constraint_results if c["met"])

    # ---- Objective alignment ----

    objective_alignments: List[Dict[str, Any]] = []
    conflicts: List[str] = []

    for obj_id in persona.get("objective_bindings", []):
        ali = _safe(
            lambda oid=obj_id: __import__(
                "runtime.tier3_alignment", fromlist=["evaluate_system_alignment"]
            ).evaluate_system_alignment(oid),
            default={},
        )
        if ali.get("error"):
            continue
        objective_alignments.append({
            "objective_id": obj_id,
            "objective_name": ali.get("objective_name", "?"),
            "alignment_score": ali.get("alignment_score", 0),
            "gaps": len(ali.get("blocking_gaps", [])),
        })
        if ali.get("alignment_score", 0) < 50:
            conflicts.append(
                f"low alignment ({ali['alignment_score']}/100) to "
                f"objective '{ali.get('objective_name', '?')}'")

    # ---- Assemble envelope ----

    envelope = {
        "persona_id": persona_id,
        "persona_name": persona["name"],
        "mode_id": mode_id,
        "mode_name": mode["name"],
        "composite_score": composite,
        "dimension_scores": dimension_scores,
        "weighting_profile": weights,
        "constraint_results": constraint_results,
        "constraints_met": constraints_met,
        "constraints_total": len(constraint_results),
        "pressure_points": pressure_points,
        "objective_alignments": objective_alignments,
        "conflicts": conflicts,
        "analytics_summary": {
            "kpis_available": len(kpis),
            "sla_passed": sla.get("passed"),
            "risk_score": risk_score,
            "risk_tier": risk.get("risk_tier", "?"),
            "maturity_tier": maturity.get("maturity_tier", "?"),
            "maturity_score": maturity_score,
            "forecast_count": len(forecasts),
            "anomaly_count": len(anomalies),
            "plan_count": len(plans),
        },
        "timestamp": time.time(),
    }

    _ENVELOPE_LOG.append({
        "persona_id": persona_id,
        "persona_name": persona["name"],
        "mode_id": mode_id,
        "mode_name": mode["name"],
        "composite_score": composite,
        "constraints_met": constraints_met,
        "constraints_total": len(constraint_results),
        "pressure_points_count": len(pressure_points),
        "conflicts_count": len(conflicts),
        "timestamp": envelope["timestamp"],
    })

    _add_insight(
        "governance_envelope",
        f"envelope '{persona['name']}' + '{mode['name']}': "
        f"composite={composite}  constraints={constraints_met}/"
        f"{len(constraint_results)}  "
        f"pressure={len(pressure_points)}  conflicts={len(conflicts)}",
        {
            "persona_id": persona_id,
            "mode_id": mode_id,
            "composite_score": composite,
        },
        [persona_id, mode_id],
    )

    return envelope
