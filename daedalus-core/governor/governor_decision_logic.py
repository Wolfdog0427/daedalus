# governor/governor_decision_logic.py

from __future__ import annotations
from typing import Dict, Any, Literal, Optional

from governor.singleton import governor
from governor.governor_trace import record_governor_event


DriftLevel = Literal["low", "medium", "high"]
StabilityLevel = Literal["low", "medium", "high"]


# ------------------------------------------------------------
# Helpers: normalize and compare levels
# ------------------------------------------------------------

_LEVEL_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


def _normalize_level(value: Any, default: str = "medium") -> str:
    if isinstance(value, str) and value in _LEVEL_ORDER:
        return value
    return default


def _level_ge(a: str, b: str) -> bool:
    return _LEVEL_ORDER[_normalize_level(a)] >= _LEVEL_ORDER[_normalize_level(b)]


def _level_le(a: str, b: str) -> bool:
    return _LEVEL_ORDER[_normalize_level(a)] <= _LEVEL_ORDER[_normalize_level(b)]


# ------------------------------------------------------------
# Core evaluation (PURE — no governor mutation)
# ------------------------------------------------------------

def evaluate_signals(
    drift: Dict[str, Any],
    stability: Dict[str, Any],
    readiness: float,
) -> Dict[str, Any]:
    """
    Pure decision logic.

    Returns a structured decision payload WITHOUT mutating the governor.
    The caller (governor_sho_bridge) applies the decision.
    """

    drift_level = _normalize_level(drift.get("level", "medium"))
    stability_level = _normalize_level(stability.get("level", "medium"))

    gov_state = governor.get_state()
    thresholds = gov_state["thresholds"]
    current_tier = gov_state["tier"]
    strict_mode = gov_state["strict_mode"]

    decision: Literal["escalate", "deescalate", "hold"] = "hold"
    reason: Optional[str] = None

    # --------------------------------------------------------
    # Readiness gating
    # --------------------------------------------------------
    readiness_min_for_escalation = thresholds["readiness_min_for_escalation"]
    readiness_min_for_autonomous = thresholds["readiness_min_for_autonomous"]

    readiness_block_escalation = readiness < readiness_min_for_escalation
    readiness_block_tier3 = readiness < readiness_min_for_autonomous

    # --------------------------------------------------------
    # Drift / Stability based decision
    # --------------------------------------------------------
    drift_escalate_th = thresholds["drift_threshold_escalate"]
    drift_deescalate_th = thresholds["drift_threshold_deescalate"]

    stability_escalate_th = thresholds["stability_threshold_escalate"]
    stability_deescalate_th = thresholds["stability_threshold_deescalate"]

    drift_wants_escalate = _level_ge(drift_level, drift_escalate_th)
    stability_wants_escalate = _level_le(stability_level, stability_escalate_th)

    drift_wants_deescalate = _level_le(drift_level, drift_deescalate_th)
    stability_wants_deescalate = _level_ge(stability_level, stability_deescalate_th)

    # 1) Escalation path
    if drift_wants_escalate or stability_wants_escalate:
        if readiness_block_escalation:
            decision = "hold"
            reason = "escalation_blocked_by_readiness"
        else:
            target_tier = min(3, current_tier + 1)

            if target_tier == 3 and readiness_block_tier3:
                decision = "hold"
                reason = "tier3_blocked_by_readiness"
            elif strict_mode and current_tier >= 3:
                decision = "hold"
                reason = "strict_mode_max_tier"
            else:
                decision = "escalate"
                reason = "signals_request_escalation"

    # 2) Deescalation path
    elif drift_wants_deescalate and stability_wants_deescalate:
        if strict_mode and current_tier <= 1:
            decision = "hold"
            reason = "strict_mode_min_tier"
        else:
            decision = "deescalate"
            reason = "signals_request_deescalation"

    # 3) Hold
    else:
        decision = "hold"
        reason = "no_strong_signal_for_change"

    # --------------------------------------------------------
    # Predict tier_after (pure)
    # --------------------------------------------------------
    old_tier = current_tier

    if decision == "escalate":
        new_tier = min(3, current_tier + 1)
    elif decision == "deescalate":
        new_tier = max(1, current_tier - 1)
    else:
        new_tier = current_tier

    # --------------------------------------------------------
    # Trace logging
    # --------------------------------------------------------
    record_governor_event("evaluate_signals", {
        "decision": decision,
        "reason": reason,
        "strict_mode": strict_mode,
        "tier_before": old_tier,
        "tier_after": new_tier,
        "signals": {
            "drift": drift,
            "stability": stability,
            "readiness": readiness,
        },
        "thresholds": thresholds,
        "readiness_block_escalation": readiness_block_escalation,
        "readiness_block_tier3": readiness_block_tier3,
        "drift_wants_escalate": drift_wants_escalate,
        "stability_wants_escalate": stability_wants_escalate,
        "drift_wants_deescalate": drift_wants_deescalate,
        "stability_wants_deescalate": stability_wants_deescalate,
    })

    # --------------------------------------------------------
    # Return structured result (pure)
    # --------------------------------------------------------
    return {
        "decision": decision,
        "reason": reason,
        "tier_before": old_tier,
        "tier_after": new_tier,
        "strict_mode": strict_mode,
        "signals": {
            "drift": drift,
            "stability": stability,
            "readiness": readiness,
        },
        "thresholds": thresholds,
    }
