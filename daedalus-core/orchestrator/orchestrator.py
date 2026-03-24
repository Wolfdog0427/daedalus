from typing import Optional

from core.contracts import (
    FixRequest,
    ImprovementPlan,
    CandidateSummary,
    ImprovementProposal,
)
from security.security_state import SecurityState
from security.code_integrity import CodeIntegrity
from config.security_config import CRITICAL_FILES
from versioning.version_manager import VersionManager


class SelfHealingOrchestrator:
    """
    Central coordinator for planning and running improvement cycles.
    Currently:
      - checks security posture via CodeIntegrity
      - converts ImprovementProposals into FixRequests
      - builds minimal ImprovementPlans
    """

    def __init__(self, code_integrity: CodeIntegrity, version_manager: VersionManager):
        self.code_integrity = code_integrity
        self.version_manager = version_manager

    def _check_security(self) -> bool:
        """
        Verify integrity of critical files and update SecurityState.
        """
        status = self.code_integrity.verify_integrity(CRITICAL_FILES)
        if not status.integrity_ok:
            SecurityState.mode = "suspicious"
            # later: surface via cockpit/meta-governor
            return False
        SecurityState.mode = "normal"
        return True

    def proposal_to_fix_request(self, proposal: ImprovementProposal) -> FixRequest:
        """
        Translate a high-level ImprovementProposal into a concrete FixRequest.
        """
        return FixRequest(
            target_subsystem=proposal.target_subsystem,
            change_type=proposal.proposal_type,
            severity="medium",
            constraints={},
            max_cycles=3,
            max_runtime_seconds=60,
        )

    def plan_improvement(self, fix_request: FixRequest) -> ImprovementPlan:
        """
        Build an initial ImprovementPlan from a FixRequest.
        Later this will consult meta-governor, architecture model, etc.
        """
        return ImprovementPlan(
            fix_request=fix_request,
            allowed_modules=[],
            forbidden_modules=[],
            change_budget_files=20,
            change_budget_lines=500,
            safety_invariants=[],
            night_mode=False,
        )

    def run_improvement_cycle(self, plan: ImprovementPlan) -> Optional[CandidateSummary]:
        """
        Stub for running a full improvement cycle.
        For now, it only respects security posture and integrity.
        """
        if SecurityState.mode != "normal":
            return None
        if not self._check_security():
            return None
        # TODO: sandbox, drift, meta-governor, etc.
        return None
