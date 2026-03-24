# runtime/state_sources.py

from __future__ import annotations
from typing import Dict, Any

from knowledge.drift_detector import compute_latest_drift
from knowledge.dignostics import analyze_audit_log
from knowledge.system_stability import compute_system_stability
from runtime.patch_history_manager import load_patch_history


def fetch_state() -> Dict[str, Any]:
    """
    Fetch the current system state for the SHO cycle.

    Returns:
        {
            "drift": {...},
            "stability": {...},
            "diagnostics": {...},
            "patch_history": {...},
        }
    """

    # -----------------------------
    # Drift
    # -----------------------------
    drift = compute_latest_drift() or {
        "drift_score": 0.0,
        "level": "none",
        "trend": "unknown",
        "deltas": {},
    }

    # -----------------------------
    # Diagnostics
    # -----------------------------
    diagnostics = analyze_audit_log(limit=2000)

    # -----------------------------
    # Stability (derived from diagnostics)
    # -----------------------------
    stability = compute_system_stability()

    # -----------------------------
    # Patch History
    # -----------------------------
    patch_history = load_patch_history()

    return {
        "drift": drift,
        "stability": stability,
        "diagnostics": diagnostics,
        "patch_history": patch_history,
    }
