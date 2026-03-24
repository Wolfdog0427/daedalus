# runtime/tier3_exec_report.py
"""
Executive-grade governance report generator.

Aggregates KPIs, scorecards, SLAs, risk scores, heatmaps, strategic
plans, forecasts, anomalies, and lineage summaries into a single
structured report.  Strictly read-only and operator-triggered.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_EXEC_REPORT_LOG: List[Dict[str, Any]] = []


def get_exec_report_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_EXEC_REPORT_LOG[-limit:])


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


def generate_executive_report() -> Dict[str, Any]:
    """Build an executive-grade governance report."""
    ts = time.time()
    report: Dict[str, Any] = {"timestamp": ts}

    # KPIs
    report["system_kpis"] = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis(),
        default={},
    )

    # Scorecard
    report["system_scorecard"] = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["generate_system_scorecard"]
        ).generate_system_scorecard(),
        default={},
    )

    # SLA
    report["system_sla"] = _safe(
        lambda: __import__(
            "runtime.tier3_sla", fromlist=["evaluate_system_sla"]
        ).evaluate_system_sla(),
        default={},
    )

    # Risk
    report["system_risk"] = _safe(
        lambda: __import__(
            "runtime.tier3_risk", fromlist=["compute_system_risk"]
        ).compute_system_risk(),
        default={},
    )

    # Heatmap
    report["system_heatmap"] = _safe(
        lambda: __import__(
            "runtime.tier3_heatmap", fromlist=["generate_system_heatmap"]
        ).generate_system_heatmap(),
        default={},
    )

    # Strategic plans
    report["recent_plans"] = _safe(
        lambda: __import__(
            "runtime.tier3_planning", fromlist=["get_plan_registry"]
        ).get_plan_registry(5),
        default=[],
    )

    # Forecasts
    report["recent_forecasts"] = _safe(
        lambda: __import__(
            "runtime.tier3_forecast", fromlist=["get_forecast_log"]
        ).get_forecast_log(5),
        default=[],
    )

    # Anomalies
    report["recent_anomalies"] = _safe(
        lambda: __import__(
            "runtime.tier3_anomaly", fromlist=["get_anomaly_registry"]
        ).get_anomaly_registry(5),
        default=[],
    )

    # Lineage summary
    report["recent_lineage"] = _safe(
        lambda: __import__(
            "runtime.tier3_lineage", fromlist=["get_lineage_log"]
        ).get_lineage_log(10),
        default=[],
    )

    # Derive headline
    sc = report.get("system_scorecard") or {}
    sla = report.get("system_sla") or {}
    risk = report.get("system_risk") or {}
    grade = sc.get("grade", "?")
    sla_pass = sla.get("passed", "?")
    risk_tier = risk.get("risk_tier", "?")

    report["headline"] = {
        "grade": grade,
        "sla_status": "PASS" if sla_pass is True else "FAIL" if sla_pass is False else "?",
        "risk_tier": risk_tier,
    }

    _EXEC_REPORT_LOG.append({
        "grade": grade,
        "sla_pass": bool(sla_pass) if isinstance(sla_pass, bool) else None,
        "risk_tier": risk_tier,
        "timestamp": ts,
    })
    _add_insight(
        "executive_report",
        f"executive report: grade={grade}, SLA={'PASS' if sla_pass else 'FAIL'}, "
        f"risk={risk_tier}",
        {"grade": grade, "sla_pass": sla_pass, "risk_tier": risk_tier},
    )

    return report
