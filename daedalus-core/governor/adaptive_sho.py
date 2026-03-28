# governor/adaptive_sho.py

from __future__ import annotations

import os
import json
from typing import Any, Dict, List
from datetime import datetime, timezone

from analytics.drift_delta_predictor import predict_drift_delta
from analytics.stability_delta_predictor import predict_stability_delta
from analytics.risk_delta_predictor import predict_risk_delta
from analytics.delta_tier_selector import choose_tier_from_deltas


LEARNING_ROOT = "data/learning"
SUBSYSTEM_MEMORY = os.path.join(LEARNING_ROOT, "subsystems")
ACTION_MEMORY = os.path.join(LEARNING_ROOT, "actions")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def _clamp01(val: Any) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except (TypeError, ValueError):
        return 0.5


def _sanitize_subsystem(name: str) -> str:
    sanitized = name.replace("\x00", "")
    sanitized = sanitized.replace("..", "").replace("/", "_").replace("\\", "_")
    if not sanitized:
        raise ValueError(f"Invalid subsystem name: {name!r}")
    return sanitized


def score_subsystem(subsystem: str, diagnostics: Dict[str, Any]) -> float:
    diag_score = max(0.0, min(1.0, float(diagnostics.get("score") or 0.0)))
    subsystem = _sanitize_subsystem(subsystem)
    mem_path = os.path.join(SUBSYSTEM_MEMORY, f"{subsystem}.json")
    mem = _load(mem_path)

    success_rate = mem.get("success_rate")
    success_rate = _clamp01(success_rate if success_rate is not None else 0.5)
    avg_score = _clamp01(mem.get("avg_score") or 0.0)
    rollback_rate = _clamp01(mem.get("rollback_rate") or 0.0)

    reliability = (
        success_rate * 0.6 +
        (1 - rollback_rate) * 0.3 +
        avg_score * 0.1
    )

    final_score = diag_score * 0.7 + reliability * 0.3
    return final_score


def score_action_type(action_type: str) -> float:
    action_type = _sanitize_subsystem(action_type)
    mem_path = os.path.join(ACTION_MEMORY, f"{action_type}.json")
    mem = _load(mem_path)

    success_rate = mem.get("success_rate")
    success_rate = _clamp01(success_rate if success_rate is not None else 0.5)
    avg_score = _clamp01(mem.get("avg_score") or 0.0)
    rollback_rate = _clamp01(mem.get("rollback_rate") or 0.0)

    return (
        success_rate * 0.6 +
        (1 - rollback_rate) * 0.3 +
        avg_score * 0.1
    )


def generate_adaptive_proposal(
    cycle_id: str,
    drift: Dict[str, Any],
    diagnostics: Dict[str, Any],
    stability: Dict[str, Any],
    max_actions: int = 3,
) -> Dict[str, Any]:
    """
    Generate a multi-action proposal using:
    - learned reliability
    - diagnostics
    - predicted drift/stability/risk deltas
    - delta-driven tier selection
    """
    subsystems = diagnostics.get("subsystems", [])
    if not subsystems:
        return {
            "status": "no_subsystems",
            "message": "No subsystems available for improvement",
        }

    scored: List[tuple[str, float, Dict[str, Any]]] = []
    for s in subsystems:
        name = s.get("name") or s.get("subsystem")
        if not name:
            continue
        score = score_subsystem(name, s)
        scored.append((name, score, s))

    if not scored:
        return {
            "status": "no_subsystems",
            "message": "No valid subsystems found in diagnostics",
        }

    scored.sort(key=lambda x: x[1])  # weakest first

    action_type = "subsystem_improvement"
    action_score = score_action_type(action_type)

    weakest_name, weakest_rel, weakest_diag = scored[0]

    planned_actions: List[Dict[str, Any]] = []
    predicted_drift_delta_total = 0.0
    predicted_stability_delta_total = 0.0
    predicted_risk_delta_total = 0.0

    for name, rel_score, diag in scored[:max_actions]:
        current_risk = diag.get("risk", "medium")

        d_delta = predict_drift_delta(name, action_type, drift)
        s_delta = predict_stability_delta(name, action_type, stability)
        r_delta = predict_risk_delta(name, action_type, current_risk)

        predicted_drift_delta_total += d_delta
        predicted_stability_delta_total += s_delta
        predicted_risk_delta_total += r_delta

        planned_actions.append(
            {
                "type": action_type,
                "target": name,
                "tier": None,  # filled after tier selection
                "predicted_drift_delta": d_delta,
                "predicted_stability_delta": s_delta,
                "predicted_risk_delta": r_delta,
            }
        )

    _raw = stability.get("score")
    base_stability_score = _raw if _raw is not None else 0.5
    tier = choose_tier_from_deltas(
        base_stability_score=base_stability_score,
        predicted_stability_delta_total=predicted_stability_delta_total,
        predicted_risk_delta_total=predicted_risk_delta_total,
    )

    for action in planned_actions:
        action["tier"] = tier

    _raw = drift.get("score")
    drift_score = _raw if _raw is not None else 0.5
    confidence = max(0.0, min(1.0,
        weakest_rel * 0.4 +
        action_score * 0.25 +
        (1 - drift_score) * 0.15 +
        max(0.0, min(1.0, predicted_stability_delta_total)) * 0.2
    ))

    return {
        "status": "proposal_generated",
        "cycle_id": cycle_id,
        "tier": tier,
        "target_subsystem": weakest_name,
        "planned_actions": planned_actions,
        "confidence": confidence,
        "reliability": weakest_rel,
        "action_score": action_score,
        "predicted_drift_delta_total": predicted_drift_delta_total,
        "predicted_stability_delta_total": predicted_stability_delta_total,
        "predicted_risk_delta_total": predicted_risk_delta_total,
        "timestamp": _now_iso(),
    }
