# runtime/delta_ui_bridge.py

from __future__ import annotations

from typing import Any, Dict

from analytics.delta_accuracy import compute_delta_accuracy
from analytics.delta_rl import load_delta_weights


def get_delta_dashboard() -> Dict[str, Any]:
    """
    Returns a compact view of delta prediction health for UI / API.

    Shape:
    {
        "accuracy": {
            "count": int,
            "drift_mae": float | None,
            "stability_mae": float | None,
            "risk_match_rate": float | None,
        },
        "weights": {
            "drift_weight": float,
            "stability_weight": float,
            "risk_weight": float,
        }
    }
    """
    accuracy = compute_delta_accuracy()
    weights = load_delta_weights()

    return {
        "accuracy": accuracy,
        "weights": weights,
    }
