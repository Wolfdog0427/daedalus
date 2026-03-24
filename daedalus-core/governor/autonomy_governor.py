# governor/autonomy_governor.py

from __future__ import annotations
from typing import Dict, Any

from governor.governor_trace import record_governor_event


class AutonomyGovernor:
    """
    Tiered autonomy governor with strict mode enforcement,
    drift/stability gating, readiness gating, and SHO integration.
    """

    def __init__(self):
        # ------------------------------------------------------------
        # Default thresholds (may be overridden by persisted values)
        # ------------------------------------------------------------
        self.drift_threshold_escalate = "low"
        self.drift_threshold_deescalate = "medium"

        self.stability_threshold_escalate = "low"
        self.stability_threshold_deescalate = "high"

        self.readiness_min_for_escalation = 0.75
        self.readiness_min_for_autonomous = 0.85

        # ------------------------------------------------------------
        # Governor state
        # ------------------------------------------------------------
        self.tier = 1
        self.strict_mode = True

    # ------------------------------------------------------------
    # State Access
    # ------------------------------------------------------------
    def get_state(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "strict_mode": self.strict_mode,
            "thresholds": {
                "drift_threshold_escalate": self.drift_threshold_escalate,
                "drift_threshold_deescalate": self.drift_threshold_deescalate,
                "stability_threshold_escalate": self.stability_threshold_escalate,
                "stability_threshold_deescalate": self.stability_threshold_deescalate,
                "readiness_min_for_escalation": self.readiness_min_for_escalation,
                "readiness_min_for_autonomous": self.readiness_min_for_autonomous,
            },
        }

    # ------------------------------------------------------------
    # Tier Management
    # ------------------------------------------------------------
    def escalate(self, reason: str) -> None:
        if self.strict_mode and self.tier >= 3:
            return

        old = self.tier
        self.tier = min(3, self.tier + 1)

        record_governor_event("tier_escalated", {
            "from": old,
            "to": self.tier,
            "reason": reason,
        })

    def deescalate(self, reason: str) -> None:
        if self.strict_mode and self.tier <= 1:
            return

        old = self.tier
        self.tier = max(1, self.tier - 1)

        record_governor_event("tier_deescalated", {
            "from": old,
            "to": self.tier,
            "reason": reason,
        })

    # ------------------------------------------------------------
    # Strict Mode
    # ------------------------------------------------------------
    def set_strict_mode(self, enabled: bool) -> None:
        old = self.strict_mode
        self.strict_mode = enabled

        record_governor_event("strict_mode_changed", {
            "from": old,
            "to": enabled,
        })
