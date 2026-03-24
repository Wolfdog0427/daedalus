# governor/autonomy_governor.py

from __future__ import annotations

from typing import Any, Dict, Optional

from governor.state_store import load_state, save_state
from governor.rules import (
    decide_base_tier,
    should_recommend_tier2,
    should_recommend_tier3,
    is_tier3_blocked,
)
from governor.proposal_manager import create_proposal, list_pending_proposals, update_proposal_status
from runtime.notification_hooks import (
    notify_tier3_proposal_created,
    notify_escalation_recommended,
    notify_autonomy_mode_changed,
    notify_system_locked,
    notify_system_unlocked,
)
from runtime.logging_manager import log_event
from knowledge.proposal_action_planner import generate_actions_for_proposal


class AutonomyGovernor:
    """
    Autonomy Governor:
    - Tracks autonomy mode, tier, lock state.
    - Evaluates drift, diagnostics, stability, patch history.
    - Recommends Tier 2 / Tier 3.
    - Creates proposals for higher-risk changes.
    - Exposes a clean interface for SHO and UI.
    """

    def __init__(self) -> None:
        self._state = load_state()

    def refresh_state(self) -> None:
        self._state = load_state()

    def get_state(self) -> Dict[str, Any]:
        return self._state

    def set_autonomy_mode(self, mode: str) -> None:
        if mode not in ("strict", "normal", "permissive"):
            return
        self._state["autonomy_mode"] = mode
        save_state(self._state)
        notify_autonomy_mode_changed(mode)
        log_event("autonomy_mode", f"Autonomy mode changed to {mode}")

    def lock(self) -> None:
        self._state["locked"] = True
        save_state(self._state)
        notify_system_locked()
        log_event("lock", "System locked")

    def unlock(self) -> None:
        self._state["locked"] = False
        save_state(self._state)
        notify_system_unlocked()
        log_event("lock", "System unlocked")

    def get_pending_proposals(self):
        return list_pending_proposals()

    def decide_for_cycle(
        self,
        cycle_id: str,
        drift: Dict[str, Any],
        diagnostics: Dict[str, Any],
        stability: Dict[str, Any],
        patch_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Main entry point for SHO.
        Returns a decision dict describing:
        - allowed_tier
        - should_generate_proposal
        - proposal_id (if any)
        - escalation flags
        - updated governor state
        """

        self.refresh_state()

        self._state["drift"] = {
            "level": drift.get("level", "none"),
            "score": drift.get("score", 0.0),
        }
        self._state["stability"] = {
            "score": stability.get("score", 1.0),
            "risk": stability.get("risk", "none"),
        }

        weakest = self._extract_weakest_subsystem(diagnostics)
        self._state["weakest_subsystem"] = weakest

        self._state["patch_history"] = {
            "total_cycles": patch_history.get("total_cycles", 0),
            "successful_patches": patch_history.get("successful_patches", 0),
            "failed_patches": patch_history.get("failed_patches", 0),
            "reverted_patches": patch_history.get("reverted_patches", 0),
            "recent_failures": patch_history.get("recent_failures", []),
        }

        base_tier = decide_base_tier(
            autonomy_mode=self._state["autonomy_mode"],
            locked=self._state["locked"],
        )

        drift_level = self._state["drift"]["level"]
        weakest_risk = weakest["risk"]
        stability_risk = self._state["stability"]["risk"]

        failed_high_level = patch_history.get("failed_high_level_cycles", 0)
        failed_tier2 = patch_history.get("failed_tier2_cycles", 0)

        tier2_rec = should_recommend_tier2(
            drift_level=drift_level,
            weakest_risk=weakest_risk,
            failed_high_level_cycles=failed_high_level,
        )

        tier3_rec = should_recommend_tier3(
            drift_level=drift_level,
            weakest_risk=weakest_risk,
            failed_high_level_cycles=failed_high_level,
            failed_tier2_cycles=failed_tier2,
            stability_risk=stability_risk,
        )

        tier3_block = is_tier3_blocked(
            base_tier=base_tier,
            autonomy_mode=self._state["autonomy_mode"],
            locked=self._state["locked"],
            stability_risk=stability_risk,
        )

        if tier3_block["blocked"]:
            tier3_rec = False

        if tier2_rec:
            notify_escalation_recommended(2, "Governor detected medium/high drift or subsystem risk.")
            log_event("escalation", "Tier 2 escalation recommended")

        if tier3_rec:
            notify_escalation_recommended(3, "Governor detected high drift + subsystem instability.")
            log_event("escalation", "Tier 3 escalation recommended")

        self._state["escalation"] = {
            "tier2_recommended": tier2_rec,
            "tier3_recommended": tier3_rec,
            "tier3_block_reason": tier3_block["reason"] if tier3_rec is False else None,
        }

        allowed_tier = base_tier
        if allowed_tier > 1 and not tier2_rec and not tier3_rec:
            allowed_tier = min(allowed_tier, 2)

        self._state["current_tier"] = allowed_tier

        proposal_id: Optional[str] = None
        should_generate_proposal = False
        planned_actions: Optional[list] = None

        if tier2_rec or tier3_rec:
            should_generate_proposal = True
            tier_requested = 3 if tier3_rec else 2
            proposal = self._create_proposal_from_context(
                cycle_id=cycle_id,
                tier_requested=tier_requested,
                diagnostics=diagnostics,
                drift=self._state["drift"],
                weakest=weakest,
                stability=self._state["stability"],
            )
            proposal_id = proposal["id"]
            planned_actions = proposal.get("planned_actions", [])

        save_state(self._state)

        log_event(
            "governor_decision",
            f"Governor decision for cycle {cycle_id}",
            {
                "allowed_tier": allowed_tier,
                "tier2_rec": tier2_rec,
                "tier3_rec": tier3_rec,
                "proposal_id": proposal_id,
            },
        )

        return {
            "allowed_tier": allowed_tier,
            "should_generate_proposal": should_generate_proposal,
            "proposal_id": proposal_id,
            "planned_actions": planned_actions or [],
            "escalation": self._state["escalation"],
            "state": self._state,
        }

    def _extract_weakest_subsystem(self, diagnostics: Dict[str, Any]) -> Dict[str, Any]:
        subs = diagnostics.get("subsystems") or []
        if not subs:
            return {
                "name": "global",
                "score": 1.0,
                "risk": "none",
            }
        weakest = min(subs, key=lambda s: s.get("score", 1.0))
        return {
            "name": weakest.get("subsystem", "unknown"),
            "score": weakest.get("score", 1.0),
            "risk": weakest.get("risk", "none"),
        }

    def _create_proposal_from_context(
        self,
        cycle_id: str,
        tier_requested: int,
        diagnostics: Dict[str, Any],
        drift: Dict[str, Any],
        weakest: Dict[str, Any],
        stability: Dict[str, Any],
    ) -> Dict[str, Any]:
        overall_score = diagnostics.get("overall_score", 1.0)
        overall_risk = diagnostics.get("overall_risk", "none")

        diagnostics_summary = {
            "overall_score": overall_score,
            "overall_risk": overall_risk,
            "subsystem_score": weakest["score"],
            "subsystem_message": f"Weakest subsystem: {weakest['name']} (risk={weakest['risk']})",
        }

        drift_context = {
            "drift_level": drift.get("level", "none"),
            "drift_score": drift.get("score", 0.0),
            "weakest_subsystem": weakest["name"],
        }

        proposal_summary = f"Subsystem {weakest['name']} shows elevated risk; tier {tier_requested} changes recommended."

        justification = [
            f"Drift level: {drift_context['drift_level']}",
            f"Weakest subsystem: {weakest['name']} (risk={weakest['risk']}, score={weakest['score']})",
            f"Stability risk: {stability.get('risk', 'none')}",
        ]

        planned_actions: list = []  # will be filled by planner

        expected_impact = {
            "stability_delta": 0.0,
            "risk_delta": -0.05,
            "trust_delta": 0.05,
            "confidence": 0.7,
        }

        sandbox_preview = {
            "status": "not_run",
            "notes": "Sandbox evaluation to be performed by SHO.",
        }

        priority = "normal"
        if drift_context["drift_level"] == "high" or weakest["risk"] == "high":
            priority = "high"

        proposal = create_proposal(
            tier_requested=tier_requested,
            subsystem=weakest["name"],
            risk_level=weakest["risk"],
            priority=priority,
            drift_context=drift_context,
            diagnostics_summary=diagnostics_summary,
            proposal_summary=proposal_summary,
            justification=justification,
            planned_actions=planned_actions,
            expected_impact=expected_impact,
            sandbox_preview=sandbox_preview,
            source_cycle_id=cycle_id,
        )

        # Now generate real planned_actions and persist them
        proposal["planned_actions"] = generate_actions_for_proposal(proposal)

        # Persist updated proposal with actions back into state
        state = load_state()
        pending = state.get("proposals", {}).get("pending", [])
        for p in pending:
            if p["id"] == proposal["id"]:
                p["planned_actions"] = proposal["planned_actions"]
                break
        save_state(state)

        log_event(
            "proposal_created",
            f"Proposal {proposal['id']} created for subsystem {weakest['name']}",
            {"tier": tier_requested},
        )

        if tier_requested == 3:
            notify_tier3_proposal_created(
                proposal_id=proposal["id"],
                subsystem=weakest["name"],
            )

        return proposal

    def record_proposal_decision(
        self,
        proposal_id: str,
        status: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        For UI / user decisions: approve/reject/cancel proposals.
        """
        if status not in ("approved", "rejected", "cancelled"):
            return None
        result = update_proposal_status(
            proposal_id=proposal_id,
            status=status,
            decided_by=decided_by,
            reason=reason,
        )
        log_event(
            "proposal_decision",
            f"Proposal {proposal_id} {status} by {decided_by}",
            {"reason": reason},
        )
        return result
