# analytics/drift_delta_predictor.py

"""
Predict the drift delta for a subsystem improvement action.

Uses learned history from data/learning/subsystems/ if available,
otherwise returns a conservative heuristic estimate based on
the current drift level and subsystem risk.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


_SUBSYSTEM_MEMORY = os.path.join("data", "learning", "subsystems")


def predict_drift_delta(
    subsystem: str,
    action_type: str,
    drift: Dict[str, Any],
) -> float:
    drift_score = drift.get("score", 0.0)
    drift_level = drift.get("level", "none")

    mem_path = os.path.join(_SUBSYSTEM_MEMORY, f"{subsystem}.json")
    if os.path.exists(mem_path):
        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                mem = json.load(f)
            avg_improvement = mem.get("avg_drift_improvement", None)
            if avg_improvement is not None:
                return -abs(avg_improvement)
        except Exception:
            pass

    level_map = {"none": 0.0, "low": -0.02, "medium": -0.05, "high": -0.08}
    return level_map.get(drift_level, -0.03)
