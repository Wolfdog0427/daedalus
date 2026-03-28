# knowledge/maintenance_scheduler.py

"""
Maintenance Scheduler

This module coordinates periodic maintenance tasks in a safe,
governed, autonomy-aware way.

It does NOT run on real timers.
Instead, it exposes a scheduler function that can be called
manually or by an external orchestrator.

It ensures:
- strict mode is respected
- readiness is evaluated
- only safe tasks run
- all actions pass through the action router
- full audit logs are returned
"""

from __future__ import annotations

import time
from typing import Dict, Any

from knowledge.action_router import route_command
from knowledge.autonomy_governor import get_autonomy_state, evaluate_readiness
from knowledge.self_model import update_self_model


# ------------------------------------------------------------
# DEFAULT INTERVALS (in seconds)
# ------------------------------------------------------------

DEFAULT_INTERVALS = {
    "self_model_update": 60 * 60,          # 1 hour
    "consistency_scan": 60 * 60 * 24,      # 24 hours
    "storage_maintenance": 60 * 60 * 24,   # 24 hours
    "concept_evolution": 60 * 60 * 24 * 7, # 7 days
}

# Persistent state (in-memory; external orchestrator can persist if desired)
LAST_RUN = {
    "self_model_update": 0,
    "consistency_scan": 0,
    "storage_maintenance": 0,
    "concept_evolution": 0,
}


# ------------------------------------------------------------
# INTERNAL CHECK
# ------------------------------------------------------------

def _should_run(task: str, now: float) -> bool:
    interval = DEFAULT_INTERVALS.get(task)
    last = LAST_RUN.get(task, 0)
    return (now - last) >= interval


# ------------------------------------------------------------
# SCHEDULER
# ------------------------------------------------------------

def run_scheduler() -> Dict[str, Any]:
    """
    Runs a full maintenance scheduling cycle.

    Returns a structured report:
    - what tasks were due
    - what tasks were allowed
    - what tasks were blocked
    - autonomy mode
    - readiness score
    - updated self-model summary
    """
    now = time.time()
    report = {
        "timestamp": now,
        "autonomy": get_autonomy_state(),
        "readiness": evaluate_readiness(),
        "tasks": [],
        "self_model_after": None,
    }

    # --------------------------------------------------------
    # 1. Self-model update (always allowed, no side effects)
    # --------------------------------------------------------
    if _should_run("self_model_update", now):
        update_self_model()
        LAST_RUN["self_model_update"] = now
        report["tasks"].append({
            "task": "self_model_update",
            "status": "completed",
        })

    # --------------------------------------------------------
    # 2. Consistency scan
    # --------------------------------------------------------
    if _should_run("consistency_scan", now):
        result = route_command("run a consistency scan")
        LAST_RUN["consistency_scan"] = now
        report["tasks"].append({
            "task": "consistency_scan",
            "status": "completed",
            "result": result,
        })

    # --------------------------------------------------------
    # 3. Storage maintenance
    # --------------------------------------------------------
    if _should_run("storage_maintenance", now):
        result = route_command("clean up storage")
        LAST_RUN["storage_maintenance"] = now
        report["tasks"].append({
            "task": "storage_maintenance",
            "status": "completed",
            "result": result,
        })

    # --------------------------------------------------------
    # 4. Concept evolution (high-impact)
    # --------------------------------------------------------
    if _should_run("concept_evolution", now):
        result = route_command("evolve concepts")
        LAST_RUN["concept_evolution"] = now
        report["tasks"].append({
            "task": "concept_evolution",
            "status": "completed",
            "result": result,
        })

    # --------------------------------------------------------
    # 5. Update self-model again after all actions
    # --------------------------------------------------------
    report["self_model_after"] = update_self_model()

    return report
