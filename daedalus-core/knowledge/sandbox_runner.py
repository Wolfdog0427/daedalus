# knowledge/sandbox_runner.py

"""
Sandbox Runner

Applies a patch in an isolated context and evaluates it.

Right now this is a logical sandbox, not a process/container sandbox:
- It uses snapshots from version_manager
- It simulates applying a patch
- It runs diagnostics + stability evaluation
- It returns a candidate snapshot_id and metrics

Later, you can upgrade this to:
- separate processes
- separate environments
- Docker-based sandboxes
"""

from __future__ import annotations

from typing import Dict, Any

# ---------------------------------------------------------
# Correct imports
# ---------------------------------------------------------
from knowledge.version_manager import create_snapshot
from diagnostics.realtime_diagnoser import RealtimeDiagnoser
from knowledge.stability_engine import evaluate_stability


def run_in_sandbox(
    patch: Dict[str, Any],
    baseline_snapshot_id: str = "baseline",
    max_iterations: int = 1,
    strict_safety: bool = True,
) -> Dict[str, Any]:
    """
    Simulate applying a patch and evaluating it.

    For now:
    - create a new snapshot (as if patched)
    - run diagnostics
    - run stability evaluation
    - return success + metrics

    Later:
    - actually modify code/knowledge in the snapshot
    - run tests in a separate process
    """

    # Create a new snapshot representing the patched candidate
    candidate_snapshot_id = create_snapshot(
        reason=f"candidate-from-{baseline_snapshot_id}-for-{patch.get('goal', '')}"
    )

    # Run diagnostics using the RealtimeDiagnoser
    diagnoser = RealtimeDiagnoser()

    synthetic_snapshot = {
        "error_type": "sandbox_review",
        "subsystem": "sandbox",
        "pipeline_stage": "sandbox_diagnostics",
        "error_message": "",
        "parsed_intent": "",
        "resolver_target": "",
        "user_input": "",
    }

    diagnostics = diagnoser.analyze_interaction(synthetic_snapshot)

    # Run stability evaluation
    stability = evaluate_stability(patch)

    # Simple success criteria stub
    success = True

    return {
        "success": success,
        "candidate_snapshot_id": candidate_snapshot_id,
        "diagnostics": diagnostics.details if diagnostics else {},
        "stability": stability,
        "meta": {
            "baseline_snapshot_id": baseline_snapshot_id,
            "patch": patch,
            "max_iterations": max_iterations,
            "strict_safety": strict_safety,
        },
    }
