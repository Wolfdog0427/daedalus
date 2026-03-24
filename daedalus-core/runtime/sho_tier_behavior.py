# runtime/sho_tier_behavior.py

from __future__ import annotations
from typing import Dict, Any

from governor.singleton import governor


class SHOBehavior:
    """
    Tier-aware SHO behavior controller.

    SHO behavior changes based on governor tier:
      - Tier 1: Safe mode (minimal actions, conservative)
      - Tier 2: Normal mode (standard behavior)
      - Tier 3: Autonomous mode (expanded actions, only if readiness allows)

    This module does NOT compute drift/stability/readiness.
    It ONLY adjusts SHO behavior based on the governor's tier.
    """

    # ------------------------------------------------------------
    # Tier 1 — Safe Mode
    # ------------------------------------------------------------
    def _tier1_behavior(self, cycle_result: Dict[str, Any]) -> Dict[str, Any]:
        cycle_result["sho_behavior"] = {
            "mode": "tier1_safe",
            "actions": [
                "limit_autonomy",
                "suppress_exploration",
                "disable_proposal_generation",
                "disable_self_modification",
                "minimal_output",
            ],
            "strict_mode": governor.strict_mode,
            "notes": "System operating in Tier 1 safe mode.",
        }
        return cycle_result

    # ------------------------------------------------------------
    # Tier 2 — Normal Mode
    # ------------------------------------------------------------
    def _tier2_behavior(self, cycle_result: Dict[str, Any]) -> Dict[str, Any]:
        cycle_result["sho_behavior"] = {
            "mode": "tier2_normal",
            "actions": [
                "normal_processing",
                "moderate_exploration",
                "proposal_generation_allowed",
                "no_high_risk_changes",
            ],
            "strict_mode": governor.strict_mode,
            "notes": "System operating in Tier 2 normal mode.",
        }
        return cycle_result

    # ------------------------------------------------------------
    # Tier 3 — Autonomous Mode
    # ------------------------------------------------------------
    def _tier3_behavior(self, cycle_result: Dict[str, Any]) -> Dict[str, Any]:
        cycle_result["sho_behavior"] = {
            "mode": "tier3_autonomous",
            "actions": [
                "autonomous_processing",
                "full_exploration",
                "proposal_generation_allowed",
                "self_improvement_allowed",
            ],
            "strict_mode": governor.strict_mode,
            "notes": "System operating in Tier 3 autonomous mode.",
        }
        return cycle_result

    # ------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------
    def apply_tier_behavior(self, cycle_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply tier-based behavior to the SHO cycle result.

        This function is called AFTER:
          - drift/stability metrics computed
          - readiness computed
          - governor decision logic applied
        """

        tier = governor.tier

        if tier == 1:
            return self._tier1_behavior(cycle_result)

        if tier == 2:
            return self._tier2_behavior(cycle_result)

        if tier == 3:
            return self._tier3_behavior(cycle_result)

        # Fallback (should never happen)
        cycle_result["sho_behavior"] = {
            "mode": "unknown",
            "actions": [],
            "strict_mode": governor.strict_mode,
            "notes": "Unknown tier state.",
        }
        return cycle_result


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
sho_behavior = SHOBehavior()
