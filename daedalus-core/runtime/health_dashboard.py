# runtime/health_dashboard.py

from __future__ import annotations
import threading
from typing import Any, Dict, List, Optional

from runtime.state_sources import fetch_state

_dash_lock = threading.Lock()
_last_watch_anomaly_lines: List[str] = []
_last_doctor_report_lines: List[str] = []
_last_self_test_report: Optional[Any] = None


def update_last_watch_anomalies(lines: List[str]) -> None:
    """Persist latest watch-monitor anomaly lines for dashboard / health views."""
    global _last_watch_anomaly_lines
    with _dash_lock:
        _last_watch_anomaly_lines = list(lines)


def update_last_doctor_report(lines: List[str]) -> None:
    """Persist latest system-doctor log lines for dashboard / health views."""
    global _last_doctor_report_lines
    with _dash_lock:
        _last_doctor_report_lines = list(lines)


def update_last_self_test(report: Any) -> None:
    """Persist latest background self-test result for dashboard / health views."""
    global _last_self_test_report
    with _dash_lock:
        _last_self_test_report = report


def get_health_summary() -> Dict[str, Any]:
    """Compatibility alias for :func:`summarize_health`."""
    return summarize_health()


def get_system_health() -> str:
    """Compatibility alias for :func:`render_health_dashboard`."""
    return render_health_dashboard()


def render_health_dashboard() -> str:
    """Return a multi-line health summary for REPL / context commands."""
    summary = summarize_health()
    lines = [
        "=== SYSTEM HEALTH SUMMARY ===",
        "",
        f"Drift:       score={summary['drift']['score']}, "
        f"level={summary['drift']['level']}, "
        f"trend={summary['drift']['trend']}",
        f"Stability:   score={summary['stability']['score']}, "
        f"risk={summary['stability']['risk']}",
        "",
        f"Readiness:   avg={summary['readiness']['average']}, "
        f"blocked={summary['readiness']['blocked_actions']}, "
        f"verification_failures={summary['readiness']['verification_failures']}",
        "",
        f"Warnings:    {summary['warnings']['drift_warnings']}",
        "",
        "Patch History:",
        f"  total_cycles:       {summary['patch_history']['total_cycles']}",
        f"  successful_patches: {summary['patch_history']['successful_patches']}",
        f"  failed_patches:     {summary['patch_history']['failed_patches']}",
        f"  reverted_patches:   {summary['patch_history']['reverted_patches']}",
        "",
    ]
    return "\n".join(lines)


def summarize_health() -> Dict[str, Any]:
    """
    Return a compact, human-readable health summary.
    """

    state = fetch_state()

    drift = state["drift"]
    stability = state["stability"]
    diagnostics = state["diagnostics"]
    patch_history = state["patch_history"]

    readiness_data = diagnostics.get("readiness", {}) if isinstance(diagnostics, dict) else {}
    summary_data = diagnostics.get("summary", {}) if isinstance(diagnostics, dict) else {}
    readiness_avg = readiness_data.get("average", 0.0)
    blocked = summary_data.get("blocked_actions", 0)
    verif_fail = summary_data.get("verification_failures", 0)
    drift_warnings = diagnostics.get("drift_warnings", []) if isinstance(diagnostics, dict) else []

    return {
        "drift": {
            "score": drift.get("drift_score"),
            "level": drift.get("level"),
            "trend": drift.get("trend"),
        },
        "stability": {
            "score": stability.get("score"),
            "risk": stability.get("risk"),
        },
        "readiness": {
            "average": readiness_avg,
            "blocked_actions": blocked,
            "verification_failures": verif_fail,
        },
        "warnings": {
            "drift_warnings": drift_warnings,
        },
        "patch_history": {
            "total_cycles": patch_history.get("total_cycles"),
            "successful_patches": patch_history.get("successful_patches"),
            "failed_patches": patch_history.get("failed_patches"),
            "reverted_patches": patch_history.get("reverted_patches"),
        },
    }


def print_health_summary() -> None:
    """
    Pretty-print the health summary for console / logs.
    """
    summary = summarize_health()

    lines = [
        "=== SYSTEM HEALTH SUMMARY ===",
        "",
        f"Drift:       score={summary['drift']['score']}, "
        f"level={summary['drift']['level']}, "
        f"trend={summary['drift']['trend']}",
        f"Stability:   score={summary['stability']['score']}, "
        f"risk={summary['stability']['risk']}",
        "",
        f"Readiness:   avg={summary['readiness']['average']}, "
        f"blocked={summary['readiness']['blocked_actions']}, "
        f"verification_failures={summary['readiness']['verification_failures']}",
        "",
        f"Warnings:    {summary['warnings']['drift_warnings']}",
        "",
        "Patch History:",
        f"  total_cycles:       {summary['patch_history']['total_cycles']}",
        f"  successful_patches: {summary['patch_history']['successful_patches']}",
        f"  failed_patches:     {summary['patch_history']['failed_patches']}",
        f"  reverted_patches:   {summary['patch_history']['reverted_patches']}",
        "",
    ]

    print("\n".join(lines))
