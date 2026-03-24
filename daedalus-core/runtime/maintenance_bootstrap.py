# runtime/maintenance_bootstrap.py
"""
Stable entry points for the maintenance scheduler layer.

Delegates to :mod:`runtime.maintenance_scheduler` (the live singleton) and
:mod:`knowledge.maintenance_scheduler` when importable. Returns safe fallback
structures on failure. No state mutation except through the existing scheduler
singleton's own `.tick()`.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict

from runtime.maintenance_scheduler import maintenance_scheduler


def get_maintenance_status() -> Dict[str, Any]:
    """
    Current status of the runtime maintenance scheduler singleton.

    Read-only; does not trigger a new check cycle.
    """
    return {
        "status": "ok",
        "last_check": maintenance_scheduler.last_check,
        "interval_seconds": maintenance_scheduler.interval,
        "current_recommendations": maintenance_scheduler.recommendations,
    }


def get_maintenance_plan() -> Dict[str, Any]:
    """
    Retrieve the knowledge-layer scheduler report if importable,
    otherwise return a minimal structure.
    """
    try:
        from knowledge.maintenance_scheduler import DEFAULT_INTERVALS, LAST_RUN

        plan = []
        now = time.time()
        for task, interval in DEFAULT_INTERVALS.items():
            last = LAST_RUN.get(task, 0)
            due_in = max(0.0, interval - (now - last))
            plan.append({
                "task": task,
                "interval_seconds": interval,
                "last_run": last or None,
                "due_in_seconds": round(due_in, 1),
            })
        return {"status": "ok", "plan": plan}
    except Exception:
        return {"status": "unavailable", "plan": []}


def run_maintenance_dry_run() -> Dict[str, Any]:
    """
    Simulate a tick of the runtime scheduler and return the recommendations.

    Does **not** run the knowledge-layer `run_scheduler()` (which has side effects).
    Calls `.tick()` on the existing singleton, which is designed to be safe and
    idempotent (only checks if enough time has passed).
    """
    try:
        recs = maintenance_scheduler.tick()
        return {"status": "ok", "simulated_tasks": [], "recommendations": recs}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "simulated_tasks": []}


def summarize_maintenance() -> str:
    """Human-readable summary for REPL-style output."""
    st = get_maintenance_status()
    lines = [
        "=== MAINTENANCE SCHEDULER ===",
        f"last check:        {st['last_check'] or 'never'}",
        f"check interval:    {st['interval_seconds']}s",
        f"recommendations:   {json.dumps(st['current_recommendations'], default=str) if st['current_recommendations'] else 'none'}",
    ]

    plan = get_maintenance_plan()
    if plan["status"] == "ok" and plan["plan"]:
        lines.append("")
        lines.append("Scheduled tasks:")
        for t in plan["plan"]:
            lines.append(
                f"  {t['task']:30s}  interval={t['interval_seconds']}s  "
                f"due_in={t['due_in_seconds']}s"
            )
    return "\n".join(lines)
