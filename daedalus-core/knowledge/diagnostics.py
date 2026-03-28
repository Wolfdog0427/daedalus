# knowledge/diagnostics.py

"""
Diagnostics Engine

Analyzes:
- audit logs
- repeated blocked actions
- subsystem drift
- autonomy mode changes
- readiness trends
- maintenance effectiveness
- concept evolution patterns
- verification outcomes

Produces:
- summaries
- warnings
- anomaly detection
- trend analysis

This module NEVER performs actions.
It only observes and reports.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
from statistics import mean

from knowledge.audit_log import read_audit_log


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def _filter_events(events: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("event_type") == event_type]


def _extract_readiness_trend(events: List[Dict[str, Any]]) -> List[float]:
    trend = []
    for e in events:
        payload = e.get("payload", {})
        readiness = payload.get("readiness", {})
        score = readiness.get("readiness_score")
        if isinstance(score, (int, float)):
            trend.append(score)
    return trend


def _extract_blocked_actions(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocked = []
    for e in events:
        if e.get("event_type") == "governed_action":
            payload = e.get("payload", {})
            if payload.get("allowed") is False:
                blocked.append(e)
    return blocked


def _extract_autonomy_changes(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _filter_events(events, "autonomy_change")


def _extract_scheduler_runs(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _filter_events(events, "scheduler_run")


def _extract_verification_failures(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    for e in events:
        if e.get("event_type") == "verification":
            result = e.get("payload", {}).get("result", {})
            if result.get("action") == "rejected" or result.get("status") == "failed":
                failures.append(e)
    return failures


# ------------------------------------------------------------
# DIAGNOSTIC ANALYSIS
# ------------------------------------------------------------

def analyze_audit_log(limit: int = 5000) -> Dict[str, Any]:
    """
    Performs a full diagnostic analysis of the audit log.
    """
    events = read_audit_log(limit=limit)

    blocked = _extract_blocked_actions(events)
    autonomy_changes = _extract_autonomy_changes(events)
    scheduler_runs = _extract_scheduler_runs(events)
    verification_failures = _extract_verification_failures(events)
    readiness_trend = _extract_readiness_trend(events)

    # Trend metrics
    readiness_avg = mean(readiness_trend) if readiness_trend else None
    readiness_recent = readiness_trend[-5:] if len(readiness_trend) >= 5 else readiness_trend

    # Subsystem drift detection
    drift_warnings = []
    if readiness_avg is not None and readiness_avg < 0.4:
        drift_warnings.append("Overall readiness is trending low.")
    if len(blocked) > 50:
        drift_warnings.append("High number of blocked actions — autonomy may be too restrictive or system unstable.")
    if verification_failures and len(verification_failures) > 20:
        drift_warnings.append("Frequent verification failures — knowledge quality may be degrading.")

    try:
        from governor.singleton import governor as _governor
        autonomy_state = _governor.get_state()
    except Exception:
        autonomy_state = "unavailable"

    try:
        from knowledge.self_model import summarize_self_model
        self_model = summarize_self_model()
    except Exception:
        self_model = "unavailable"

    return {
        "summary": {
            "total_events_analyzed": len(events),
            "blocked_actions": len(blocked),
            "autonomy_changes": len(autonomy_changes),
            "scheduler_runs": len(scheduler_runs),
            "verification_failures": len(verification_failures),
        },
        "readiness": {
            "trend": readiness_trend,
            "average": readiness_avg,
            "recent": readiness_recent,
        },
        "blocked_actions": blocked[-20:],
        "autonomy_changes": autonomy_changes[-10:],
        "scheduler_runs": scheduler_runs[-10:],
        "verification_failures": verification_failures[-20:],
        "drift_warnings": drift_warnings,
        "current_autonomy_state": autonomy_state,
        "current_self_model": self_model,
    }


# ------------------------------------------------------------
# HIGH-LEVEL DIAGNOSTIC SUMMARY
# ------------------------------------------------------------

def diagnostic_summary() -> Dict[str, Any]:
    """
    Returns a human-readable diagnostic summary.
    """
    analysis = analyze_audit_log(limit=2000)

    return {
        "health": {
            "readiness_avg": analysis["readiness"]["average"],
            "blocked_actions": analysis["summary"]["blocked_actions"],
            "verification_failures": analysis["summary"]["verification_failures"],
            "drift_warnings": analysis["drift_warnings"],
        },
        "autonomy": analysis["current_autonomy_state"],
        "self_model": analysis["current_self_model"],
    }


# Historical API name (orchestrator / SHO cycle callers)
compute_diagnostics = analyze_audit_log
