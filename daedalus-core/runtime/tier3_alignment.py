# runtime/tier3_alignment.py
"""
Governance alignment scoring.

Evaluates how closely the current governance posture (system, env,
or policy) aligns with an operator-defined objective.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_ALIGNMENT_LOG: List[Dict[str, Any]] = []

_MATURITY_ORDER = {"Emerging": 0, "Developing": 1, "Mature": 2, "Advanced": 3}
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def get_alignment_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_ALIGNMENT_LOG[-limit:])


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


def _get_objective(objective_id: str):
    from runtime.tier3_objectives import get_objective
    return get_objective(objective_id)


def _metric_gap(current: float, target: float, higher_is_better: bool) -> Dict[str, Any]:
    delta = round(current - target, 2)
    met = (current >= target) if higher_is_better else (current <= target)
    return {"current": current, "target": target, "delta": delta, "met": met}


# ------------------------------------------------------------------
# System alignment
# ------------------------------------------------------------------

def evaluate_system_alignment(objective_id: str) -> Dict[str, Any]:
    """Score system alignment against an objective."""
    obj = _get_objective(objective_id)
    if obj is None:
        return {"error": True, "reason": f"objective '{objective_id}' not found"}

    gaps: List[Dict[str, Any]] = []
    warnings: List[str] = []
    focus: List[str] = []
    checks_met = 0
    checks_total = 0

    # KPI-based target metrics
    kpis = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis().get("kpis", {}),
        default={},
    )

    higher_better = {
        "drift_stability_index", "readiness_trend_score",
        "policy_lifecycle_health", "pack_consistency_score",
        "plan_effectiveness",
    }
    lower_better = {"anomaly_rate", "lineage_volatility"}

    for key, target in obj.get("target_metrics", {}).items():
        checks_total += 1
        current = kpis.get(key)
        if current is None:
            warnings.append(f"metric '{key}' not available in system KPIs")
            continue
        hib = key in higher_better
        g = _metric_gap(current, target, hib)
        if g["met"]:
            checks_met += 1
        else:
            gaps.append({"metric": key, **g})
            focus.append(f"close gap on {key}")

    # Maturity tier target
    if obj.get("target_maturity_tier"):
        checks_total += 1
        mat = _safe(
            lambda: __import__(
                "runtime.tier3_maturity", fromlist=["compute_system_maturity"]
            ).compute_system_maturity(),
            default={},
        )
        cur_tier = mat.get("maturity_tier", "Emerging")
        tgt_tier = obj["target_maturity_tier"]
        cur_ord = _MATURITY_ORDER.get(cur_tier, 0)
        tgt_ord = _MATURITY_ORDER.get(tgt_tier, 0)
        if cur_ord >= tgt_ord:
            checks_met += 1
        else:
            gaps.append({"metric": "maturity_tier", "current": cur_tier,
                         "target": tgt_tier, "met": False})
            focus.append(f"advance maturity from {cur_tier} to {tgt_tier}")

    # Risk tier target
    if obj.get("target_risk_tier"):
        checks_total += 1
        risk = _safe(
            lambda: __import__(
                "runtime.tier3_risk", fromlist=["compute_system_risk"]
            ).compute_system_risk(),
            default={},
        )
        cur_risk = risk.get("risk_tier", "critical")
        tgt_risk = obj["target_risk_tier"]
        cur_ord = _RISK_ORDER.get(cur_risk, 3)
        tgt_ord = _RISK_ORDER.get(tgt_risk, 0)
        if cur_ord <= tgt_ord:
            checks_met += 1
        else:
            gaps.append({"metric": "risk_tier", "current": cur_risk,
                         "target": tgt_risk, "met": False})
            focus.append(f"reduce risk from {cur_risk} to {tgt_risk}")

    # SLA pass rate target
    if obj.get("target_sla_pass_rate") is not None:
        checks_total += 1
        sla = _safe(
            lambda: __import__(
                "runtime.tier3_sla", fromlist=["evaluate_system_sla"]
            ).evaluate_system_sla(),
            default={},
        )
        sla_passed = 100.0 if sla.get("passed") else 0.0
        target_rate = obj["target_sla_pass_rate"]
        if sla_passed >= target_rate:
            checks_met += 1
        else:
            gaps.append({"metric": "sla_pass_rate", "current": sla_passed,
                         "target": target_rate, "met": False})
            focus.append("improve SLA compliance")

    score = round(checks_met / max(checks_total, 1) * 100, 1)

    result = {
        "scope": "system",
        "objective_id": objective_id,
        "objective_name": obj["name"],
        "alignment_score": score,
        "checks_met": checks_met,
        "checks_total": checks_total,
        "blocking_gaps": gaps,
        "warnings": warnings,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _ALIGNMENT_LOG.append({
        "type": "system", "objective_id": objective_id,
        "score": score, "timestamp": result["timestamp"],
    })
    _add_insight(
        "alignment_report",
        f"system alignment to '{obj['name']}': {score}/100 "
        f"({checks_met}/{checks_total} met)",
        {"scope": "system", "objective_id": objective_id, "score": score},
        [objective_id],
    )

    return result


# ------------------------------------------------------------------
# Environment alignment
# ------------------------------------------------------------------

def evaluate_environment_alignment(
    env_id: str, objective_id: str,
) -> Dict[str, Any]:
    """Score environment alignment against an objective."""
    obj = _get_objective(objective_id)
    if obj is None:
        return {"error": True, "reason": f"objective '{objective_id}' not found"}

    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_r = compute_environment_kpis(env_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        env_name = kpi_r.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    gaps: List[Dict[str, Any]] = []
    warnings: List[str] = []
    focus: List[str] = []
    checks_met = 0
    checks_total = 0

    for key, target in obj.get("target_metrics", {}).items():
        checks_total += 1
        current = kpis.get(key)
        if current is None or not isinstance(current, (int, float)):
            warnings.append(f"metric '{key}' not numeric/available for env")
            continue
        higher = key in ("drift_stability_index", "policy_coverage",
                         "applied_packs", "promotion_readiness")
        g = _metric_gap(current, target, higher)
        if g["met"]:
            checks_met += 1
        else:
            gaps.append({"metric": key, **g})
            focus.append(f"close gap on {key}")

    if obj.get("target_maturity_tier"):
        checks_total += 1
        mat = _safe(
            lambda: __import__(
                "runtime.tier3_maturity", fromlist=["compute_environment_maturity"]
            ).compute_environment_maturity(env_id),
            default={},
        )
        cur_tier = mat.get("maturity_tier", "Emerging")
        tgt_tier = obj["target_maturity_tier"]
        if _MATURITY_ORDER.get(cur_tier, 0) >= _MATURITY_ORDER.get(tgt_tier, 0):
            checks_met += 1
        else:
            gaps.append({"metric": "maturity_tier", "current": cur_tier,
                         "target": tgt_tier, "met": False})
            focus.append(f"advance maturity to {tgt_tier}")

    if obj.get("target_risk_tier"):
        checks_total += 1
        risk = _safe(
            lambda: __import__(
                "runtime.tier3_risk", fromlist=["compute_environment_risk"]
            ).compute_environment_risk(env_id),
            default={},
        )
        cur_risk = risk.get("risk_tier", "critical")
        tgt_risk = obj["target_risk_tier"]
        if _RISK_ORDER.get(cur_risk, 3) <= _RISK_ORDER.get(tgt_risk, 0):
            checks_met += 1
        else:
            gaps.append({"metric": "risk_tier", "current": cur_risk,
                         "target": tgt_risk, "met": False})
            focus.append(f"reduce risk to {tgt_risk}")

    score = round(checks_met / max(checks_total, 1) * 100, 1)

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "objective_id": objective_id,
        "objective_name": obj["name"],
        "alignment_score": score,
        "checks_met": checks_met,
        "checks_total": checks_total,
        "blocking_gaps": gaps,
        "warnings": warnings,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _ALIGNMENT_LOG.append({
        "type": "environment", "env_id": env_id,
        "objective_id": objective_id, "score": score,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "alignment_report",
        f"env '{env_name}' alignment to '{obj['name']}': {score}/100",
        {"scope": "environment", "env_id": env_id,
         "objective_id": objective_id, "score": score},
        [env_id, objective_id],
    )

    return result


# ------------------------------------------------------------------
# Policy alignment
# ------------------------------------------------------------------

def evaluate_policy_alignment(
    policy_id: str, objective_id: str,
) -> Dict[str, Any]:
    """Score policy alignment against an objective."""
    obj = _get_objective(objective_id)
    if obj is None:
        return {"error": True, "reason": f"objective '{objective_id}' not found"}

    try:
        from runtime.tier3_kpis import compute_policy_kpis
        kpi_r = compute_policy_kpis(policy_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        pol_name = kpi_r.get("policy_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute policy KPIs"}

    gaps: List[Dict[str, Any]] = []
    warnings: List[str] = []
    focus: List[str] = []
    checks_met = 0
    checks_total = 0

    for key, target in obj.get("target_metrics", {}).items():
        checks_total += 1
        current = kpis.get(key)
        if current is None or not isinstance(current, (int, float)):
            warnings.append(f"metric '{key}' not numeric/available for policy")
            continue
        higher = key in ("completeness_score", "environment_presence",
                         "lineage_records")
        g = _metric_gap(current, target, higher)
        if g["met"]:
            checks_met += 1
        else:
            gaps.append({"metric": key, **g})
            focus.append(f"close gap on {key}")

    if obj.get("target_maturity_tier"):
        checks_total += 1
        mat = _safe(
            lambda: __import__(
                "runtime.tier3_maturity", fromlist=["compute_policy_maturity"]
            ).compute_policy_maturity(policy_id),
            default={},
        )
        cur_tier = mat.get("maturity_tier", "Emerging")
        tgt_tier = obj["target_maturity_tier"]
        if _MATURITY_ORDER.get(cur_tier, 0) >= _MATURITY_ORDER.get(tgt_tier, 0):
            checks_met += 1
        else:
            gaps.append({"metric": "maturity_tier", "current": cur_tier,
                         "target": tgt_tier, "met": False})
            focus.append(f"advance maturity to {tgt_tier}")

    score = round(checks_met / max(checks_total, 1) * 100, 1)

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "objective_id": objective_id,
        "objective_name": obj["name"],
        "alignment_score": score,
        "checks_met": checks_met,
        "checks_total": checks_total,
        "blocking_gaps": gaps,
        "warnings": warnings,
        "recommended_focus": focus,
        "timestamp": time.time(),
    }

    _ALIGNMENT_LOG.append({
        "type": "policy", "policy_id": policy_id,
        "objective_id": objective_id, "score": score,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "alignment_report",
        f"policy '{pol_name}' alignment to '{obj['name']}': {score}/100",
        {"scope": "policy", "policy_id": policy_id,
         "objective_id": objective_id, "score": score},
        [policy_id, objective_id],
    )

    return result
