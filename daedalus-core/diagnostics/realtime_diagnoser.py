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

    def analyze_interaction(self, snapshot: Dict[str, Any]) -> Optional[FailureReport]:
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
