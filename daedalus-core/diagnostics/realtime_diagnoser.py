# diagnostics/realtime_diagnoser.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from diagnostics.subsystem_diagnoser import run_subsystem_diagnostics


@dataclass
class FailureReport:
    failure_type: str
    details: Dict[str, Any]


class RealtimeDiagnoser:
    """
    Realtime diagnoser with subsystem-aware system review.

    - For concrete failures (non-system_review), it just wraps the snapshot.
    - For system review cycles, it runs subsystem diagnostics and returns a
      structured health report.
    """

    def propose_fix(self, report: FailureReport):
        """Generate an ImprovementProposal from a failure report."""
        from core.contracts import ImprovementProposal
        subsystem = report.details.get("subsystem", "unknown")
        return ImprovementProposal(
            description=f"Auto-fix for {report.failure_type} in {subsystem}",
            target_subsystem=subsystem,
            proposal_type="bugfix",
            estimated_complexity="low",
            risk_level="low",
            expected_benefit=0.3,
        )

    def analyze_interaction(self, snapshot: Dict[str, Any]) -> Optional[FailureReport]:
        if not isinstance(snapshot, dict):
            return None
        failure_type = snapshot.get("error_type", "") or ""

        # Direct failure: just wrap the snapshot
        if failure_type and failure_type != "system_review":
            return FailureReport(
                failure_type=failure_type,
                details=snapshot,
            )

        # System review: run subsystem diagnostics
        subsystem_report = run_subsystem_diagnostics()

        return FailureReport(
            failure_type="system_review",
            details={
                "interaction_snapshot": snapshot,
                "subsystem_diagnostics": subsystem_report,
            },
        )
