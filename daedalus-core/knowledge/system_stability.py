# knowledge/system_stability.py

from __future__ import annotations
from typing import Dict, Any

from knowledge.diagnostics import analyze_audit_log


def compute_system_stability() -> Dict[str, Any]:
    """
    Derive system-level stability from diagnostics.

    Stability is based on:
    - readiness average
    - verification failures
    - blocked actions
    - drift warnings
    """

    diag = analyze_audit_log(limit=2000)

    readiness_avg = diag.get("readiness", {}).get("average")
    verification_failures = diag.get("summary", {}).get("verification_failures", 0)
    blocked_actions = diag.get("summary", {}).get("blocked_actions", 0)
    drift_warnings = diag.get("drift_warnings", [])

    # -----------------------------
    # Stability Score
    # -----------------------------
    if readiness_avg is None:
        stability_score = 0.5
    else:
        stability_score = float(readiness_avg)

    # -----------------------------
    # Stability Risk Classification
    # -----------------------------
    if readiness_avg is None:
        risk = "medium"
    elif readiness_avg < 0.3:
        risk = "high"
    elif readiness_avg < 0.5:
        risk = "medium"
    else:
        risk = "low"

    # Additional risk modifiers
    if verification_failures > 20:
        risk = "high"
    if blocked_actions > 50:
        risk = "high"
    if drift_warnings:
        risk = "high"

    return {
        "score": stability_score,
        "risk": risk,
        "notes": {
            "readiness_avg": readiness_avg,
            "verification_failures": verification_failures,
            "blocked_actions": blocked_actions,
            "drift_warnings": drift_warnings,
        },
    }


# Historical API name (orchestrator / scheduler SHO cycle callers)
compute_stability = compute_system_stability
