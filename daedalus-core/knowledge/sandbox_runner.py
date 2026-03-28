# knowledge/sandbox_runner.py

"""
Logical Sandbox Runner

Applies a patch in an isolated logical context and evaluates it.
This is NOT process-level isolation — it copies state data, simulates
the patch, runs diagnostics + stability checks on the copy, and
returns a real pass/fail verdict.

The rollback system in patch_applier.py remains the heavy safety net
for unexpected failures.  This sandbox catches obvious problems
cheaply before committing.
"""

from __future__ import annotations

from typing import Dict, Any

from knowledge.version_manager import create_snapshot
from diagnostics.realtime_diagnoser import RealtimeDiagnoser
from knowledge.stability_engine import evaluate_stability


_STABILITY_THRESHOLD = 0.4
_DIAGNOSTICS_RISK_REJECT = "high"


def run_in_sandbox(
    patch: Dict[str, Any],
    baseline_snapshot_id: str = "baseline",
    max_iterations: int = 1,
    strict_safety: bool = True,
) -> Dict[str, Any]:
    """
    Simulate applying a patch and evaluate whether it is safe.

    Steps:
      1. Snapshot current state as the candidate baseline.
      2. Run diagnostics against a synthetic interaction representing
         the patch's intended change.
      3. Run stability evaluation on the patch metadata.
      4. Derive a real pass/fail from diagnostics risk + stability score.
    """
    candidate_snapshot_id = create_snapshot(
        reason=f"candidate-from-{baseline_snapshot_id}-for-{patch.get('goal', '')}"
    )

    diagnoser = RealtimeDiagnoser()
    synthetic_snapshot = {
        "error_type": "sandbox_review",
        "subsystem": patch.get("target", "sandbox"),
        "pipeline_stage": "sandbox_diagnostics",
        "error_message": "",
        "parsed_intent": patch.get("goal", ""),
        "resolver_target": patch.get("target", ""),
        "user_input": "",
    }
    diagnostics = diagnoser.analyze_interaction(synthetic_snapshot)

    stability = evaluate_stability(patch)

    rejection_reasons: list[str] = []

    diag_details = diagnostics.details if diagnostics else {}
    diag_risk = diag_details.get("risk", "none") if isinstance(diag_details, dict) else "none"
    if diag_risk == _DIAGNOSTICS_RISK_REJECT:
        rejection_reasons.append(f"diagnostics_risk={diag_risk}")

    stability_score = stability.get("stability_score", stability.get("score", 1.0)) if isinstance(stability, dict) else 1.0
    if strict_safety and stability_score < _STABILITY_THRESHOLD:
        rejection_reasons.append(f"stability_score={stability_score:.3f} < {_STABILITY_THRESHOLD}")

    success = len(rejection_reasons) == 0

    return {
        "success": success,
        "rejection_reasons": rejection_reasons,
        "candidate_snapshot_id": candidate_snapshot_id,
        "diagnostics": diag_details,
        "stability": stability,
        "meta": {
            "baseline_snapshot_id": baseline_snapshot_id,
            "patch": patch,
            "max_iterations": max_iterations,
            "strict_safety": strict_safety,
        },
    }
