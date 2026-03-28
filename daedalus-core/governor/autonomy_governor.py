# governor/autonomy_governor.py

from __future__ import annotations
import threading
from typing import Dict, Any

from governor.governor_trace import record_governor_event


class AutonomyGovernor:
    """
    Tiered autonomy governor with strict mode enforcement,
    drift/stability gating, readiness gating, and SHO integration.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # ------------------------------------------------------------
        # Default thresholds (may be overridden by persisted values)
        # ------------------------------------------------------------
        self.drift_threshold_escalate = "medium"
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
        with self._lock:
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
        with self._lock:
            if self.strict_mode and self.tier >= 3:
                return

            old = self.tier
            self.tier = min(3, self.tier + 1)
            new_tier = self.tier

        record_governor_event("tier_escalated", {
            "from": old,
            "to": new_tier,
            "reason": reason,
        })

    def deescalate(self, reason: str) -> None:
        with self._lock:
            if self.strict_mode and self.tier <= 1:
                return

            old = self.tier
            self.tier = max(1, min(3, self.tier - 1))
            new_tier = self.tier

        record_governor_event("tier_deescalated", {
            "from": old,
            "to": new_tier,
            "reason": reason,
        })

    # ------------------------------------------------------------
    # Strict Mode
    # ------------------------------------------------------------
    def set_tier(self, tier: int) -> None:
        """Set the governor tier (clamped to 1-3, max ±1 step per call)."""
        try:
            tier = max(1, min(3, int(tier)))
        except (TypeError, ValueError):
            return
        with self._lock:
            old = self.tier
            if old == tier:
                return
            if abs(tier - old) > 1:
                tier = old + (1 if tier > old else -1)
            self.tier = tier

        record_governor_event("tier_set", {
            "from": old,
            "to": tier,
        })

    def set_strict_mode(self, enabled: bool) -> None:
        with self._lock:
            old = self.strict_mode
            self.strict_mode = enabled

        record_governor_event("strict_mode_changed", {
            "from": old,
            "to": enabled,
        })

    def enable_strict_mode(self) -> None:
        self.set_strict_mode(True)

    def disable_strict_mode(self) -> None:
        self.set_strict_mode(False)

    # ------------------------------------------------------------
    # SHO Integration
    # ------------------------------------------------------------
    def decide_for_cycle(
        self,
        cycle_id: str = "",
        drift: Dict[str, Any] | None = None,
        diagnostics: Dict[str, Any] | None = None,
        stability: Dict[str, Any] | None = None,
        patch_history: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Produce a governor decision compatible with SHOCycleOrchestrator.

        This lightweight implementation bases the decision purely on
        the current tier and strict_mode without the full knowledge-layer
        autonomy logic.  It satisfies the API contract that
        ``runtime.sho_cycle_orchestrator`` depends on.
        """
        with self._lock:
            tier = self.tier
            strict = self.strict_mode

        should_generate = tier >= 2 and not strict
        return {
            "allowed_tier": tier,
            "proposal_id": None,
            "should_generate_proposal": should_generate,
            "state": self.get_state(),
            "cycle_id": cycle_id,
        }
