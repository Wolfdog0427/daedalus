# runtime/governor_sho_bridge.py

from __future__ import annotations
from typing import Dict, Any

from governor.governor_decision_logic import evaluate_signals
from governor.singleton import governor


def integrate_governor_with_cycle(cycle_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Integrate the autonomy governor into a single SHO cycle result.

    Expected cycle_result shape (minimum):
      {
        "drift": {...},
        "stability": {...},
        "readiness": float,
        ...
      }

    This function:
      - Calls governor decision logic with drift/stability/readiness
      - Applies tier changes via the governor
      - Attaches the governor decision payload to the cycle_result
      - Returns the augmented cycle_result
    """

    # Extract required signals
    drift = cycle_result.get("drift", {}) or {}
    stability = cycle_result.get("stability", {}) or {}
    readiness_raw = cycle_result.get("readiness", 0.0)
    readiness = (
        readiness_raw.get("readiness_score", 0.0)
        if isinstance(readiness_raw, dict)
        else (readiness_raw or 0.0)
    )

    # Evaluate signals through the governor
    decision_payload = evaluate_signals(
        drift=drift,
        stability=stability,
        readiness=readiness,
    )

    # Apply tier changes
    decision = decision_payload.get("decision")
    reason = decision_payload.get("reason", "no_reason_provided")

    if decision == "escalate":
        governor.escalate(reason)

    elif decision == "deescalate":
        governor.deescalate(reason)

    # Attach governor decision + state to the cycle result
    cycle_result["governor_decision"] = decision_payload
    cycle_result["governor_tier"] = governor.tier
    cycle_result["governor_strict_mode"] = governor.strict_mode

    return cycle_result
