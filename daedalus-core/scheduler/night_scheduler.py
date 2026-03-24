# scheduler/night_scheduler.py

"""
Night Scheduler

Runs nightly maintenance tasks, including self-healing improvement cycles.
"""

from knowledge.self_healing_orchestrator import run_improvement_cycle
from knowledge.audit_log import log_event


def run_nightly_self_healing():
    """
    Run a nightly self-healing / improvement cycle.
    """

    log_event("night_scheduler_start", {"task": "self_healing"})

    result = run_improvement_cycle(
        goal="general system improvement",
        max_candidates=3,
        max_iterations=5,
        strict_safety=True,
    )

    log_event("night_scheduler_complete", {
        "task": "self_healing",
        "result": result,
    })

    return result
