from core.contracts import DriftReport, CycleResult


class DriftAnalyzer:
    """
    Computes drift and net improvement between baseline and candidate.
    """

    def analyze(self, baseline: CycleResult, candidate: CycleResult) -> DriftReport:
        # TODO: real drift computation
        return DriftReport(
            code_drift_pct=0.0,
            behavior_drift_pct=0.0,
            positive_change_score=0.0,
            negative_change_score=0.0,
            net_improvement=0.0,
            confidence=0.0,
        )
