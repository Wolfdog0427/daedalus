# runtime/integration_bootstrap.py
"""
Unified integration layer for cross-subsystem introspection.

Composes read-only snapshots from existing bootstrap façades. Does not modify
governor, SHO, diagnostics, self-model, or maintenance logic.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict


def get_system_snapshot() -> Dict[str, Any]:
    """
    Consolidated dict: diagnostics, governor, SHO, self-model, maintenance.

    Each subsystem is filled independently; failures are isolated per key.
    """
    subsystems: Dict[str, Any] = {}

    try:
        from runtime.diagnostics_bootstrap import collect_health_report

        subsystems["diagnostics"] = collect_health_report()
    except Exception as exc:
        subsystems["diagnostics"] = {"status": "error", "error": str(exc)}

    try:
        from governor.singleton import get_governor_status

        subsystems["governor"] = get_governor_status()
    except Exception as exc:
        subsystems["governor"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.sho_bootstrap import get_sho_status

        subsystems["sho"] = get_sho_status()
    except Exception as exc:
        subsystems["sho"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.self_model_bootstrap import get_self_summary

        subsystems["self_model"] = {"status": "ok", "summary": get_self_summary()}
    except Exception as exc:
        subsystems["self_model"] = {"status": "error", "error": str(exc)}

    try:
        from runtime.maintenance_bootstrap import get_maintenance_status, get_maintenance_plan

        subsystems["maintenance"] = {
            "status": get_maintenance_status(),
            "plan": get_maintenance_plan(),
        }
    except Exception as exc:
        subsystems["maintenance"] = {"status": "error", "error": str(exc)}

    return {
        "status": "ok",
        "timestamp": time.time(),
        "subsystems": subsystems,
    }


def get_system_overview() -> Dict[str, Any]:
    """
    Compact cross-subsystem summary (presence / error per area).
    """
    snap = get_system_snapshot()
    sub = snap.get("subsystems") or {}
    overview_sub: Dict[str, str] = {}

    for name, payload in sub.items():
        if not isinstance(payload, dict):
            overview_sub[name] = "ok"
            continue
        if payload.get("status") == "error" or "error" in payload:
            overview_sub[name] = "error"
            continue
        overview_sub[name] = "ok"

    return {
        "status": "ok",
        "timestamp": snap.get("timestamp"),
        "subsystems": overview_sub,
    }


def summarize_system() -> str:
    """Human-readable + JSON overview for REPL-style output."""
    overview = get_system_overview()
    lines = [
        "=== SYSTEM INTEGRATION VIEW ===",
        f"timestamp: {overview.get('timestamp')}",
        "",
        "Subsystem rollup:",
    ]
    for k, v in overview.get("subsystems", {}).items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Full overview (JSON):")
    lines.append(json.dumps(overview, indent=2, default=str))
    return "\n".join(lines)
