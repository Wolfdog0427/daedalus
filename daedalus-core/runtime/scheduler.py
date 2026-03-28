# runtime/scheduler.py

from __future__ import annotations
from typing import Dict, Any

from runtime.readiness_score import compute_readiness_score
from orchestrator.sho_cycle_orchestrator import run_sho_cycle

try:
    from knowledge.integration_layer import do_meta_cycle
    _META_AVAILABLE = True
except ImportError:
    _META_AVAILABLE = False


def scheduler_tick(governor) -> Dict[str, Any]:
    """
    Scheduler runs periodically and may trigger:
    - Meta-cognition cycle (knowledge maintenance, curiosity, flow tuning)
    - SHO cycles (self-healing)
    """

    readiness = compute_readiness_score()
    score = readiness["readiness_score"]

    result: Dict[str, Any] = {"readiness_score": score}

    # Run meta-cognition cycle (knowledge health, curiosity, provider
    # discovery, flow tuning, deferred verification)
    if _META_AVAILABLE and score >= 0.3:
        try:
            meta_report = do_meta_cycle()
            if meta_report.get("allowed", False):
                result["meta_cycle"] = {
                    "status": "completed",
                    "actions": [a.get("type", "unknown") for a in meta_report.get("actions", [])],
                }
            else:
                result["meta_cycle"] = {"status": "blocked_by_governor"}
        except Exception as e:
            result["meta_cycle"] = {"status": "error", "error": str(e)}

    # If readiness is too low, do not run SHO
    if score < 0.4:
        result["status"] = "skipped_low_readiness"
        return result

    # SHO cycle allowed only if tier >= 2
    if getattr(governor, "tier", 1) < 2:
        result["status"] = "skipped_low_tier"
        return result

    cycle = run_sho_cycle(governor)

    result["status"] = "cycle_run"
    result["cycle"] = cycle
    return result
