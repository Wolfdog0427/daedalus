# analytics/delta_rl.py

from __future__ import annotations

import os
import json
from typing import Any, Dict

from analytics.delta_accuracy import compute_delta_accuracy


WEIGHTS_PATH = os.path.join("data", "learning", "delta_weights.json")


def _default_weights() -> Dict[str, Any]:
    return {
        "drift_weight": 1.0,
        "stability_weight": 1.0,
        "risk_weight": 1.0,
    }


def load_delta_weights() -> Dict[str, Any]:
    if not os.path.exists(WEIGHTS_PATH):
        return _default_weights()
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _default_weights()
    base = _default_weights()
    base.update(data)
    return base


def save_delta_weights(weights: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2)


def update_delta_weights() -> Dict[str, Any]:
    """
    Simple RL-style adjustment:
    - If drift MAE is high → reduce drift_weight
    - If stability MAE is low → increase stability_weight
    - If risk_match_rate is high → increase risk_weight
    """
    acc = compute_delta_accuracy()
    weights = load_delta_weights()

    drift_mae = acc.get("drift_mae")
    stab_mae = acc.get("stability_mae")
    risk_match = acc.get("risk_match_rate")

    if drift_mae is not None:
        if drift_mae > 0.2:
            weights["drift_weight"] *= 0.9
        elif drift_mae < 0.05:
            weights["drift_weight"] *= 1.05

    if stab_mae is not None:
        if stab_mae < 0.05:
            weights["stability_weight"] *= 1.05
        elif stab_mae > 0.2:
            weights["stability_weight"] *= 0.9

    if risk_match is not None:
        if risk_match > 0.8:
            weights["risk_weight"] *= 1.05
        elif risk_match < 0.5:
            weights["risk_weight"] *= 0.9

    save_delta_weights(weights)
    return weights
