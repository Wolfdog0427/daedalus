# runtime/readiness_score.py

from __future__ import annotations
from typing import Dict, Any

from runtime.state_sources import fetch_state
from runtime.startup_diagnostics import run_startup_diagnostics


def compute_readiness_score() -> Dict[str, Any]:
    """
    Compute a single readiness score between 0.0 and 1.0.
    """

    state = fetch_state()
    diag = run_startup_diagnostics()

    drift = state.get("drift", {})
    stability = state.get("stability", {})
    diagnostics = state.get("diagnostics", {})
    patch_history = state.get("patch_history", {})

    # -----------------------------
    # Drift score (0–1)
    # -----------------------------
    drift_level = drift.get("level", "none")
    drift_map = {
        "none": 1.0,
        "low": 0.85,
        "medium": 0.55,
        "high": 0.25,
    }
    drift_score = drift_map.get(drift_level, 0.5)

    # -----------------------------
    # Stability score (0–1)
    # -----------------------------
    stability_risk = stability.get("risk", "medium")
    stability_map = {
        "low": 1.0,
        "medium": 0.7,
        "high": 0.3,
    }
    stability_score = stability_map.get(stability_risk, 0.5)

    # -----------------------------
    # Diagnostics readiness (0–1)
    # -----------------------------
    readiness_avg = diagnostics.get("readiness", {}).get("average", 0.0) or 0.0
    summary = diagnostics.get("summary", {})
    blocked = summary.get("blocked_actions", 0)
    verif_fail = summary.get("verification_failures", 0)

    diag_penalty = 0.0
    diag_penalty += min(blocked * 0.05, 0.3)
    diag_penalty += min(verif_fail * 0.05, 0.3)

    diagnostics_score = max(0.0, readiness_avg - diag_penalty)

    # -----------------------------
    # Patch history health (0–1)
    # -----------------------------
    total = patch_history.get("total_cycles", 1)
    failed = patch_history.get("failed_patches", 0)
    reverted = patch_history.get("reverted_patches", 0)

    failure_rate = (failed + reverted) / max(total, 1)
    patch_score = max(0.0, 1.0 - failure_rate)

    # -----------------------------
    # Startup integrity (0–1)
    # -----------------------------
    startup_ok = (
        diag["state_sources_ok"]
        and diag["patch_history_integrity"]
    )
    startup_score = 1.0 if startup_ok else 0.0

    # -----------------------------
    # Weighted final score
    # -----------------------------
    final_score = (
        drift_score * 0.25 +
        stability_score * 0.25 +
        diagnostics_score * 0.25 +
        patch_score * 0.15 +
        startup_score * 0.10
    )

    return {
        "readiness_score": round(final_score, 3),
        "components": {
            "drift_score": drift_score,
            "stability_score": stability_score,
            "diagnostics_score": diagnostics_score,
            "patch_score": patch_score,
            "startup_score": startup_score,
        },
        "raw_state": state,
        "startup_diagnostics": diag,
    }
