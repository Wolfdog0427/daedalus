# analytics/risk_delta_predictor.py

"""
Predict the risk delta for a subsystem improvement action.

Uses learned history if available, otherwise returns a heuristic
estimate. Negative deltas mean risk reduction (good).
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


def predict_risk_delta(
    subsystem: str,
    action_type: str,
    current_risk: str,
) -> float:
    mem_path = os.path.join(_SUBSYSTEM_MEMORY, f"{_safe_name(subsystem)}.json")
    if os.path.exists(mem_path):
        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                mem = json.load(f)
            avg_reduction = mem.get("avg_risk_reduction", None)
            if avg_reduction is not None:
                return -abs(avg_reduction)
        except (json.JSONDecodeError, OSError, ValueError):
            pass
        except Exception:
            pass

    risk_map = {"none": 0.0, "low": -0.01, "medium": -0.03, "high": -0.06, "critical": -0.08}
    return risk_map.get(current_risk, -0.02)
