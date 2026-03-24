from typing import Any, Dict

from core.contracts import Patch, CycleResult


class SandboxRunner:
    """
    Applies patches in a sandbox, runs tests, collects metrics.
    """

    def run_cycle(self, patches: Dict[str, Patch]) -> CycleResult:
        # TODO: apply patches in temp copy, run tests, capture metrics
        return CycleResult(
            success=False,
            tests_passed=0,
            tests_failed=0,
            metrics={},
            behavior_snapshot={},
        )
