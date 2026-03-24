# runtime/runtime_loop_bootstrap.py
"""
Passive single-cycle runner that exercises every subsystem façade once.

Returns a structured snapshot for inspection. Does not schedule, loop, or
mutate subsystem state beyond what the façades already do internally
(e.g. SHO caches its last cycle result).
"""

from __future__ import annotations

import time
from typing import Any, Dict


def run_runtime_cycle_once() -> Dict[str, Any]:
    """
    Execute one passive read-through of every subsystem façade.

    Call order:
      1. diagnostics  – collect_health_report()
      2. governor     – get_governor_status()
      3. SHO          – run_sho_cycle()
      4. self-model   – get_self_summary()
      5. maintenance  – run_maintenance_dry_run()
      6. integration  – get_system_snapshot()

    Each step is isolated: a failure in one does not abort the rest.
    """
    results: Dict[str, Any] = {}

    try:
        from runtime.diagnostics_bootstrap import collect_health_report

        results["diagnostics"] = collect_health_report()
    except Exception as exc:
        results["diagnostics"] = {"status": "error", "error": str(exc)}

    try:
        from governor.singleton import get_governor_status

        results["governor"] = get_governor_status()
    except Exception as exc:
        results["governor"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.sho_bootstrap import run_sho_cycle

        results["sho"] = run_sho_cycle()
    except Exception as exc:
        results["sho"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.self_model_bootstrap import get_self_summary

        results["self_model"] = get_self_summary()
    except Exception as exc:
        results["self_model"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.maintenance_bootstrap import run_maintenance_dry_run

        results["maintenance"] = run_maintenance_dry_run()
    except Exception as exc:
        results["maintenance"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.integration_bootstrap import get_system_snapshot

        results["snapshot"] = get_system_snapshot()
    except Exception as exc:
        results["snapshot"] = {"status": "error", "error": str(exc)}

    out = {
        "status": "ok",
        "timestamp": time.time(),
        "results": results,
    }

    try:
        from runtime.telemetry import make_telemetry_record, record_telemetry

        record_telemetry(make_telemetry_record(out))
    except Exception:
        pass

    return out
