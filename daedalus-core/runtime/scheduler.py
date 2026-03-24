# runtime/scheduler.py

from __future__ import annotations
from typing import Dict, Any

from runtime.readiness_score import compute_readiness_score
from orchestrator.sho_cycle_orchestrator import run_sho_cycle


def scheduler_tick(governor) -> Dict[str, Any]:
    """
    Scheduler runs periodically and may trigger SHO cycles.
    """

    readiness = compute_readiness_score()
    score = readiness["readiness_score"]

    # If readiness is too low, do not run SHO
    if score < 0.4:
        return {"status": "skipped_low_readiness"}

    # Governor evaluates before deciding
    governor.evaluate()

    # SHO cycle allowed only if tier >= 2
    if governor.tier < 2:
        return {"status": "skipped_low_tier"}

    cycle = run_sho_cycle(governor)

    return {
        "status": "cycle_run",
        "cycle": cycle,
    }
