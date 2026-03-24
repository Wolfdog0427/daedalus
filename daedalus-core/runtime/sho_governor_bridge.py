# runtime/sho_governor_bridge.py

"""
SHO ↔ Autonomy Governor Integration Layer

This module connects the Self-Healing Orchestrator (SHO) with the
Autonomy Governor. It does NOT perform any self-modification.

Responsibilities:
- Run the governor each cycle
- Determine allowed tier
- Handle proposal creation
- Route patch requests to the patch_applier (stub)
- Log decisions and outcomes
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from governor.autonomy_governor import AutonomyGovernor
from knowledge.patch_applier import apply_patch_in_sandbox


class SHOGovernorBridge:
    def __init__(self):
        self.gov = AutonomyGovernor()

    def run_cycle(
        self,
        cycle_id: str,
        drift: Dict[str, Any],
        diagnostics: Dict[str, Any],
        stability: Dict[str, Any],
        patch_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Main entry point for SHO.
        Returns a dict describing:
        - allowed tier
        - proposal created (if any)
        - patch application result (if any)
        """

        decision = self.gov.decide_for_cycle(
            cycle_id=cycle_id,
            drift=drift,
            diagnostics=diagnostics,
            stability=stability,
            patch_history=patch_history,
        )

        allowed_tier = decision["allowed_tier"]
        proposal_id = decision["proposal_id"]
        should_generate = decision["should_generate_proposal"]

        patch_result = None

        # Tier 1 and Tier 2: auto-apply safe patches
        if allowed_tier in (1, 2) and not should_generate:
            # SHO would normally generate a patch here
            # For now, we call the stub patch applier
            patch_result = apply_patch_in_sandbox({
                "tier": allowed_tier,
                "cycle_id": cycle_id,
                "note": "Placeholder patch. Implement real logic later."
            })

        # Tier 3: proposal created, waiting for user approval
        if allowed_tier == 3 and should_generate:
            patch_result = {
                "status": "awaiting_approval",
                "proposal_id": proposal_id,
            }

        return {
            "allowed_tier": allowed_tier,
            "proposal_id": proposal_id,
            "patch_result": patch_result,
            "governor_state": decision["state"],
        }
