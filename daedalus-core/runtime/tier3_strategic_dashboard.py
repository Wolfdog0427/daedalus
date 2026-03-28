# runtime/tier3_strategic_dashboard.py
"""
Strategic dashboard aggregator.

Builds a unified, read-only dashboard object that combines KPIs,
scorecards, strategic plans, forecasts, anomalies, health scores,
readiness scores, and lineage summaries into a single structure
suitable for cockpit display.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_STRATEGIC_DASH_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 200


def get_strategic_dashboard_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_STRATEGIC_DASH_LOG[-limit:])


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


def build_strategic_dashboard() -> Dict[str, Any]:
    """Aggregate all strategic signals into a single dashboard object."""
    ts = time.time()
    dash: Dict[str, Any] = {"timestamp": ts}

    # System KPIs
    dash["system_kpis"] = _safe(
        lambda: __import__(
            "runtime.tier3_kpis", fromlist=["compute_system_kpis"]
        ).compute_system_kpis(),
        default={},
    )

    # System scorecard
    dash["system_scorecard"] = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["generate_system_scorecard"]
        ).generate_system_scorecard(),
        default={},
    )

    # Recent plans
    dash["recent_plans"] = _safe(
        lambda: __import__(
            "runtime.tier3_planning", fromlist=["get_plan_registry"]
        ).get_plan_registry(5),
        default=[],
    )

    # Recent forecasts
    dash["recent_forecasts"] = _safe(
        lambda: __import__(
            "runtime.tier3_forecast", fromlist=["get_forecast_log"]
        ).get_forecast_log(5),
        default=[],
    )

    # Recent anomalies
    dash["recent_anomalies"] = _safe(
        lambda: __import__(
            "runtime.tier3_anomaly", fromlist=["get_anomaly_registry"]
        ).get_anomaly_registry(5),
        default=[],
    )

    # Environment health summary
    health_entries = _safe(
        lambda: __import__(
            "runtime.tier3_env_health", fromlist=["get_health_log"]
        ).get_health_log(10),
        default=[],
    )
    dash["recent_health"] = health_entries

    # Readiness summary
    readiness_entries = _safe(
        lambda: __import__(
            "runtime.tier3_env_health", fromlist=["get_readiness_log"]
        ).get_readiness_log(5),
        default=[],
    )
    dash["recent_readiness"] = readiness_entries

    # Lineage summary
    lineage = _safe(
        lambda: __import__(
            "runtime.tier3_lineage", fromlist=["get_lineage_log"]
        ).get_lineage_log(10),
        default=[],
    )
    dash["recent_lineage"] = lineage

    # Recent scorecards
    dash["recent_scorecards"] = _safe(
        lambda: __import__(
            "runtime.tier3_scorecards", fromlist=["get_scorecard_log"]
        ).get_scorecard_log(5),
        default=[],
    )

    scorecard = dash.get("system_scorecard") or {}
    grade = scorecard.get("grade", "?")
    score = scorecard.get("score", "?")

    _STRATEGIC_DASH_LOG.append({
        "grade": grade, "score": score, "timestamp": ts,
    })
    if len(_STRATEGIC_DASH_LOG) > _MAX_LOG:
        _STRATEGIC_DASH_LOG[:] = _STRATEGIC_DASH_LOG[-_MAX_LOG:]
    _add_insight(
        "strategic_dashboard",
        f"strategic dashboard built: system grade={grade} ({score}/100)",
        {"grade": grade, "score": score},
    )

    return dash
