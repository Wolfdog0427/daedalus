# analytics/stability_delta_predictor.py

"""
Predict the stability delta for a subsystem improvement action.

Uses learned history if available, otherwise returns a heuristic
estimate based on current stability score and risk level.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


import re

_SUBSYSTEM_MEMORY = os.path.join("data", "learning", "subsystems")
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _safe_name(name: str) -> str:
    return _SAFE_NAME_RE.sub("_", name)[:128]


def predict_stability_delta(
    subsystem: str,
    action_type: str,
    stability: Dict[str, Any],
) -> float:
    stability_score = stability.get("score", 0.5)
    risk = stability.get("risk", "medium")

    mem_path = os.path.join(_SUBSYSTEM_MEMORY, f"{_safe_name(subsystem)}.json")
    if os.path.exists(mem_path):
        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                mem = json.load(f)
            avg_improvement = mem.get("avg_stability_improvement", None)
            if avg_improvement is not None:
                return max(-1.0, min(1.0, float(avg_improvement)))
        except (json.JSONDecodeError, OSError, ValueError):
            pass
        except Exception:
            pass

    if stability_score < 0.3:
        return 0.08
    if stability_score < 0.6:
        return 0.05
    return 0.02
