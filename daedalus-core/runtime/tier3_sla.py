# runtime/tier3_sla.py
"""
Governance SLA evaluators.

Measures governance health against configurable thresholds and
produces structured pass/fail reports at system, environment,
and policy levels.  All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_SLA_LOG: List[Dict[str, Any]] = []

# Configurable thresholds (read at evaluation time, never auto-enforced)
_SYSTEM_THRESHOLDS: Dict[str, float] = {
    "drift_stability_min": 70.0,
    "anomaly_rate_max": 30.0,
    "readiness_floor": 40.0,
    "policy_completeness_min": 50.0,
    "pack_consistency_min": 80.0,
    "lineage_volatility_max": 5.0,
}

_ENV_THRESHOLDS: Dict[str, Any] = {
    "drift_stability_min": 70.0,
    "health_grade_acceptable": {"healthy", "minor_issues"},
    "policy_coverage_min": 1,
}

_POLICY_THRESHOLDS: Dict[str, float] = {
    "completeness_min": 50.0,
    "environment_presence_min": 1,
}


def get_sla_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_SLA_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def _check(name: str, value: Any, op: str, threshold: Any) -> Dict[str, Any]:
    """Compare a metric against a threshold and return a structured check."""
    if op == ">=":
        passed = value >= threshold
    elif op == "<=":
        passed = value <= threshold
    elif op == "in":
        passed = value in threshold
    else:
        passed = False
    return {
        "metric": name,
        "value": value,
        "op": op,
        "threshold": threshold if not isinstance(threshold, set) else sorted(threshold),
        "passed": passed,
    }


# ------------------------------------------------------------------
# System SLA
# ------------------------------------------------------------------

def evaluate_system_sla() -> Dict[str, Any]:
    """Evaluate governance SLAs across the entire system."""
    try:
        from runtime.tier3_kpis import compute_system_kpis
        kpi_r = compute_system_kpis()
        kpis = kpi_r.get("kpis", {})
    except Exception:
        kpis = {}

    t = _SYSTEM_THRESHOLDS
    checks = [
        _check("drift_stability_index",
               kpis.get("drift_stability_index", 0), ">=", t["drift_stability_min"]),
        _check("anomaly_rate",
               kpis.get("anomaly_rate", 0), "<=", t["anomaly_rate_max"]),
        _check("readiness_trend_score",
               kpis.get("readiness_trend_score", 0), ">=", t["readiness_floor"]),
        _check("policy_lifecycle_health",
               kpis.get("policy_lifecycle_health", 0), ">=", t["policy_completeness_min"]),
        _check("pack_consistency_score",
               kpis.get("pack_consistency_score", 0), ">=", t["pack_consistency_min"]),
        _check("lineage_volatility",
               kpis.get("lineage_volatility", 0), "<=", t["lineage_volatility_max"]),
    ]

    failures = [c for c in checks if not c["passed"]]
    warnings = [c["metric"] for c in failures]
    overall = len(failures) == 0

    result = {
        "scope": "system",
        "passed": overall,
        "checks": checks,
        "failures": len(failures),
        "warnings": warnings,
        "timestamp": time.time(),
    }

    _SLA_LOG.append({
        "type": "system", "passed": overall,
        "failures": len(failures), "timestamp": result["timestamp"],
    })
    _add_insight(
        "sla_report",
        f"system SLA: {'PASS' if overall else 'FAIL'} "
        f"({len(failures)} failure(s))",
        {"scope": "system", "passed": overall, "failures": len(failures)},
    )

    return result


# ------------------------------------------------------------------
# Environment SLA
# ------------------------------------------------------------------

def evaluate_environment_sla(env_id: str) -> Dict[str, Any]:
    """Evaluate SLAs for a single environment."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_r = compute_environment_kpis(env_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        env_name = kpi_r.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    t = _ENV_THRESHOLDS
    checks = [
        _check("drift_stability_index",
               kpis.get("drift_stability_index", 0), ">=", t["drift_stability_min"]),
        _check("health_grade",
               kpis.get("health_grade", "unknown"), "in", t["health_grade_acceptable"]),
        _check("policy_coverage",
               kpis.get("policy_coverage", 0), ">=", t["policy_coverage_min"]),
    ]

    failures = [c for c in checks if not c["passed"]]
    warnings = [c["metric"] for c in failures]
    overall = len(failures) == 0

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env_name,
        "passed": overall,
        "checks": checks,
        "failures": len(failures),
        "warnings": warnings,
        "timestamp": time.time(),
    }

    _SLA_LOG.append({
        "type": "environment", "env_id": env_id, "passed": overall,
        "failures": len(failures), "timestamp": result["timestamp"],
    })
    _add_insight(
        "sla_report",
        f"env '{env_name}' SLA: {'PASS' if overall else 'FAIL'} "
        f"({len(failures)} failure(s))",
        {"scope": "environment", "env_id": env_id,
         "passed": overall, "failures": len(failures)},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy SLA
# ------------------------------------------------------------------

def evaluate_policy_sla(policy_id: str) -> Dict[str, Any]:
    """Evaluate SLAs for a single policy."""
    try:
        from runtime.tier3_kpis import compute_policy_kpis
        kpi_r = compute_policy_kpis(policy_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis = kpi_r.get("kpis", {})
        pol_name = kpi_r.get("policy_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute policy KPIs"}

    t = _POLICY_THRESHOLDS
    checks = [
        _check("completeness_score",
               kpis.get("completeness_score", 0), ">=", t["completeness_min"]),
        _check("environment_presence",
               kpis.get("environment_presence", 0), ">=", t["environment_presence_min"]),
    ]

    failures = [c for c in checks if not c["passed"]]
    warnings = [c["metric"] for c in failures]
    overall = len(failures) == 0

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol_name,
        "passed": overall,
        "checks": checks,
        "failures": len(failures),
        "warnings": warnings,
        "timestamp": time.time(),
    }

    _SLA_LOG.append({
        "type": "policy", "policy_id": policy_id, "passed": overall,
        "failures": len(failures), "timestamp": result["timestamp"],
    })
    _add_insight(
        "sla_report",
        f"policy '{pol_name}' SLA: {'PASS' if overall else 'FAIL'} "
        f"({len(failures)} failure(s))",
        {"scope": "policy", "policy_id": policy_id,
         "passed": overall, "failures": len(failures)},
        [policy_id],
    )

    return result
