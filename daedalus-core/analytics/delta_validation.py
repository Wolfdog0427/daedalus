# analytics/delta_validation.py

from __future__ import annotations

import os
import json
from typing import Any, Dict, List
from datetime import datetime


DELTA_LOG_PATH = os.path.join("data", "learning", "delta_validation.jsonl")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def record_delta_outcome(
    cycle_id: str,
    proposal_id: str,
    plan: Dict[str, Any],
    pre_metrics: Dict[str, Any],
    post_metrics: Dict[str, Any],
) -> None:
    """
    Record how accurate predicted deltas were vs actual.

    pre_metrics / post_metrics example shape:
    {
        "drift_score": float,
        "stability_score": float,
        "risk_by_subsystem": { name: "low|medium|high", ... }
    }
    """
    predicted_actions: List[Dict[str, Any]] = plan.get("planned_actions", [])

    pre_drift = pre_metrics.get("drift_score")
    post_drift = post_metrics.get("drift_score")
    pre_stab = pre_metrics.get("stability_score")
    post_stab = post_metrics.get("stability_score")

    if pre_drift is None or post_drift is None or pre_stab is None or post_stab is None:
        return

    actual_drift_delta = post_drift - pre_drift
    actual_stability_delta = post_stab - pre_stab

    risk_before = pre_metrics.get("risk_by_subsystem", {})
    risk_after = post_metrics.get("risk_by_subsystem", {})

    records: List[Dict[str, Any]] = []

    for action in predicted_actions:
        target = action.get("target")
        if not target:
            continue

        predicted_drift = action.get("predicted_drift_delta")
        predicted_stab = action.get("predicted_stability_delta")
        predicted_risk = action.get("predicted_risk_delta")

        before_risk = risk_before.get(target)
        after_risk = risk_after.get(target)

        records.append(
            {
                "timestamp": _now_iso(),
                "cycle_id": cycle_id,
                "proposal_id": proposal_id,
                "target": target,
                "action_type": action.get("type"),
                "tier": action.get("tier"),
                "predicted_drift_delta": predicted_drift,
                "predicted_stability_delta": predicted_stab,
                "predicted_risk_delta": predicted_risk,
                "actual_drift_delta": actual_drift_delta,
                "actual_stability_delta": actual_stability_delta,
                "risk_before": before_risk,
                "risk_after": after_risk,
            }
        )

    if not records:
        return

    _ensure_dir(os.path.dirname(DELTA_LOG_PATH))
    with open(DELTA_LOG_PATH, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
