# runtime/metrics_capture.py

from __future__ import annotations

from typing import Any, Dict


def build_metrics_from_state(
    drift: Dict[str, Any],
    stability: Dict[str, Any],
    diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a compact metrics snapshot suitable for delta validation.

    Returns:
    {
        "drift_score": float,
        "stability_score": float,
        "risk_by_subsystem": { name: "low|medium|high", ... }
    }
    """
    drift_score = drift.get("score", 0.5)
    stability_score = stability.get("score", 0.5)

    risk_by_subsystem: Dict[str, Any] = {}
    for s in diagnostics.get("subsystems", []) or []:
        name = s.get("name") or s.get("subsystem")
        if not name:
            continue
        risk_by_subsystem[name] = s.get("risk", "medium")

    return {
        "drift_score": drift_score,
        "stability_score": stability_score,
        "risk_by_subsystem": risk_by_subsystem,
    }
