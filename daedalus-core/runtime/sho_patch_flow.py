# runtime/sho_patch_flow.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from governor.autonomy_governor import AutonomyGovernor
from runtime.approval_interface import ApprovalInterface
from runtime.logging_manager import log_event
from knowledge.patch_applier import apply_patch_in_sandbox, apply_patch_live
from knowledge.patch_outcome_memory import record_outcome


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class SHOPatchFlow:
    """
    SHO Patch Flow

    Orchestrates:
    - SHO improvement cycle requests (proposal creation via governor)
    - Post-approval patch application (sandbox + live)
    - Patch history updates
    - Rollback-aware patch result reporting
    - Outcome recording for learning
    """

    def __init__(self) -> None:
        self.gov = AutonomyGovernor()
        self.approvals = ApprovalInterface()

    # -------------------------------------------------
    # SHO Improvement Cycle (proposal creation)
    # -------------------------------------------------

    def run_improvement_cycle(
        self,
        cycle_id: str,
        drift: Dict[str, Any],
        diagnostics: Dict[str, Any],
        stability: Dict[str, Any],
        patch_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Trigger an SHO improvement cycle.

        Delegates to the AutonomyGovernor to:
        - evaluate drift/diagnostics/stability
        - decide tier
        - create a proposal (if warranted)
        - return governor_state + proposal_id
        """
        log_event(
            "sho_cycle",
            f"SHO improvement cycle requested: {cycle_id}",
            {
                "drift": drift,
                "stability": stability,
            },
        )

        result = self.gov.run_improvement_cycle(
            cycle_id=cycle_id,
            drift=drift,
            diagnostics=diagnostics,
            stability=stability,
            patch_history=patch_history,
        )

        return result

    # -------------------------------------------------
    # Post-Approval Patch Application
    # -------------------------------------------------

    def _build_plan_from_proposal(
        self,
        proposal_id: str,
        cycle_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Build a patch plan from a stored proposal.
        """
        proposal = self.approvals.get_proposal(proposal_id)
        if not proposal:
            return None

        tier = proposal.get("tier_requested") or proposal.get("tier")
        planned_actions = proposal.get("planned_actions", [])

        return {
            "cycle_id": cycle_id,
            "proposal_id": proposal_id,
            "tier": tier,
            "planned_actions": planned_actions,
        }

    def _update_patch_history_on_failure(
        self,
        patch_history: Dict[str, Any],
        cycle_id: str,
        tier: int,
        phase: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update patch history when a patch attempt fails.
        """
        new_history = dict(patch_history) if patch_history is not None else {}

        total_cycles = new_history.get("total_cycles", 0) + 1
        failed_patches = new_history.get("failed_patches", 0) + 1

        new_history["total_cycles"] = total_cycles
        new_history["failed_patches"] = failed_patches
        new_history.setdefault("successful_patches", new_history.get("successful_patches", 0))
        new_history.setdefault("reverted_patches", new_history.get("reverted_patches", 0))
        new_history.setdefault("failed_high_level_cycles", new_history.get("failed_high_level_cycles", 0))
        new_history.setdefault("failed_tier2_cycles", new_history.get("failed_tier2_cycles", 0))

        recent_failures: List[Dict[str, Any]] = new_history.get("recent_failures", [])
        recent_failures.append(
            {
                "cycle_id": cycle_id,
                "tier": tier,
                "timestamp": _now_iso(),
                "details": {
                    "phase": phase,
                    **details,
                },
            }
        )
        new_history["recent_failures"] = recent_failures

        return new_history

    def _update_patch_history_on_success(
        self,
        patch_history: Dict[str, Any],
        cycle_id: str,
        tier: int,
    ) -> Dict[str, Any]:
        """
        Update patch history when a patch attempt succeeds.
        """
        new_history = dict(patch_history) if patch_history is not None else {}

        total_cycles = new_history.get("total_cycles", 0) + 1
        successful_patches = new_history.get("successful_patches", 0) + 1

        new_history["total_cycles"] = total_cycles
        new_history["successful_patches"] = successful_patches
        new_history.setdefault("failed_patches", new_history.get("failed_patches", 0))
        new_history.setdefault("reverted_patches", new_history.get("reverted_patches", 0))
        new_history.setdefault("failed_high_level_cycles", new_history.get("failed_high_level_cycles", 0))
        new_history.setdefault("failed_tier2_cycles", new_history.get("failed_tier2_cycles", 0))
        new_history.setdefault("recent_failures", new_history.get("recent_failures", []))

        return new_history

    def resume_after_approval(
        self,
        proposal_id: str,
        cycle_id: str,
        patch_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        After a proposal is approved by the user, run:
        - sandbox patch
        - live patch (rollback + validation aware)
        - patch history update
        - outcome recording for learning

        Returns:

        {
            "status": "tier3_patch_attempted",
            "proposal_id": "...",
            "patch_result": {...},
            "patch_history": {...},
        }
        """
        log_event(
            "sho_cycle",
            f"Resume after approval for proposal {proposal_id}",
            {"cycle_id": cycle_id},
        )

        plan = self._build_plan_from_proposal(proposal_id, cycle_id)
        if plan is None:
            log_event(
                "sho_cycle",
                f"Proposal {proposal_id} not found when resuming",
                {"cycle_id": cycle_id},
            )
            return {
                "status": "proposal_not_found",
                "proposal_id": proposal_id,
                "patch_history": patch_history,
            }

        tier = plan.get("tier", 3)

        # 1) Sandbox phase
        sandbox_result = apply_patch_in_sandbox(plan)
        if sandbox_result.get("status") != "success":
            patch_result = {
                "status": "failed",
                "details": {
                    "phase": "sandbox",
                    "sandbox": sandbox_result.get("details", {}),
                },
            }

            new_history = self._update_patch_history_on_failure(
                patch_history=patch_history,
                cycle_id=cycle_id,
                tier=tier,
                phase="sandbox",
                details={
                    "sandbox": sandbox_result.get("details", {}),
                },
            )

            log_event(
                "sho_cycle",
                f"Sandbox patch failed for proposal {proposal_id}",
                {
                    "cycle_id": cycle_id,
                    "sandbox_details": sandbox_result.get("details", {}),
                },
            )

            # Record outcome for learning
            record_outcome(plan, patch_result)

            return {
                "status": "tier3_patch_attempted",
                "proposal_id": proposal_id,
                "patch_result": patch_result,
                "patch_history": new_history,
            }

        # 2) Live phase (rollback + validation aware)
        live_result = apply_patch_live(plan)
        live_status = live_result.get("status")
        live_details = live_result.get("details", {})

        if live_status != "success":
            patch_result = {
                "status": "failed",
                "details": {
                    "phase": live_details.get("phase", "live"),
                    "sandbox": sandbox_result.get("details", {}),
                    "live": live_details,
                    "rolled_back": live_details.get("rolled_back", True),
                },
            }

            new_history = self._update_patch_history_on_failure(
                patch_history=patch_history,
                cycle_id=cycle_id,
                tier=tier,
                phase=patch_result["details"]["phase"],
                details={
                    "sandbox": sandbox_result.get("details", {}),
                    "live": live_details,
                },
            )

            log_event(
                "sho_cycle",
                f"Live patch failed for proposal {proposal_id}",
                {
                    "cycle_id": cycle_id,
                    "live_details": live_details,
                },
            )

            # Record outcome for learning
            record_outcome(plan, patch_result)

            return {
                "status": "tier3_patch_attempted",
                "proposal_id": proposal_id,
                "patch_result": patch_result,
                "patch_history": new_history,
            }

        # 3) Success path
        patch_result = {
            "status": "success",
            "details": {
                "phase": "live",
                "sandbox": sandbox_result.get("details", {}),
                "live": live_details,
            },
        }

        new_history = self._update_patch_history_on_success(
            patch_history=patch_history,
            cycle_id=cycle_id,
            tier=tier,
        )

        log_event(
            "sho_cycle",
            f"Patch successfully applied for proposal {proposal_id}",
            {
                "cycle_id": cycle_id,
                "sandbox_details": sandbox_result.get("details", {}),
                "live_details": live_details,
            },
        )

        # Record outcome for learning
        record_outcome(plan, patch_result)

        return {
            "status": "tier3_patch_attempted",
            "proposal_id": proposal_id,
            "patch_result": patch_result,
            "patch_history": new_history,
        }
