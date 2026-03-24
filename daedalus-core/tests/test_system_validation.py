# tests/test_system_validation.py
"""
Full-system validation suite exercising all subsystem façades end-to-end.

Every scenario is read-only: no subsystem logic, scoring, thresholds, or
autonomy rules are modified. Results are structured dicts for human inspection.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
from unittest.mock import patch


EXPECTED_SUBSYSTEMS = {"diagnostics", "governor", "sho", "self_model", "maintenance"}


# ------------------------------------------------------------------ helpers


def _ok(scenario: str, details: Any = None) -> Dict[str, Any]:
    return {"scenario": scenario, "status": "ok", "details": details}


def _err(scenario: str, details: Any = None) -> Dict[str, Any]:
    return {"scenario": scenario, "status": "error", "details": details}


# ------------------------------------------------------------------ scenarios


def _safe_check(checks: Dict[str, Any], key: str, fn: Any) -> Any:
    """Run *fn*, store pass/fail in *checks[key]*, return the result or None."""
    try:
        result = fn()
        checks[key] = True
        return result
    except Exception as exc:
        checks[key] = f"FAIL: {exc}"
        return None


def scenario_cold_start_snapshot() -> Dict[str, Any]:
    """
    Scenario 1 — Cold Start Snapshot

    Call every façade individually then the integration snapshot; confirm each
    returns the expected type and the snapshot contains all subsystems.
    Each check is isolated so one import/runtime failure does not abort the rest.
    """
    name = "cold_start_snapshot"
    checks: Dict[str, Any] = {}
    try:
        from runtime.diagnostics_bootstrap import run_diagnostics, collect_health_report
        from governor.singleton import get_governor_status, get_current_tier
        from runtime.sho_bootstrap import get_sho_status
        from runtime.self_model_bootstrap import get_self_model, get_self_summary
        from runtime.maintenance_bootstrap import get_maintenance_status, get_maintenance_plan
        from runtime.integration_bootstrap import get_system_snapshot

        _safe_check(checks, "diagnostics_run",
                     lambda: isinstance(run_diagnostics(), dict))

        _safe_check(checks, "health_report",
                     lambda: isinstance(collect_health_report(), dict))

        _safe_check(checks, "governor_status",
                     lambda: get_governor_status().get("status") == "ok")

        _safe_check(checks, "governor_tier",
                     lambda: isinstance(get_current_tier(), int))

        _safe_check(checks, "sho_status",
                     lambda: isinstance(get_sho_status(), dict))

        _safe_check(checks, "self_model",
                     lambda: "capabilities" in get_self_model())

        _safe_check(checks, "self_summary",
                     lambda: isinstance(get_self_summary(), dict))

        _safe_check(checks, "maintenance_status",
                     lambda: get_maintenance_status().get("status") == "ok")

        _safe_check(checks, "maintenance_plan",
                     lambda: "plan" in get_maintenance_plan())

        snap = _safe_check(checks, "snapshot_call", get_system_snapshot)
        if isinstance(snap, dict):
            checks["snapshot_status"] = snap.get("status") == "ok"
            checks["snapshot_has_timestamp"] = isinstance(snap.get("timestamp"), float)
            present = set(snap.get("subsystems", {}).keys())
            checks["snapshot_subsystems_complete"] = EXPECTED_SUBSYSTEMS.issubset(present)

        all_pass = all(v is True for v in checks.values())
        return _ok(name, checks) if all_pass else _err(name, checks)
    except Exception as exc:
        checks["exception"] = str(exc)
        return _err(name, checks)


def scenario_sho_governor_snapshot() -> Dict[str, Any]:
    """
    Scenario 2 — SHO → Governor → Snapshot

    Run one SHO cycle, read the governor tier, take a snapshot, and confirm
    the SHO status in the snapshot reflects a recorded cycle.
    """
    name = "sho_governor_snapshot"
    checks: Dict[str, Any] = {}
    try:
        from runtime.sho_bootstrap import run_sho_cycle, get_sho_status
        from governor.singleton import get_current_tier
        from runtime.integration_bootstrap import get_system_snapshot

        cycle = run_sho_cycle()
        checks["cycle_returned_dict"] = isinstance(cycle, dict)
        checks["cycle_has_id"] = "cycle_id" in cycle
        checks["cycle_status"] = cycle.get("status") in ("ok", "error")

        tier = get_current_tier()
        checks["tier_is_int"] = isinstance(tier, int)

        status = get_sho_status()
        checks["last_cycle_recorded"] = status.get("last_cycle") is not None

        snap = get_system_snapshot()
        sho_sub = snap.get("subsystems", {}).get("sho", {})
        checks["snapshot_sho_has_last_cycle"] = sho_sub.get("last_cycle") is not None

        all_ok = all(checks.values())
        return _ok(name, checks) if all_ok else _err(name, checks)
    except Exception as exc:
        checks["exception"] = str(exc)
        return _err(name, checks)


def scenario_maintenance_dry_run() -> Dict[str, Any]:
    """
    Scenario 3 — Maintenance Dry-Run

    Call run_maintenance_dry_run(), confirm it returns a dict with expected
    keys, then confirm the integration snapshot includes maintenance.
    """
    name = "maintenance_dry_run"
    checks: Dict[str, Any] = {}
    try:
        from runtime.maintenance_bootstrap import run_maintenance_dry_run
        from runtime.integration_bootstrap import get_system_snapshot

        dr = run_maintenance_dry_run()
        checks["dry_run_is_dict"] = isinstance(dr, dict)
        checks["dry_run_has_status"] = "status" in dr
        checks["dry_run_has_tasks"] = "simulated_tasks" in dr

        snap = get_system_snapshot()
        m = snap.get("subsystems", {}).get("maintenance", {})
        checks["snapshot_has_maintenance"] = bool(m)

        all_ok = all(checks.values())
        return _ok(name, checks) if all_ok else _err(name, checks)
    except Exception as exc:
        checks["exception"] = str(exc)
        return _err(name, checks)


def scenario_failure_isolation() -> Dict[str, Any]:
    """
    Scenario 4 — Failure Isolation

    Monkeypatch the governor façade to raise, then confirm the integration
    snapshot marks only `governor` as errored while other subsystems survive.
    The patch is automatically reversed by unittest.mock.
    """
    name = "failure_isolation"
    checks: Dict[str, Any] = {}
    try:
        from runtime.integration_bootstrap import get_system_snapshot

        # integration_bootstrap does late `from governor.singleton import ...`
        # inside get_system_snapshot(), so patch at the source module.
        with patch(
            "governor.singleton.get_governor_status",
            side_effect=RuntimeError("synthetic test fault"),
        ):
            snap = get_system_snapshot()

        subs = snap.get("subsystems", {})

        gov = subs.get("governor", {})
        checks["governor_isolated_error"] = gov.get("status") == "error"
        checks["governor_error_message"] = "synthetic" in gov.get("error", "")

        for key in ("sho", "self_model", "maintenance"):
            sub = subs.get(key, {})
            if isinstance(sub, dict) and sub.get("status") == "error":
                checks[f"{key}_survived"] = False
            else:
                checks[f"{key}_survived"] = True

        all_ok = all(checks.values())
        return _ok(name, checks) if all_ok else _err(name, checks)
    except Exception as exc:
        checks["exception"] = str(exc)
        return _err(name, checks)


def scenario_summary_outputs() -> Dict[str, Any]:
    """
    Scenario 5 — Summary Outputs

    Call summarize_self(), summarize_maintenance(), summarize_system() and
    confirm each returns a non-empty string.
    """
    name = "summary_outputs"
    checks: Dict[str, Any] = {}
    try:
        from runtime.self_model_bootstrap import summarize_self
        from runtime.maintenance_bootstrap import summarize_maintenance
        from runtime.integration_bootstrap import summarize_system

        ss = summarize_self()
        checks["summarize_self_is_str"] = isinstance(ss, str)
        checks["summarize_self_nonempty"] = len(ss) > 0

        sm = summarize_maintenance()
        checks["summarize_maintenance_is_str"] = isinstance(sm, str)
        checks["summarize_maintenance_nonempty"] = len(sm) > 0

        sy = summarize_system()
        checks["summarize_system_is_str"] = isinstance(sy, str)
        checks["summarize_system_nonempty"] = len(sy) > 0

        all_ok = all(checks.values())
        return _ok(name, checks) if all_ok else _err(name, checks)
    except Exception as exc:
        checks["exception"] = str(exc)
        return _err(name, checks)


# ------------------------------------------------------------------ runner


ALL_SCENARIOS = [
    scenario_cold_start_snapshot,
    scenario_sho_governor_snapshot,
    scenario_maintenance_dry_run,
    scenario_failure_isolation,
    scenario_summary_outputs,
]


def run_all_system_validations() -> Dict[str, Any]:
    """
    Execute every scenario and collect results.

    Never raises. Never mutates subsystem state beyond what the façades
    themselves do (e.g. SHO caching the last cycle result).
    """
    results: List[Dict[str, Any]] = []
    for fn in ALL_SCENARIOS:
        try:
            results.append(fn())
        except Exception as exc:
            results.append(_err(fn.__name__, {"exception": str(exc)}))

    passed = sum(1 for r in results if r["status"] == "ok")
    failed = len(results) - passed

    return {
        "timestamp": time.time(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


# ------------------------------------------------------------------ CLI


if __name__ == "__main__":
    import json as _json

    report = run_all_system_validations()
    print(_json.dumps(report, indent=2, default=str))
