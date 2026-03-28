# knowledge/drift_detector.py

"""
Drift Detector

Provides longitudinal analysis over Self-Healing Orchestrator (SHO) cycles.

Goals:
- Detect score and stability drift across cycles
- Classify drift severity (none / low / medium / high)
- Expose structured drift reports for SHO, dashboard, and analytics
- Stay read-only: this module never mutates snapshots, only observes them

This module operates purely on:
- decision records written by the SHO (data/cockpit/decision-*.json)
- the "best_candidate" structure inside each decision
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Tuple


DECISION_DIR = os.path.join("data", "cockpit")


# -------------------------------------------------------------------
# File loading utilities
# -------------------------------------------------------------------

def _list_decision_files() -> List[str]:
    if not os.path.exists(DECISION_DIR):
        return []
    files = [f for f in os.listdir(DECISION_DIR) if f.startswith("decision-")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(DECISION_DIR, f)), reverse=True)
    return files


def load_recent_decisions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Load up to `limit` most recent SHO decision records.

    Returns newest-first list of decision dicts.
    """
    files = _list_decision_files()
    if not files:
        return []

    decisions: List[Dict[str, Any]] = []
    for name in files[:limit]:
        path = os.path.join(DECISION_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                decisions.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            # Corrupt or partial file: skip but continue
            continue
    return decisions


def load_latest_pair() -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Load the two most recent decision records, if available.

    Returns:
        (current, previous)
    """
    decisions = load_recent_decisions(limit=2)
    if not decisions:
        return None, None
    if len(decisions) == 1:
        return decisions[0], None
    return decisions[0], decisions[1]


# -------------------------------------------------------------------
# Metric extraction
# -------------------------------------------------------------------

def _extract_metrics(decision: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Extract core numeric metrics from a decision record.

    Expected structure:
        decision["best_candidate"]["scores"]["improvement_score"]
        decision["best_candidate"]["scores"]["trust_score"]
        decision["best_candidate"]["scores"]["risk_score"]
        decision["best_candidate"]["stability"]["stability_score"]
    """
    best = decision.get("best_candidate", {}) or {}
    scores = best.get("scores", {}) or {}
    stability = best.get("stability", {}) or {}

    return {
        "improvement_score": scores.get("improvement_score"),
        "trust_score": scores.get("trust_score"),
        "risk_score": scores.get("risk_score"),
        "stability_score": stability.get("stability_score"),
    }


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


# -------------------------------------------------------------------
# Drift scoring and classification
# -------------------------------------------------------------------

def _aggregate_drift(deltas: Dict[str, Optional[float]]) -> float:
    """
    Aggregate per-metric deltas into a single drift score.

    Uses mean absolute delta over available metrics.
    """
    values = [abs(v) for v in deltas.values() if v is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _classify_drift_level(score: float) -> str:
    """
    Classify drift severity based on aggregate drift score.

    Thresholds are intentionally conservative and can be tuned later.
    """
    if score < 0.05:
        return "none"
    if score < 0.15:
        return "low"
    if score < 0.30:
        return "medium"
    return "high"


def _classify_trend(delta: Optional[float]) -> str:
    """
    Classify trend direction for a primary metric (e.g., improvement_score).
    """
    if delta is None:
        return "unknown"
    if abs(delta) < 0.01:
        return "flat"
    return "up" if delta > 0 else "down"


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def compute_drift_report(
    current_decision: Dict[str, Any],
    previous_decision: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute a structured drift report between two SHO decisions.

    Parameters
    ----------
    current_decision:
        The most recent decision record.
    previous_decision:
        The prior decision record, or None if not available.

    Returns
    -------
    dict
        {
            "drift_score": float,
            "level": "none" | "low" | "medium" | "high",
            "trend": "up" | "down" | "flat" | "unknown",
            "deltas": {
                "improvement_score": float | None,
                "trust_score": float | None,
                "risk_score": float | None,
                "stability_score": float | None,
            },
            "current_cycle_id": str | None,
            "previous_cycle_id": str | None,
        }
    """
    if previous_decision is None:
        # No prior data: no drift, but report is still structured
        metrics_current = _extract_metrics(current_decision)
        return {
            "drift_score": 0.0,
            "level": "none",
            "trend": "unknown",
            "deltas": {k: None for k in metrics_current.keys()},
            "current_cycle_id": current_decision.get("cycle_id"),
            "previous_cycle_id": None,
        }

    metrics_current = _extract_metrics(current_decision)
    metrics_prev = _extract_metrics(previous_decision)

    deltas: Dict[str, Optional[float]] = {}
    for key in metrics_current.keys():
        deltas[key] = _delta(metrics_current.get(key), metrics_prev.get(key))

    drift_score = _aggregate_drift(deltas)
    level = _classify_drift_level(drift_score)
    trend = _classify_trend(deltas.get("improvement_score"))

    return {
        "drift_score": drift_score,
        "level": level,
        "trend": trend,
        "deltas": deltas,
        "current_cycle_id": current_decision.get("cycle_id"),
        "previous_cycle_id": previous_decision.get("cycle_id"),
    }


def compute_latest_drift() -> Optional[Dict[str, Any]]:
    """
    Convenience helper: compute drift between the two most recent decisions.

    Returns
    -------
    dict | None
        Drift report, or None if there are no decisions yet.
    """
    current, previous = load_latest_pair()
    if current is None:
        return None
    return compute_drift_report(current, previous)


def summarize_drift(report: Dict[str, Any]) -> str:
    """
    Render a human-readable summary of a drift report.

    Suitable for logs, console output, or dashboard panels.
    """
    if not report:
        return "[DRIFT] No drift report available."

    drift_score = report.get("drift_score")
    level = report.get("level")
    trend = report.get("trend")
    deltas = report.get("deltas", {}) or {}

    lines = [
        "=== DRIFT ANALYSIS ===",
        f"Drift Score:      {drift_score}",
        f"Drift Level:      {level}",
        f"Trend:            {trend}",
        "",
        "Metric Deltas:",
        f"  Improvement:    {deltas.get('improvement_score')}",
        f"  Trust:          {deltas.get('trust_score')}",
        f"  Risk:           {deltas.get('risk_score')}",
        f"  Stability:      {deltas.get('stability_score')}",
        "",
        f"Current Cycle:    {report.get('current_cycle_id')}",
        f"Previous Cycle:   {report.get('previous_cycle_id')}",
        "",
    ]
    return "\n".join(lines)


# Historical API name (orchestrator / scheduler SHO cycle callers)
compute_drift = compute_latest_drift
