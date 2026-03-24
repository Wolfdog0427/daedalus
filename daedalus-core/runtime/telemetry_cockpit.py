# runtime/telemetry_cockpit.py
"""
Cockpit-friendly views over the in-memory telemetry buffer.

Read-only, no persistence, no threads, no subsystem calls.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_cockpit_telemetry_overview() -> Dict[str, Any]:
    """
    Structured overview for cockpit consumers:

    - latest  : most recent telemetry record (or None)
    - recent  : last 10 records
    - error_counts : per-subsystem error tallies across the last 50 records
    """
    try:
        from runtime.telemetry import get_recent_telemetry, _SUBSYSTEM_KEYS
    except Exception:
        return {"latest": None, "recent": [], "error_counts": {}}

    recent_50 = get_recent_telemetry(50)
    recent_10 = recent_50[-10:] if len(recent_50) >= 10 else list(recent_50)
    latest: Optional[Dict[str, Any]] = recent_50[-1] if recent_50 else None

    errors: Dict[str, int] = {k: 0 for k in _SUBSYSTEM_KEYS}
    for rec in recent_50:
        subs = rec.get("subsystems")
        if not isinstance(subs, dict):
            continue
        for key in _SUBSYSTEM_KEYS:
            if subs.get(key) == "error":
                errors[key] += 1

    return {
        "latest": latest,
        "recent": recent_10,
        "error_counts": errors,
    }


def format_cockpit_telemetry() -> str:
    """
    Human-readable cockpit summary (plain text, no ANSI).
    """
    try:
        overview = get_cockpit_telemetry_overview()
    except Exception:
        return "Telemetry cockpit unavailable."

    lines = ["=== TELEMETRY COCKPIT ===", ""]

    latest = overview.get("latest")
    if latest:
        lines.append(f"Latest cycle timestamp: {latest.get('timestamp')}")
        subs = latest.get("subsystems") or {}
        lines.append("Subsystem status:")
        for k, v in subs.items():
            lines.append(f"  {k}: {v}")
    else:
        lines.append("No telemetry records yet.")

    lines.append("")
    errors = overview.get("error_counts") or {}
    lines.append("Error counts (last 50 cycles):")
    for k, v in errors.items():
        lines.append(f"  {k}: {v}")

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 3: trend views
# ------------------------------------------------------------


def get_cockpit_trend_overview() -> Dict[str, Any]:
    """
    Structured trend summary for cockpit consumers.
    """
    try:
        from runtime.telemetry import (
            compute_error_rate,
            compute_stability_signal,
            compute_sho_trend,
        )
    except Exception:
        return {"error_rates": {}, "stability": {}, "sho_trend": {}}

    return {
        "error_rates": compute_error_rate(50),
        "stability": compute_stability_signal(50),
        "sho_trend": compute_sho_trend(20),
    }


def format_cockpit_trends() -> str:
    """Human-readable trend summary (plain text, no ANSI)."""
    try:
        overview = get_cockpit_trend_overview()
    except Exception:
        return "Telemetry trend data unavailable."

    lines = ["=== TELEMETRY TRENDS ===", ""]

    er = overview.get("error_rates") or {}
    rates = er.get("rates") or {}
    lines.append(f"Error rates (last {er.get('window', '?')} cycles):")
    for k, v in rates.items():
        lines.append(f"  {k}: {v:.1%}")

    lines.append("")
    stab = overview.get("stability") or {}
    label = "STABLE" if stab.get("stable") else "UNSTABLE"
    lines.append(
        f"Stability: {label}  "
        f"(error-free {stab.get('error_free_cycles', '?')}"
        f"/{stab.get('total_cycles', '?')} cycles)"
    )

    lines.append("")
    sho = overview.get("sho_trend") or {}
    lines.append(
        f"SHO trend: {sho.get('trend', '?')}  "
        f"(ok={sho.get('sho_ok', '?')} err={sho.get('sho_error', '?')})"
    )

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 4: health & readiness views
# ------------------------------------------------------------


def get_cockpit_health_overview() -> Dict[str, Any]:
    """Structured health + readiness for cockpit consumers."""
    try:
        from runtime.telemetry import compute_system_health, compute_readiness_level
    except Exception:
        return {"system_health": {}, "readiness": {}}

    return {
        "system_health": compute_system_health(50),
        "readiness": compute_readiness_level(50),
    }


def format_cockpit_health() -> str:
    """Human-readable health summary (plain text, no ANSI)."""
    try:
        overview = get_cockpit_health_overview()
    except Exception:
        return "Health overview unavailable."

    lines = ["=== SYSTEM HEALTH ===", ""]

    health = overview.get("system_health") or {}
    lines.append(f"Overall: {health.get('overall', '?')}")

    rates = health.get("error_rates") or {}
    if rates:
        lines.append(f"Error rates (last {health.get('window', '?')} cycles):")
        for k, v in rates.items():
            lines.append(f"  {k}: {v:.1%}")

    stab = health.get("stability") or {}
    stab_label = "STABLE" if stab.get("stable") else "UNSTABLE"
    lines.append(
        f"Stability: {stab_label}  "
        f"(error-free {stab.get('error_free_cycles', '?')}"
        f"/{stab.get('total_cycles', '?')} cycles)"
    )

    sho = health.get("sho_trend") or {}
    lines.append(f"SHO trend: {sho.get('trend', '?')}")

    lines.append("")
    rd = overview.get("readiness") or {}
    lines.append(
        f"Readiness: level {rd.get('level', '?')} — {rd.get('description', '?')}"
    )

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 5: unified dashboard wrappers
# ------------------------------------------------------------


def get_cockpit_dashboard() -> Dict[str, Any]:
    """Delegate to :func:`runtime.system_dashboard.get_system_dashboard`."""
    try:
        from runtime.system_dashboard import get_system_dashboard

        return get_system_dashboard()
    except Exception:
        return {}


def format_cockpit_dashboard() -> str:
    """Delegate to :func:`runtime.system_dashboard.format_system_dashboard`."""
    try:
        from runtime.system_dashboard import format_system_dashboard

        return format_system_dashboard()
    except Exception:
        return "Dashboard unavailable."


# ------------------------------------------------------------
# Phase 7: integrity & degradation wrappers
# ------------------------------------------------------------


def get_cockpit_integrity() -> Dict[str, Any]:
    """Integrity flags + degradation level for cockpit consumers."""
    try:
        from runtime.telemetry import compute_integrity_flags, compute_degradation_level

        return {
            "integrity_flags": compute_integrity_flags(50),
            "degradation": compute_degradation_level(50),
        }
    except Exception:
        return {"integrity_flags": {}, "degradation": {}}


def format_cockpit_integrity() -> str:
    """Human-readable integrity summary (plain text, no ANSI)."""
    try:
        data = get_cockpit_integrity()
    except Exception:
        return "Integrity data unavailable."

    lines = ["=== RUNTIME INTEGRITY ===", ""]

    flags = (data.get("integrity_flags") or {}).get("flags") or {}
    lines.append("Integrity flags:")
    for k, v in flags.items():
        lines.append(f"  {k}: {'ACTIVE' if v else 'ok'}")

    lines.append("")
    deg = data.get("degradation") or {}
    lines.append(
        f"Degradation: level {deg.get('level', '?')} — {deg.get('description', '?')}"
    )

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 8: maintenance readiness wrappers
# ------------------------------------------------------------


def get_cockpit_maintenance_readiness() -> Dict[str, Any]:
    """Maintenance readiness gate for cockpit consumers."""
    try:
        from runtime.telemetry import compute_maintenance_readiness

        return compute_maintenance_readiness(50)
    except Exception:
        return {}


def format_cockpit_maintenance_readiness() -> str:
    """Human-readable maintenance readiness summary (plain text, no ANSI)."""
    try:
        mr = get_cockpit_maintenance_readiness()
    except Exception:
        return "Maintenance readiness data unavailable."

    lines = ["=== MAINTENANCE READINESS ===", ""]

    gate = mr.get("level", "?")
    ready = mr.get("ready", False)
    lines.append(f"Gate: {gate}  (ready={ready})")

    lines.append("")
    lines.append("Reasons:")
    for reason in mr.get("reasons") or []:
        lines.append(f"  - {reason}")

    lines.append("")
    health = (mr.get("health") or {}).get("overall", "?")
    rd = (mr.get("readiness") or {}).get("description", "?")
    deg = (mr.get("degradation") or {}).get("description", "?")
    drift = (mr.get("drift") or {}).get("drift", "?")
    lines.append(f"Contributing: health={health}  readiness={rd}  degradation={deg}  drift={drift}")

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 9: pre-maintenance checklist wrappers
# ------------------------------------------------------------


def get_cockpit_premaintenance_checklist() -> Dict[str, Any]:
    """Pre-maintenance checklist for cockpit consumers."""
    try:
        from runtime.telemetry import compute_premaintenance_checklist

        return compute_premaintenance_checklist(50)
    except Exception:
        return {}


def format_cockpit_premaintenance_checklist() -> str:
    """Human-readable pre-maintenance checklist (plain text, no ANSI)."""
    try:
        pc = get_cockpit_premaintenance_checklist()
    except Exception:
        return "Pre-maintenance checklist unavailable."

    lines = ["=== PRE-MAINTENANCE CHECKLIST ===", ""]

    lines.append(f"Overall: {pc.get('overall', '?')}")
    lines.append("")

    for item in pc.get("checklist") or []:
        lines.append(f"  [{item.get('status', '?'):4s}] {item.get('item', '?')}  ({item.get('details', '')})")

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 10: maintenance envelope wrappers
# ------------------------------------------------------------


def get_cockpit_maintenance_envelope() -> Dict[str, Any]:
    """Delegate to :func:`runtime.system_dashboard.get_maintenance_envelope_summary`."""
    try:
        from runtime.system_dashboard import get_maintenance_envelope_summary

        return get_maintenance_envelope_summary()
    except Exception:
        return {}


def format_cockpit_maintenance_envelope() -> str:
    """Delegate to :func:`runtime.system_dashboard.format_maintenance_envelope_summary`."""
    try:
        from runtime.system_dashboard import format_maintenance_envelope_summary

        return format_maintenance_envelope_summary()
    except Exception:
        return "Maintenance envelope unavailable."


# ------------------------------------------------------------
# Phase 11: maintenance action preview wrappers
# ------------------------------------------------------------


def get_cockpit_maintenance_action_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """Delegate to :func:`runtime.system_dashboard.get_maintenance_action_preview`."""
    try:
        from runtime.system_dashboard import get_maintenance_action_preview

        return get_maintenance_action_preview(action)
    except Exception:
        return {}


def format_cockpit_maintenance_action_preview(action: Dict[str, Any]) -> str:
    """Human-readable maintenance action preview (plain text, no ANSI)."""
    try:
        preview = get_cockpit_maintenance_action_preview(action)
    except Exception:
        return "Action preview unavailable."

    lines = ["=== MAINTENANCE ACTION PREVIEW ===", ""]

    act = (preview.get("validation") or {}).get("action") or action
    lines.append(f"Action: {act.get('name', '?')}")
    lines.append(f"Description: {act.get('description', '?')}")

    lines.append("")
    env = preview.get("envelope") or {}
    lines.append(f"Envelope: {env.get('summary', '?')}")

    val = preview.get("validation") or {}
    lines.append(f"Allowed: {val.get('allowed', False)}")
    for r in val.get("reasons") or []:
        lines.append(f"  - {r}")

    lines.append("")
    dr = preview.get("dry_run") or {}
    lines.append("Dry-run steps:")
    for idx, s in enumerate(dr.get("steps") or [], 1):
        lines.append(f"  {idx}. {s}")

    lines.append("")
    plan = preview.get("execution_plan") or {}
    lines.append("Execution plan:")
    for entry in plan.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 12: maintenance execution preview wrappers
# ------------------------------------------------------------


def get_cockpit_maintenance_execution_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """Delegate to :func:`runtime.system_dashboard.get_maintenance_execution_preview`."""
    try:
        from runtime.system_dashboard import get_maintenance_execution_preview

        return get_maintenance_execution_preview(action)
    except Exception:
        return {}


def format_cockpit_maintenance_execution_preview(action: Dict[str, Any]) -> str:
    """Human-readable execution simulation preview (plain text, no ANSI)."""
    try:
        preview = get_cockpit_maintenance_execution_preview(action)
    except Exception:
        return "Execution preview unavailable."

    lines = ["=== MAINTENANCE EXECUTION PREVIEW ===", ""]

    act = (preview.get("validation") or {}).get("action") or action
    lines.append(f"Action: {act.get('name', '?')}")
    lines.append(f"Description: {act.get('description', '?')}")

    lines.append("")
    env = preview.get("envelope") or {}
    lines.append(f"Envelope: {env.get('summary', '?')}")

    val = preview.get("validation") or {}
    lines.append(f"Allowed: {val.get('allowed', False)}")
    for r in val.get("reasons") or []:
        lines.append(f"  - {r}")

    lines.append("")
    plan = preview.get("execution_plan") or {}
    lines.append("Execution plan (initial):")
    for entry in plan.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    lines.append("")
    sim = preview.get("execution_simulation") or {}
    lines.append("Execution simulation (all steps):")
    for entry in sim.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    lines.append("")
    rb = preview.get("rollback_simulation") or {}
    lines.append("Rollback simulation:")
    for entry in rb.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    return "\n".join(lines)


# ------------------------------------------------------------
# Phase 13: real operation preview wrappers
# ------------------------------------------------------------


def get_cockpit_maintenance_operation_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """Delegate to :func:`runtime.system_dashboard.get_maintenance_operation_preview`."""
    try:
        from runtime.system_dashboard import get_maintenance_operation_preview

        return get_maintenance_operation_preview(action)
    except Exception:
        return {}


def format_cockpit_maintenance_operation_preview(action: Dict[str, Any]) -> str:
    """Human-readable real-operation preview (plain text, no ANSI)."""
    try:
        preview = get_cockpit_maintenance_operation_preview(action)
    except Exception:
        return "Operation preview unavailable."

    lines = ["=== MAINTENANCE OPERATION PREVIEW ===", ""]

    act = (preview.get("validation") or {}).get("action") or action
    lines.append(f"Action: {act.get('name', '?')}")
    lines.append(f"Description: {act.get('description', '?')}")

    lines.append("")
    env = preview.get("envelope") or {}
    lines.append(f"Envelope: {env.get('summary', '?')}")

    val = preview.get("validation") or {}
    lines.append(f"Allowed: {val.get('allowed', False)}")
    for r in val.get("reasons") or []:
        lines.append(f"  - {r}")

    lines.append("")
    sim = preview.get("execution_simulation") or {}
    lines.append("Simulated execution:")
    for entry in sim.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    lines.append("")
    srb = preview.get("rollback_simulation") or {}
    lines.append("Simulated rollback:")
    for entry in srb.get("plan") or []:
        lines.append(f"  [{entry.get('status', '?')}] {entry.get('step', '?')}")

    lines.append("")
    real = preview.get("real_operation") or {}
    lines.append(f"Real operation: performed={real.get('performed', False)}  result={real.get('result', '?')}")
    for s in real.get("steps") or []:
        lines.append(f"  [{s.get('status', '?')}] {s.get('step', '?')}")

    lines.append("")
    rrb = preview.get("real_rollback") or {}
    lines.append(f"Real rollback: rolled_back={rrb.get('rolled_back', False)}")
    lines.append(f"  {rrb.get('restored_state', '')}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 14: cockpit — action classification & autonomy eligibility
# ------------------------------------------------------------------

def get_cockpit_maintenance_action_classification(
    action: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        from runtime.system_dashboard import get_maintenance_action_classification

        return get_maintenance_action_classification(action)
    except Exception:
        return {}


def format_cockpit_maintenance_action_classification(
    action: Dict[str, Any],
) -> str:
    try:
        cls = get_cockpit_maintenance_action_classification(action)
    except Exception:
        return "Action classification unavailable."

    lines = [
        "=== MAINTENANCE ACTION CLASSIFICATION ===",
        "",
        f"Action: {action.get('name', '?')}",
        f"Class:  {cls.get('class', '?')}",
        f"Reason: {cls.get('reason', '?')}",
    ]
    return "\n".join(lines)


def get_cockpit_autonomy_eligibility_preview(
    action: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        from runtime.system_dashboard import get_autonomy_eligibility_preview

        return get_autonomy_eligibility_preview(action)
    except Exception:
        return {}


def format_cockpit_autonomy_eligibility_preview(
    action: Dict[str, Any],
) -> str:
    try:
        elig = get_cockpit_autonomy_eligibility_preview(action)
    except Exception:
        return "Autonomy eligibility unavailable."

    lines = [
        "=== AUTONOMY ELIGIBILITY PREVIEW ===",
        "",
        f"Action:   {action.get('name', '?')}",
        f"Class:    {elig.get('class', '?')}",
        f"Eligible: {elig.get('eligible', '?')}",
        "Reasons:",
    ]
    for r in elig.get("reasons") or []:
        lines.append(f"  - {r}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 15: cockpit — tier-1 autonomy framework
# ------------------------------------------------------------------

def get_cockpit_tier1_autonomy_preview(
    action: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        from runtime.system_dashboard import get_tier1_autonomy_preview

        return get_tier1_autonomy_preview(action)
    except Exception:
        return {}


def format_cockpit_tier1_autonomy_preview(
    action: Dict[str, Any],
) -> str:
    try:
        preview = get_cockpit_tier1_autonomy_preview(action)
    except Exception:
        return "Tier-1 autonomy preview unavailable."

    verdict = preview.get("verdict") or {}
    settings = preview.get("settings") or {}
    cls = preview.get("classification") or {}

    lines = [
        "=== TIER-1 AUTONOMY PREVIEW ===",
        "",
        f"Action:              {action.get('name', '?')}",
        f"Class:               {cls.get('class', '?')}",
        f"Autonomy enabled:    {settings.get('tier1_enabled', '?')}",
        f"Eligible:            {verdict.get('eligible', '?')}",
        f"Should auto-execute: {verdict.get('should_auto_execute', '?')}",
        "Reasons:",
    ]
    for r in verdict.get("reasons") or []:
        lines.append(f"  - {r}")

    return "\n".join(lines)


def get_cockpit_autonomy_settings() -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import get_autonomy_settings

        return get_autonomy_settings()
    except Exception:
        return {}


def set_cockpit_autonomy_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import set_autonomy_settings

        return set_autonomy_settings(settings)
    except Exception:
        return {}


# ------------------------------------------------------------------
# Phase 16: cockpit — tier-1 autonomy cycle
# ------------------------------------------------------------------

def get_cockpit_tier1_autonomy_cycle_preview(
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        from runtime.system_dashboard import get_tier1_autonomy_cycle_preview

        return get_tier1_autonomy_cycle_preview(actions)
    except Exception:
        return {}


def format_cockpit_tier1_autonomy_cycle_preview(
    actions: List[Dict[str, Any]],
) -> str:
    try:
        preview = get_cockpit_tier1_autonomy_cycle_preview(actions)
    except Exception:
        return "Tier-1 autonomy cycle preview unavailable."

    settings = preview.get("settings") or {}
    lines = [
        "=== TIER-1 AUTONOMY CYCLE PREVIEW ===",
        "",
        f"Autonomy enabled: {settings.get('tier1_enabled', '?')}",
        f"Would execute:    {preview.get('would_execute', [])}",
        f"Would skip:       {preview.get('would_skip', [])}",
        "",
    ]
    for entry in preview.get("actions") or []:
        a = entry.get("action") or {}
        v = entry.get("verdict") or {}
        c = entry.get("classification") or {}
        lines.append(f"  {a.get('name', '?')}:")
        lines.append(f"    class={c.get('class', '?')}  "
                      f"eligible={v.get('eligible', '?')}  "
                      f"auto_execute={v.get('should_auto_execute', '?')}")

    return "\n".join(lines)


def run_cockpit_tier1_autonomy_cycle(
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Thin cockpit wrapper — runs a tier-1 autonomy cycle explicitly."""
    try:
        from runtime.maintenance_actions import run_tier1_autonomy_cycle
        from runtime.system_dashboard import get_maintenance_envelope_summary

        envelope = get_maintenance_envelope_summary()
        return run_tier1_autonomy_cycle(actions, envelope)
    except Exception:
        return {"autonomy_enabled": False, "executed": [], "skipped": []}


# ------------------------------------------------------------------
# Phase 17: cockpit — autonomy loop
# ------------------------------------------------------------------

def get_cockpit_autonomy_loop_preview(
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        from runtime.system_dashboard import get_autonomy_loop_preview

        return get_autonomy_loop_preview(actions)
    except Exception:
        return {}


def format_cockpit_autonomy_loop_preview(
    actions: List[Dict[str, Any]],
) -> str:
    try:
        report = get_cockpit_autonomy_loop_preview(actions)
    except Exception:
        return "Autonomy loop preview unavailable."

    lines = [
        "=== AUTONOMY LOOP PREVIEW ===",
        "",
        f"Autonomy enabled: {report.get('autonomy_enabled', '?')}",
        f"Envelope:         {report.get('envelope_summary', '?')}",
        f"Would execute:    {report.get('would_execute', [])}",
        f"Would skip:       {report.get('would_skip', [])}",
        "",
    ]
    for entry in report.get("actions") or []:
        a = entry.get("action") or {}
        c = entry.get("classification") or {}
        e = entry.get("eligibility") or {}
        v = entry.get("verdict") or {}
        lines.append(f"  {a.get('name', '?')}:")
        lines.append(f"    class={c.get('class', '?')}  "
                      f"eligible={e.get('eligible', '?')}  "
                      f"auto_execute={v.get('should_auto_execute', '?')}")
        for r in v.get("reasons") or []:
            lines.append(f"      - {r}")

    return "\n".join(lines)


def run_cockpit_autonomy_loop(
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Thin cockpit wrapper — runs the autonomy loop explicitly."""
    try:
        from runtime.maintenance_actions import run_autonomy_loop
        from runtime.system_dashboard import get_maintenance_envelope_summary

        envelope = get_maintenance_envelope_summary()
        return run_autonomy_loop(actions, envelope)
    except Exception:
        return {"autonomy_enabled": False, "envelope_summary": "unknown",
                "actions": [], "would_execute": [], "would_skip": []}


# ------------------------------------------------------------------
# Phase 18: cockpit — active tier-1 autonomy state
# ------------------------------------------------------------------

def get_cockpit_active_tier1_autonomy_state() -> Optional[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_active_tier1_autonomy_state

        return get_active_tier1_autonomy_state()
    except Exception:
        return None


def format_cockpit_active_tier1_autonomy_state() -> str:
    try:
        state = get_cockpit_active_tier1_autonomy_state()
    except Exception:
        return "Active Tier-1 autonomy state unavailable."

    if not state:
        return "Active Tier-1 autonomy: no cycle has fired yet."

    exec_names = [e.get("action", {}).get("name", "?") for e in state.get("executed") or []]
    skip_names = [s.get("action", {}).get("name", "?") for s in state.get("skipped") or []]

    lines = [
        "=== ACTIVE TIER-1 AUTONOMY STATE ===",
        "",
        f"Autonomy enabled: {state.get('autonomy_enabled', '?')}",
        f"Envelope:         {state.get('envelope_summary', '?')}",
        f"Executed:         {exec_names}",
        f"Skipped:          {skip_names}",
    ]

    for s in state.get("skipped") or []:
        v = s.get("verdict") or {}
        lines.append(f"  {s.get('action', {}).get('name', '?')}:")
        for r in v.get("reasons") or []:
            lines.append(f"    - {r}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 19: cockpit — tier-1 action registry
# ------------------------------------------------------------------

def get_cockpit_tier1_action_registry() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier1_action_registry

        return get_tier1_action_registry()
    except Exception:
        return []


def format_cockpit_tier1_action_registry() -> str:
    try:
        entries = get_cockpit_tier1_action_registry()
    except Exception:
        return "Tier-1 action registry unavailable."

    if not entries:
        return "Tier-1 action registry: empty."

    lines = [
        "=== TIER-1 ACTION REGISTRY ===",
        "",
        f"Registered actions: {len(entries)}",
        "",
    ]
    for entry in entries:
        a = entry.get("action") or {}
        c = entry.get("classification") or {}
        steps = a.get("steps") or []
        lines.append(f"  {a.get('name', '?')}:")
        lines.append(f"    steps: {', '.join(steps)}")
        lines.append(f"    class: {c.get('class', '?')}  ({c.get('reason', '')})")

    return "\n".join(lines)


def register_cockpit_tier1_action(action: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import register_tier1_action

        return register_tier1_action(action)
    except Exception:
        return {"registered": False, "reason": "unavailable", "action": action}


def clear_cockpit_tier1_action_registry() -> None:
    try:
        from runtime.maintenance_actions import clear_tier1_action_registry

        clear_tier1_action_registry()
    except Exception:
        pass


# ------------------------------------------------------------------
# Phase 20: cockpit — tier-1 promotion & demotion
# ------------------------------------------------------------------

def promote_cockpit_action_to_tier1(action: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import promote_action_to_tier1

        return promote_action_to_tier1(action)
    except Exception:
        return {"promoted": False, "reason": "unavailable", "action": action}


def demote_cockpit_action_from_tier1(name: str) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import demote_action_from_tier1

        return demote_action_from_tier1(name)
    except Exception:
        return {"demoted": False, "reason": "unavailable", "name": name}


def get_cockpit_tier1_promotion_events() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier1_promotion_events

        return get_tier1_promotion_events()
    except Exception:
        return []


def get_cockpit_tier1_demotion_events() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier1_demotion_events

        return get_tier1_demotion_events()
    except Exception:
        return []


def format_cockpit_tier1_promotion_events() -> str:
    try:
        events = get_cockpit_tier1_promotion_events()
    except Exception:
        return "Promotion events unavailable."

    if not events:
        return "Tier-1 promotion events: none."

    lines = ["=== TIER-1 PROMOTION EVENTS ===", ""]
    for evt in events[-10:]:
        lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                      f"{evt.get('reason', '?')}")
    return "\n".join(lines)


def format_cockpit_tier1_demotion_events() -> str:
    try:
        events = get_cockpit_tier1_demotion_events()
    except Exception:
        return "Demotion events unavailable."

    if not events:
        return "Tier-1 demotion events: none."

    lines = ["=== TIER-1 DEMOTION EVENTS ===", ""]
    for evt in events[-10:]:
        lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                      f"{evt.get('reason', '?')}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 21: cockpit — tier-2 registry + supervised execution
# ------------------------------------------------------------------

def register_cockpit_tier2_action(action: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import register_tier2_action

        return register_tier2_action(action)
    except Exception:
        return {"registered": False, "reason": "unavailable", "action": action}


def queue_cockpit_tier2_action_for_review(name: str) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import queue_tier2_action_for_review

        return queue_tier2_action_for_review(name)
    except Exception:
        return {"queued": False, "reason": "unavailable", "name": name}


def execute_cockpit_tier2_action(name: str) -> Dict[str, Any]:
    """Operator-initiated Tier-2 execution with current envelope."""
    try:
        from runtime.maintenance_actions import execute_tier2_action
        from runtime.system_dashboard import get_maintenance_envelope_summary

        envelope = get_maintenance_envelope_summary()
        return execute_tier2_action(name, envelope)
    except Exception:
        return {"executed": False, "reason": "unavailable", "action": None, "result": None}


def get_cockpit_tier2_action_registry() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier2_action_registry

        return get_tier2_action_registry()
    except Exception:
        return []


def get_cockpit_tier2_pending_queue() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier2_pending_queue

        return get_tier2_pending_queue()
    except Exception:
        return []


def format_cockpit_tier2_action_registry() -> str:
    try:
        entries = get_cockpit_tier2_action_registry()
    except Exception:
        return "Tier-2 action registry unavailable."

    if not entries:
        return "Tier-2 action registry: empty."

    lines = ["=== TIER-2 ACTION REGISTRY ===", "", f"Registered actions: {len(entries)}", ""]
    for entry in entries:
        a = entry.get("action") or {}
        c = entry.get("classification") or {}
        steps = a.get("steps") or []
        lines.append(f"  {a.get('name', '?')}:")
        lines.append(f"    steps: {', '.join(steps)}")
        lines.append(f"    class: {c.get('class', '?')}  ({c.get('reason', '')})")
    return "\n".join(lines)


def format_cockpit_tier2_pending_queue() -> str:
    try:
        queue = get_cockpit_tier2_pending_queue()
    except Exception:
        return "Tier-2 pending queue unavailable."

    if not queue:
        return "Tier-2 pending queue: empty."

    lines = ["=== TIER-2 PENDING QUEUE ===", "", f"Pending actions: {len(queue)}", ""]
    for a in queue:
        steps = a.get("steps") or []
        lines.append(f"  {a.get('name', '?')} ({len(steps)} steps)")
    return "\n".join(lines)


def format_cockpit_tier2_execution_events() -> str:
    try:
        from runtime.system_dashboard import get_tier2_execution_events

        events = get_tier2_execution_events()
    except Exception:
        return "Tier-2 execution events unavailable."

    if not events:
        return "Tier-2 execution events: none."

    lines = ["=== TIER-2 EXECUTION EVENTS ===", ""]
    for evt in events[-10:]:
        lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                      f"{evt.get('reason', '?')}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 22: cockpit — tier-2 promotion candidates
# ------------------------------------------------------------------

def get_cockpit_tier2_promotion_candidates() -> List[Dict[str, Any]]:
    try:
        from runtime.system_dashboard import get_tier2_promotion_candidates

        return get_tier2_promotion_candidates()
    except Exception:
        return []


def format_cockpit_tier2_promotion_candidates() -> str:
    try:
        candidates = get_cockpit_tier2_promotion_candidates()
    except Exception:
        return "Tier-2 promotion candidates unavailable."

    if not candidates:
        return "Tier-2 promotion candidates: none registered."

    lines = ["=== TIER-2 PROMOTION CANDIDATES ===", ""]
    for c in candidates:
        lines.append(f"  {c.get('name', '?')}:")
        lines.append(f"    runs: {c.get('total_runs', 0)}  "
                      f"(ok={c.get('successful_runs', 0)}  "
                      f"fail={c.get('failed_runs', 0)})")
        lines.append(f"    last result:    {c.get('last_result', '?')}")
        lines.append(f"    recommendation: {c.get('recommendation', '?')}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 23: cockpit — tier-2 lifecycle controls
# ------------------------------------------------------------------

def retire_cockpit_tier2_action(name: str) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import retire_tier2_action

        return retire_tier2_action(name)
    except Exception:
        return {"retired": False, "reason": "unavailable", "name": name}


def reset_cockpit_tier2_action_history(name: str) -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import reset_tier2_action_history

        return reset_tier2_action_history(name)
    except Exception:
        return {"reset": False, "reason": "unavailable", "name": name}


def reset_cockpit_all_tier2_history() -> Dict[str, Any]:
    try:
        from runtime.maintenance_actions import reset_all_tier2_history

        return reset_all_tier2_history()
    except Exception:
        return {"reset": False, "reason": "unavailable"}


def recompute_cockpit_tier2_promotion_candidates() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import recompute_tier2_promotion_candidates

        return recompute_tier2_promotion_candidates()
    except Exception:
        return []


def format_cockpit_tier2_lifecycle_status() -> str:
    try:
        from runtime.system_dashboard import get_tier2_lifecycle_status

        lc = get_tier2_lifecycle_status()
    except Exception:
        return "Tier-2 lifecycle status unavailable."

    lines = [
        "=== TIER-2 LIFECYCLE STATUS ===",
        "",
        f"Registry:       {lc.get('registry_count', 0)} actions",
        f"Pending queue:  {lc.get('pending_count', 0)} actions",
        f"Exec events:    {lc.get('event_count', 0)}",
        f"Lifecycle ops:  {lc.get('lifecycle_log_count', 0)}",
    ]
    last_op = lc.get("last_operation")
    if last_op:
        lines.append("")
        lines.append(f"Last operation: [{last_op.get('result', '?')}] "
                      f"{last_op.get('operation', '?')} "
                      f"{last_op.get('action_name', '?')}")
        lines.append(f"  {last_op.get('reason', '?')}")
    else:
        lines.append("")
        lines.append("Last operation: none")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 24: unified autonomy governance panel
# ------------------------------------------------------------------

def format_cockpit_autonomy_governance_panel() -> str:
    """
    Single entry point that consolidates all autonomy-related state
    into a human-readable governance panel.

    Read-only — no execution, no mutation.
    """
    lines: List[str] = [
        "=" * 56,
        "       AUTONOMY GOVERNANCE PANEL",
        "=" * 56,
    ]

    # -- envelope + settings --
    try:
        from runtime.maintenance_actions import get_autonomy_settings
        from runtime.system_dashboard import get_maintenance_envelope_summary

        envelope = get_maintenance_envelope_summary()
        settings = get_autonomy_settings()
    except Exception:
        envelope = {}
        settings = {}

    lines.append("")
    lines.append("--- Envelope & Settings ---")
    lines.append(f"  Envelope summary:  {envelope.get('summary', '?')}")
    for r in (envelope.get("reasons") or [])[:5]:
        lines.append(f"    - {r}")
    lines.append(f"  Tier-1 autonomy:   {'ENABLED' if settings.get('tier1_enabled') else 'DISABLED'}")

    # -- tier-1 autonomy --
    lines.append("")
    lines.append("--- Tier-1 Autonomy ---")

    try:
        state = get_cockpit_active_tier1_autonomy_state()
    except Exception:
        state = None

    if state:
        exec_names = [e.get("action", {}).get("name", "?")
                       for e in state.get("executed") or []]
        skip_names = [s.get("action", {}).get("name", "?")
                       for s in state.get("skipped") or []]
        lines.append(f"  Last cycle: executed={exec_names}  skipped={skip_names}")
    else:
        lines.append("  Last cycle: no autonomy cycle has fired yet")

    try:
        t1_reg = get_cockpit_tier1_action_registry()
    except Exception:
        t1_reg = []

    lines.append(f"  Registered actions ({len(t1_reg)}):")
    for entry in t1_reg:
        a = entry.get("action") or {}
        steps = a.get("steps") or []
        lines.append(f"    {a.get('name', '?')} ({len(steps)} steps)")

    try:
        from runtime.system_dashboard import (
            get_tier1_promotion_events,
            get_tier1_demotion_events,
        )
        promos = get_tier1_promotion_events()
        demos = get_tier1_demotion_events()
    except Exception:
        promos = []
        demos = []

    recent_pd = (promos + demos)[-5:]
    if recent_pd:
        lines.append(f"  Recent promotion/demotion ({len(promos)}p / {len(demos)}d):")
        for evt in recent_pd:
            lines.append(f"    [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                          f"{evt.get('reason', '?')}")
    else:
        lines.append("  Promotion/demotion events: none")

    # -- tier-2 supervised actions --
    lines.append("")
    lines.append("--- Tier-2 Supervised Actions ---")

    try:
        t2_reg = get_cockpit_tier2_action_registry()
    except Exception:
        t2_reg = []

    lines.append(f"  Registered actions ({len(t2_reg)}):")
    for entry in t2_reg:
        a = entry.get("action") or {}
        c = entry.get("classification") or {}
        steps = a.get("steps") or []
        lines.append(f"    {a.get('name', '?')} ({len(steps)} steps)  "
                      f"class={c.get('class', '?')}")

    try:
        t2_q = get_cockpit_tier2_pending_queue()
    except Exception:
        t2_q = []

    lines.append(f"  Pending queue ({len(t2_q)}):")
    if t2_q:
        for a in t2_q:
            lines.append(f"    {a.get('name', '?')}")
    else:
        lines.append("    (empty)")

    try:
        from runtime.system_dashboard import get_tier2_execution_events

        t2_evts = get_tier2_execution_events()
    except Exception:
        t2_evts = []

    if t2_evts:
        lines.append(f"  Recent execution events (last 5 of {len(t2_evts)}):")
        for evt in t2_evts[-5:]:
            lines.append(f"    [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                          f"{evt.get('reason', '?')}")
    else:
        lines.append("  Execution events: none")

    try:
        cands = get_cockpit_tier2_promotion_candidates()
    except Exception:
        cands = []

    if cands:
        lines.append(f"  Promotion candidates ({len(cands)}):")
        for c in cands:
            lines.append(f"    {c.get('name', '?')}:  "
                          f"runs={c.get('total_runs', 0)} "
                          f"(ok={c.get('successful_runs', 0)} "
                          f"fail={c.get('failed_runs', 0)})  "
                          f"-> {c.get('recommendation', '?')}")
    else:
        lines.append("  Promotion candidates: none")

    try:
        from runtime.system_dashboard import get_tier2_lifecycle_status

        lc = get_tier2_lifecycle_status()
    except Exception:
        lc = {}

    if lc:
        lines.append(f"  Lifecycle: "
                      f"registry={lc.get('registry_count', 0)}  "
                      f"pending={lc.get('pending_count', 0)}  "
                      f"events={lc.get('event_count', 0)}  "
                      f"ops={lc.get('lifecycle_log_count', 0)}")
        last_op = lc.get("last_operation")
        if last_op:
            lines.append(f"    last op: [{last_op.get('result', '?')}] "
                          f"{last_op.get('operation', '?')} "
                          f"{last_op.get('action_name', '?')}: "
                          f"{last_op.get('reason', '?')}")

    lines.append("")
    lines.append("=" * 56)

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 25: high-level cockpit commands
# ------------------------------------------------------------------

def cockpit_show_tier1_overview() -> str:
    """Consolidated Tier-1 overview: registry, last cycle, recent events."""
    lines: List[str] = ["=== TIER-1 OVERVIEW ===", ""]

    try:
        t1_reg = get_cockpit_tier1_action_registry()
    except Exception:
        t1_reg = []

    lines.append(f"Registered actions ({len(t1_reg)}):")
    for entry in t1_reg:
        a = entry.get("action") or {}
        steps = a.get("steps") or []
        lines.append(f"  {a.get('name', '?')} ({len(steps)} steps)")

    try:
        state = get_cockpit_active_tier1_autonomy_state()
    except Exception:
        state = None

    lines.append("")
    if state:
        exec_names = [e.get("action", {}).get("name", "?")
                       for e in state.get("executed") or []]
        skip_names = [s.get("action", {}).get("name", "?")
                       for s in state.get("skipped") or []]
        lines.append(f"Last autonomy cycle:")
        lines.append(f"  enabled={state.get('autonomy_enabled', '?')}  "
                      f"envelope={state.get('envelope_summary', '?')}")
        lines.append(f"  executed: {exec_names}")
        lines.append(f"  skipped:  {skip_names}")
    else:
        lines.append("Last autonomy cycle: none")

    try:
        from runtime.system_dashboard import (
            get_tier1_promotion_events,
            get_tier1_demotion_events,
        )
        promos = get_tier1_promotion_events()
        demos = get_tier1_demotion_events()
    except Exception:
        promos = []
        demos = []

    recent = (promos + demos)[-5:]
    lines.append("")
    if recent:
        lines.append(f"Recent promotion/demotion ({len(promos)}p / {len(demos)}d):")
        for evt in recent:
            lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                          f"{evt.get('reason', '?')}")
    else:
        lines.append("Promotion/demotion events: none")

    return "\n".join(lines)


def cockpit_promote_strong_tier2_candidates() -> str:
    """Promote all Tier-2 actions with 'strong_candidate' recommendation."""
    try:
        from runtime.maintenance_actions import (
            get_tier2_promotion_candidates,
            promote_action_to_tier1,
            define_maintenance_action,
            get_registered_tier2_actions,
        )
    except Exception:
        return "Promotion unavailable: maintenance_actions module not loaded."

    candidates = get_tier2_promotion_candidates()
    strong = [c for c in candidates if c.get("recommendation") == "strong_candidate"]

    if not strong:
        return "No strong candidates to promote."

    t2_actions = {a["name"]: a for a in get_registered_tier2_actions()}

    lines: List[str] = [f"Promoting {len(strong)} strong candidate(s):", ""]
    for c in strong:
        name = c["name"]
        action = t2_actions.get(name)
        if not action:
            lines.append(f"  {name}: SKIP (not found in tier2 registry)")
            continue

        # Tier-2 actions classify as tier2, not tier1, so promotion via
        # promote_action_to_tier1 will fail classification.  We need to
        # re-define a tier1-compatible version (fewer steps).  For now,
        # we attempt promotion and report the result honestly.
        result = promote_action_to_tier1(action)
        if result["promoted"]:
            lines.append(f"  {name}: PROMOTED")
        else:
            lines.append(f"  {name}: FAILED ({result['reason']})")

    return "\n".join(lines)


def cockpit_queue_all_tier2_actions() -> str:
    """Queue all registered Tier-2 actions for review, skipping already-queued."""
    try:
        from runtime.maintenance_actions import (
            get_registered_tier2_actions,
            queue_tier2_action_for_review,
        )
    except Exception:
        return "Queue unavailable."

    actions = get_registered_tier2_actions()
    if not actions:
        return "No Tier-2 actions registered."

    lines: List[str] = [f"Queueing {len(actions)} Tier-2 action(s):", ""]
    for a in actions:
        name = a.get("name", "?")
        result = queue_tier2_action_for_review(name)
        if result["queued"]:
            lines.append(f"  {name}: queued")
        else:
            lines.append(f"  {name}: skipped ({result['reason']})")

    return "\n".join(lines)


def cockpit_clear_tier2_pending_queue() -> str:
    """Remove all actions from the Tier-2 pending queue."""
    try:
        from runtime.maintenance_actions import _TIER2_PENDING_QUEUE
    except Exception:
        return "Clear unavailable."

    count = len(_TIER2_PENDING_QUEUE)
    _TIER2_PENDING_QUEUE.clear()
    return f"Tier-2 pending queue cleared ({count} action(s) removed)."


def cockpit_reset_tier2_action(name: str) -> str:
    """Reset history and remove from pending queue for a Tier-2 action."""
    try:
        from runtime.maintenance_actions import (
            reset_tier2_action_history,
            _TIER2_PENDING_QUEUE,
        )
    except Exception:
        return f"Reset unavailable for '{name}'."

    lines: List[str] = [f"Resetting Tier-2 action '{name}':", ""]

    hist = reset_tier2_action_history(name)
    lines.append(f"  History: {'cleared' if hist['reset'] else hist['reason']}")

    pq_idx = next(
        (i for i, a in enumerate(_TIER2_PENDING_QUEUE) if a.get("name") == name),
        None,
    )
    if pq_idx is not None:
        _TIER2_PENDING_QUEUE.pop(pq_idx)
        lines.append("  Pending queue: removed")
    else:
        lines.append("  Pending queue: not present")

    return "\n".join(lines)


def cockpit_show_envelope_and_settings() -> str:
    """Display current envelope summary and autonomy settings."""
    try:
        from runtime.maintenance_actions import get_autonomy_settings
        from runtime.system_dashboard import get_maintenance_envelope_summary

        envelope = get_maintenance_envelope_summary()
        settings = get_autonomy_settings()
    except Exception:
        return "Envelope/settings unavailable."

    lines: List[str] = ["=== ENVELOPE & SETTINGS ===", ""]
    summary = envelope.get("summary", "?")
    lines.append(f"Envelope: {summary}")
    for r in (envelope.get("reasons") or [])[:5]:
        lines.append(f"  - {r}")

    lines.append("")
    lines.append(f"Tier-1 autonomy: {'ENABLED' if settings.get('tier1_enabled') else 'DISABLED'}")

    if summary != "pass":
        lines.append("")
        lines.append("WARNING: envelope is not 'pass' -- no maintenance actions will execute.")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 26: cockpit command aliases
# ------------------------------------------------------------------

# Tier-1
def t1() -> str:
    """Show Tier-1 overview."""
    return cockpit_show_tier1_overview()

def t1_actions() -> List[Dict[str, Any]]:
    """List registered Tier-1 actions."""
    return get_cockpit_tier1_action_registry()

def t1_events() -> List[Dict[str, Any]]:
    """List recent Tier-1 promotion events."""
    return get_cockpit_tier1_promotion_events()

# Tier-2
def t2() -> str:
    """Show Tier-2 action registry."""
    return format_cockpit_tier2_action_registry()

def t2q() -> str:
    """Show Tier-2 pending queue."""
    return format_cockpit_tier2_pending_queue()

def t2_execs() -> str:
    """Show Tier-2 execution events."""
    return format_cockpit_tier2_execution_events()

def t2_promos() -> str:
    """Show Tier-2 promotion candidates."""
    return format_cockpit_tier2_promotion_candidates()

def t2_life() -> str:
    """Show Tier-2 lifecycle status."""
    return format_cockpit_tier2_lifecycle_status()

# Workflow
def queue_all() -> str:
    """Queue all registered Tier-2 actions for review."""
    return cockpit_queue_all_tier2_actions()

def clear_queue() -> str:
    """Clear the Tier-2 pending queue."""
    return cockpit_clear_tier2_pending_queue()

def promote_strong() -> str:
    """Promote all strong Tier-2 candidates to Tier-1."""
    return cockpit_promote_strong_tier2_candidates()

def reset_t2(name: str) -> str:
    """Reset a Tier-2 action's history and pending status."""
    return cockpit_reset_tier2_action(name)

# Envelope & settings
def env() -> str:
    """Show envelope summary and autonomy settings."""
    return cockpit_show_envelope_and_settings()

def panel() -> str:
    """Show the unified Autonomy Governance Panel."""
    return format_cockpit_autonomy_governance_panel()


# ------------------------------------------------------------------
# Phase 27: runtime tuning controls
# ------------------------------------------------------------------

def show_settings() -> str:
    """Pretty-print all runtime settings."""
    from runtime.system_settings import get_system_settings

    ss = get_system_settings()
    lines = ["Runtime settings:"]
    for k, v in ss.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def set_cadence(seconds: int) -> str:
    """Adjust the Tier-1 autonomy cadence (in seconds)."""
    from runtime.system_settings import set_setting

    result = set_setting("tier1_cadence_seconds", seconds)
    if result["updated"]:
        return f"Tier-1 cadence updated to {seconds}s."
    return f"Cadence not updated: {result['reason']}"


def set_promotion_threshold(n: int) -> str:
    """Adjust the Tier-2 promotion success threshold."""
    from runtime.system_settings import set_setting

    result = set_setting("tier2_promotion_threshold", n)
    if result["updated"]:
        return f"Tier-2 promotion threshold updated to {n}."
    return f"Threshold not updated: {result['reason']}"


# Aliases
def cadence(n: int) -> str:
    """Alias for set_cadence."""
    return set_cadence(n)


def promo_thresh(n: int) -> str:
    """Alias for set_promotion_threshold."""
    return set_promotion_threshold(n)


def settings() -> str:
    """Alias for show_settings."""
    return show_settings()


# ------------------------------------------------------------------
# Phase 28: autonomy cadence visualization
# ------------------------------------------------------------------

def format_cockpit_tier1_cycle_history(limit: int = 20) -> str:
    """Pretty-print recent Tier-1 autonomy cycle history."""
    from runtime.autonomy_cycle_log import get_tier1_cycle_log

    entries = get_tier1_cycle_log(limit)
    if not entries:
        return "No Tier-1 autonomy cycles recorded yet."

    lines = [f"Tier-1 cycle history (last {len(entries)}):"]
    for e in entries:
        ts = e.get("timestamp", 0)
        lines.append(f"  t={ts:.1f}  result={e.get('result', '?')}  "
                      f"envelope={e.get('envelope', '?')}")
    return "\n".join(lines)


def format_cockpit_tier1_next_cycle_eta() -> str:
    """Show iterations remaining until the next Tier-1 autonomy cycle."""
    from runtime.runtime_loop_controller import get_cycles_until_next_autonomy

    remaining = get_cycles_until_next_autonomy()
    return f"Next Tier-1 autonomy cycle in {remaining} loop iteration(s)."


# Aliases
def t1_cycles() -> str:
    """Alias for format_cockpit_tier1_cycle_history."""
    return format_cockpit_tier1_cycle_history()


def t1_eta() -> str:
    """Alias for format_cockpit_tier1_next_cycle_eta."""
    return format_cockpit_tier1_next_cycle_eta()


# ------------------------------------------------------------------
# Phase 29: autonomy drift visualization
# ------------------------------------------------------------------

def format_cockpit_autonomy_drift() -> str:
    """Pretty-print the autonomy drift report."""
    from runtime.autonomy_cycle_log import get_autonomy_drift_report

    dr = get_autonomy_drift_report()
    sr = dr.get("skip_rate") or {}
    es = dr.get("envelope_stability") or {}
    cd = dr.get("cadence_drift") or {}

    lines = ["Autonomy drift report:"]
    lines.append(f"  skip rate: {sr.get('skip_rate', 0):.1%}  "
                  f"({sr.get('skip_count', 0)}/{sr.get('total_count', 0)})  "
                  f"severity={sr.get('severity', '?')}")
    lines.append(f"  envelope stability: {es.get('fail_rate', 0):.1%} non-pass  "
                  f"({es.get('fail_count', 0)}/{es.get('total_count', 0)})  "
                  f"severity={es.get('severity', '?')}")
    lines.append(f"  cadence drift: avg_delta={cd.get('avg_delta', 0)}s  "
                  f"expected={cd.get('expected', '?')}s  "
                  f"drift={cd.get('drift', 0)}s  "
                  f"severity={cd.get('severity', '?')}")
    return "\n".join(lines)


def t1_drift() -> str:
    """Alias for format_cockpit_autonomy_drift."""
    return format_cockpit_autonomy_drift()


# ------------------------------------------------------------------
# Phase 30: Tier-3 proposal cockpit
# ------------------------------------------------------------------

def create_proposal(title: str, rationale: str) -> str:
    """Create a Tier-3 proposal with the current drift report as evidence."""
    from runtime.autonomy_cycle_log import get_autonomy_drift_report
    from runtime.tier3_proposals import create_tier3_proposal

    evidence = get_autonomy_drift_report()
    p = create_tier3_proposal(title, rationale, evidence)
    return (
        f"Proposal created:\n"
        f"  id: {p['id']}\n"
        f"  title: {p['title']}\n"
        f"  status: {p['status']}"
    )


def list_proposals() -> str:
    """Pretty-print all Tier-3 proposals."""
    from runtime.tier3_proposals import get_tier3_proposals

    proposals = get_tier3_proposals()
    if not proposals:
        return "No Tier-3 proposals."

    lines = [f"Tier-3 proposals ({len(proposals)}):"]
    for p in proposals:
        pid = p.get("id", "?")[:8]
        lines.append(
            f"  [{p.get('status', '?')}] {pid}..  "
            f"{p.get('title', '?')}  "
            f"-- {p.get('rationale', '')}"
        )
    return "\n".join(lines)


def set_proposal_status(proposal_id: str, status: str) -> str:
    """Update a Tier-3 proposal's status (pending/approved/rejected)."""
    from runtime.tier3_proposals import update_tier3_proposal_status

    result = update_tier3_proposal_status(proposal_id, status)
    if result.get("updated"):
        return (
            f"Proposal {proposal_id[:8]}.. status: "
            f"{result['old_status']} -> {result['new_status']}"
        )
    return f"Not updated: {result.get('reason', 'unknown')}"


# Aliases
def t3_new(title: str, rationale: str) -> str:
    """Alias for create_proposal."""
    return create_proposal(title, rationale)


def t3_list() -> str:
    """Alias for list_proposals."""
    return list_proposals()


def t3_set(proposal_id: str, status: str) -> str:
    """Alias for set_proposal_status."""
    return set_proposal_status(proposal_id, status)


# ------------------------------------------------------------------
# Phase 31: Tier-3 execution harness cockpit
# ------------------------------------------------------------------

def _find_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    from runtime.tier3_proposals import get_tier3_proposals

    for p in get_tier3_proposals():
        if p["id"] == proposal_id:
            return p
    return None


def preview_proposal(proposal_id: str) -> str:
    """Show a non-executable preview of a Tier-3 proposal."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    from runtime.tier3_execution import sandbox_preview

    pv = sandbox_preview(p)
    lines = [
        f"Proposal preview ({pv['proposal_id'][:8]}..):",
        f"  {pv['preview']}",
        f"  rationale: {pv['rationale']}",
    ]
    ev = pv.get("evidence") or {}
    if ev:
        lines.append(f"  evidence keys: {sorted(ev.keys())}")
    return "\n".join(lines)


def run_proposal(proposal_id: str) -> str:
    """Validate and execute a Tier-3 proposal through the harness."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    from runtime.tier3_execution import (
        validate_proposal_for_execution,
        execute_tier3_proposal,
    )

    val = validate_proposal_for_execution(p)
    if not val["valid"]:
        return f"Proposal {proposal_id[:8]}.. blocked: {val['reason']}"

    result = execute_tier3_proposal(p)
    return (
        f"Proposal {proposal_id[:8]}.. executed:\n"
        f"  timestamp: {result['timestamp']:.1f}\n"
        f"  note: {result['note']}"
    )


# Aliases
def t3_preview(proposal_id: str) -> str:
    """Alias for preview_proposal."""
    return preview_proposal(proposal_id)


def t3_run(proposal_id: str) -> str:
    """Alias for run_proposal."""
    return run_proposal(proposal_id)


# ------------------------------------------------------------------
# Phase 32: Tier-3 action definitions cockpit
# ------------------------------------------------------------------

def list_action_types() -> str:
    """Pretty-print all Tier-3 action types."""
    from runtime.tier3_actions import get_tier3_action_types

    types = get_tier3_action_types()
    if not types:
        return "No Tier-3 action types defined."

    lines = [f"Tier-3 action types ({len(types)}):"]
    for name, spec in types.items():
        rev = "reversible" if spec.get("reversible") else "irreversible"
        fields = ", ".join(spec.get("required_fields", []))
        lines.append(f"  {name}: {spec.get('description', '?')} ({rev})")
        lines.append(f"    required: [{fields}]")
    return "\n".join(lines)


def create_typed_proposal(
    title: str,
    rationale: str,
    action_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a Tier-3 proposal with a validated action type and payload."""
    from runtime.autonomy_cycle_log import get_autonomy_drift_report
    from runtime.tier3_proposals import create_typed_tier3_proposal

    evidence = get_autonomy_drift_report()
    result = create_typed_tier3_proposal(
        title, rationale, action_type, payload, evidence
    )

    if result.get("error"):
        return f"Proposal not created: {result['reason']}"

    return (
        f"Typed proposal created:\n"
        f"  id: {result['id']}\n"
        f"  title: {result['title']}\n"
        f"  action_type: {result['action_type']}\n"
        f"  reversible: {result['reversible']}\n"
        f"  status: {result['status']}"
    )


def describe_proposal_action(proposal_id: str) -> str:
    """Describe what a typed proposal's action would do."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    at = p.get("action_type")
    if not at:
        return f"Proposal {proposal_id[:8]}.. has no action type (untyped)."

    from runtime.tier3_actions import describe_tier3_action

    return describe_tier3_action(at, p.get("payload", {}))


# Aliases
def t3_types() -> str:
    """Alias for list_action_types."""
    return list_action_types()


def t3_typed(
    title: str,
    rationale: str,
    action_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Alias for create_typed_proposal."""
    return create_typed_proposal(title, rationale, action_type, payload)


def t3_describe(proposal_id: str) -> str:
    """Alias for describe_proposal_action."""
    return describe_proposal_action(proposal_id)


# ------------------------------------------------------------------
# Phase 33: Tier-3 dispatcher cockpit
# ------------------------------------------------------------------

def t3_execute(proposal_id: str) -> str:
    """Validate, dispatch, and execute a typed Tier-3 proposal."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    from runtime.tier3_execution import (
        validate_proposal_for_execution,
        execute_tier3_proposal,
    )

    val = validate_proposal_for_execution(p)
    if not val["valid"]:
        return f"Proposal {proposal_id[:8]}.. blocked: {val['reason']}"

    result = execute_tier3_proposal(p)

    lines = [f"Proposal {proposal_id[:8]}.. executed:"]
    lines.append(f"  timestamp: {result['timestamp']:.1f}")

    dr = result.get("dispatch_result")
    if dr and dr.get("dispatched"):
        hr = dr.get("handler_result") or {}
        lines.append(f"  dispatched: {dr['action_type']}")
        applied = hr.get("applied", False)
        lines.append(f"  applied: {applied}")
        if applied:
            for k, v in hr.items():
                if k.startswith("old_") or k.startswith("new_") or k == "key":
                    lines.append(f"  {k}: {v}")
        if hr.get("stub"):
            lines.append(f"  stub: True (deferred)")
        if hr.get("reason") and not applied:
            lines.append(f"  reason: {hr['reason']}")
    elif dr and not dr.get("dispatched"):
        lines.append(f"  dispatch failed: {dr.get('reason', '?')}")
    else:
        lines.append(f"  note: {result.get('note', '?')}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 34: reversible ledger + history cockpit
# ------------------------------------------------------------------

def t3_history(limit: int = 10) -> str:
    """Show the Tier-3 reversible ledger."""
    from runtime.tier3_execution import get_tier3_reversible_ledger

    entries = get_tier3_reversible_ledger(limit)
    if not entries:
        return "No Tier-3 reversible ledger entries."

    lines = [f"Tier-3 reversible ledger (last {len(entries)}):"]
    for e in entries:
        rev = "reversible" if e.get("reversible") else "irreversible"
        pid = e.get("proposal_id", "?")[:8]
        lines.append(f"  {pid}..  {e.get('action_type', '?')}  "
                      f"({rev})  t={e.get('timestamp', 0):.1f}")
        old = e.get("old_values") or {}
        new = e.get("new_values") or {}
        if old:
            lines.append(f"    old: {old}")
        if new:
            lines.append(f"    new: {new}")
    return "\n".join(lines)


def t3_last() -> str:
    """Show the most recent Tier-3 execution."""
    from runtime.tier3_execution import get_tier3_execution_log

    log = get_tier3_execution_log()
    if not log:
        return "No Tier-3 executions recorded."

    e = log[-1]
    pid = e.get("proposal_id", "?")[:8]
    lines = [f"Last Tier-3 execution:"]
    lines.append(f"  proposal: {pid}..  {e.get('title', '?')}")
    lines.append(f"  timestamp: {e.get('timestamp', 0):.1f}")
    dr = e.get("dispatch_result") or {}
    if dr.get("dispatched"):
        hr = dr.get("handler_result") or {}
        lines.append(f"  action: {dr.get('action_type', '?')}")
        lines.append(f"  applied: {hr.get('applied', False)}")
    else:
        lines.append(f"  note: {e.get('note', '?')}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 35: migration cockpit
# ------------------------------------------------------------------

def t3_migration_status(migration_name: str) -> str:
    """Show the status of a specific Tier-3 migration."""
    from runtime.tier3_execution import get_tier3_migration_status

    entry = get_tier3_migration_status(migration_name)
    if entry is None:
        return f"Migration '{migration_name}' not found."

    lines = [f"Migration '{migration_name}':"]
    lines.append(f"  status: {entry.get('status', '?')}")
    lines.append(f"  steps executed: {entry.get('steps_executed', 0)}/{entry.get('total_steps', 0)}")
    lines.append(f"  succeeded: {entry.get('steps_succeeded', 0)}")
    lines.append(f"  failed: {entry.get('steps_failed', 0)}")
    if entry.get("failure_reason"):
        lines.append(f"  failure reason: {entry['failure_reason']}")
    return "\n".join(lines)


def t3_migrations(limit: int = 10) -> str:
    """List recent Tier-3 migrations."""
    from runtime.tier3_execution import get_tier3_migration_log

    entries = get_tier3_migration_log(limit)
    if not entries:
        return "No Tier-3 migrations recorded."

    lines = [f"Tier-3 migrations (last {len(entries)}):"]
    for m in entries:
        lines.append(
            f"  {m.get('migration_name', '?')}  "
            f"status={m.get('status', '?')}  "
            f"steps={m.get('steps_succeeded', 0)}/{m.get('total_steps', 0)}  "
            f"t={m.get('timestamp', 0):.1f}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 36: dry-run, diff, approval cockpit
# ------------------------------------------------------------------

def t3_dryrun(proposal_id: str) -> str:
    """Show dry-run results for a migration proposal."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    dr = p.get("dryrun")
    if dr is None:
        return f"Proposal {proposal_id[:8]}.. has no dry-run results."

    lines = [f"Dry-run for {proposal_id[:8]}.. ({dr.get('migration_name', '?')}):"]
    lines.append(f"  status: {dr.get('status', '?')}")
    lines.append(f"  steps evaluated: {dr.get('steps_evaluated', 0)}/{dr.get('total_steps', 0)}")

    for sd in dr.get("step_diffs") or []:
        idx = sd.get("index", "?")
        st = sd.get("step_type", "?")
        status = sd.get("status", "?")
        diff = sd.get("diff")
        reason = sd.get("reason", "")
        if status == "ok" and diff:
            lines.append(f"  [{idx}] {st}: {diff.get('before')} -> {diff.get('after')}")
        elif status == "ok":
            msg = sd.get("message", "")
            lines.append(f"  [{idx}] {st}: (note) {msg}")
        else:
            lines.append(f"  [{idx}] {st}: ERROR {reason}")

    return "\n".join(lines)


def t3_diff(proposal_id: str) -> str:
    """Show only the structural diff for a migration proposal."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    dr = p.get("dryrun")
    if dr is None:
        return f"Proposal {proposal_id[:8]}.. has no dry-run results."

    diffs = [sd for sd in (dr.get("step_diffs") or [])
             if sd.get("diff") is not None]

    if not diffs:
        return f"No structural diffs for {proposal_id[:8]}.."

    lines = [f"Structural diff for {proposal_id[:8]}..:"]
    for sd in diffs:
        d = sd["diff"]
        lines.append(f"  [{sd.get('index', '?')}] {sd.get('step_type', '?')}: "
                      f"{d.get('before')} -> {d.get('after')}")
    return "\n".join(lines)


def t3_pending_approvals() -> str:
    """List proposals awaiting operator approval."""
    from runtime.tier3_proposals import get_proposals_awaiting_approval

    pending = get_proposals_awaiting_approval()
    if not pending:
        return "No proposals awaiting approval."

    lines = [f"Proposals awaiting approval ({len(pending)}):"]
    for p in pending:
        pid = p.get("id", "?")[:8]
        name = (p.get("payload") or {}).get("migration_name", "")
        lines.append(f"  {pid}..  {p.get('title', '?')}  migration={name}")
    return "\n".join(lines)


def t3_approve(proposal_id: str) -> str:
    """Approve a migration proposal that passed dry-run."""
    p = _find_proposal(proposal_id)
    if p is None:
        return f"Proposal '{proposal_id}' not found."

    if p.get("status") == "invalid":
        return f"Proposal {proposal_id[:8]}.. is invalid (dry-run failed). Cannot approve."

    if p.get("status") != "awaiting_approval":
        return (f"Proposal {proposal_id[:8]}.. status is '{p.get('status')}', "
                f"must be 'awaiting_approval' to approve.")

    dr = p.get("dryrun") or {}
    if dr.get("status") != "pass":
        return f"Proposal {proposal_id[:8]}.. dry-run did not pass. Cannot approve."

    from runtime.tier3_proposals import update_tier3_proposal_status

    result = update_tier3_proposal_status(proposal_id, "approved")
    if result.get("updated"):
        return f"Proposal {proposal_id[:8]}.. approved and ready for execution."
    return f"Approval failed: {result.get('reason', 'unknown')}"


# ------------------------------------------------------------------
# Phase 37: execution plan cockpit
# ------------------------------------------------------------------

def t3_plan_create(
    name: str,
    description: str,
    proposal_ids: List[str],
    dependencies: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a Tier-3 execution plan."""
    from runtime.tier3_plans import create_plan

    result = create_plan(name, description, proposal_ids, dependencies)
    if result.get("error"):
        reasons = "\n  ".join(result.get("reasons", []))
        return f"Plan not created:\n  {reasons}"

    return (
        f"Plan created:\n"
        f"  plan_id: {result['plan_id']}\n"
        f"  name: {result['name']}\n"
        f"  proposals: {len(result['proposal_ids'])}\n"
        f"  execution order: {[pid[:8] + '..' for pid in result['execution_order']]}\n"
        f"  status: {result['status']}"
    )


def t3_plan(plan_id: str) -> str:
    """Show detailed plan status and per-proposal results."""
    from runtime.tier3_plans import get_plan

    plan = get_plan(plan_id)
    if plan is None:
        return f"Plan '{plan_id}' not found."

    lines = [f"Plan '{plan['name']}' ({plan_id[:8]}..):"]
    lines.append(f"  status: {plan['status']}")
    lines.append(f"  proposals: {len(plan['proposal_ids'])}")
    lines.append(f"  order: {[pid[:8] + '..' for pid in plan['execution_order']]}")

    pr = plan.get("proposal_results") or {}
    if pr:
        succeeded = sum(1 for r in pr.values() if r["status"] == "success")
        failed = sum(1 for r in pr.values() if r["status"] == "failed")
        skipped = sum(1 for r in pr.values() if r["status"] == "skipped")
        lines.append(f"  results: {succeeded} succeeded, {failed} failed, {skipped} skipped")
        for pid, r in pr.items():
            reason = f"  -- {r.get('reason', '')}" if r.get("reason") else ""
            lines.append(f"    {pid[:8]}..  {r['status']}{reason}")

    deps = plan.get("dependencies") or {}
    if deps:
        lines.append(f"  dependencies:")
        for pid, dep_list in deps.items():
            lines.append(f"    {pid[:8]}.. depends on {[d[:8] + '..' for d in dep_list]}")

    return "\n".join(lines)


def t3_plans() -> str:
    """List existing execution plans."""
    from runtime.tier3_plans import get_plans

    plans = get_plans()
    if not plans:
        return "No Tier-3 execution plans."

    lines = [f"Tier-3 execution plans ({len(plans)}):"]
    for p in plans:
        pr = p.get("proposal_results") or {}
        succeeded = sum(1 for r in pr.values() if r.get("status") == "success")
        total = len(p.get("proposal_ids", []))
        lines.append(
            f"  {p['plan_id'][:8]}..  {p['name']}  "
            f"status={p['status']}  "
            f"proposals={total}  "
            f"ok={succeeded}"
        )
    return "\n".join(lines)


def t3_plan_execute(plan_id: str) -> str:
    """Trigger execution of a Tier-3 plan."""
    from runtime.tier3_plans import execute_plan

    result = execute_plan(plan_id)
    if not result.get("executed"):
        return f"Plan execution blocked: {result.get('reason', '?')}"

    lines = [f"Plan {plan_id[:8]}.. execution {result['status']}:"]
    lines.append(f"  total: {result['total']}")
    lines.append(f"  succeeded: {result['succeeded']}")
    lines.append(f"  failed: {result['failed']}")
    lines.append(f"  skipped: {result['skipped']}")

    for pid, r in result.get("proposal_results", {}).items():
        reason = f"  -- {r.get('reason', '')}" if r.get("reason") else ""
        lines.append(f"    {pid[:8]}..  {r['status']}{reason}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 38: policy engine cockpit
# ------------------------------------------------------------------

def t3_policy_create(
    name: str,
    description: str,
    trigger_conditions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    enabled: bool = True,
) -> str:
    """Create a Tier-3 policy."""
    from runtime.tier3_policies import create_policy

    result = create_policy(name, description, trigger_conditions, actions, enabled)
    if result.get("error"):
        reasons = "\n  ".join(result.get("reasons", []))
        return f"Policy not created:\n  {reasons}"

    return (
        f"Policy created:\n"
        f"  policy_id: {result['policy_id']}\n"
        f"  name: {result['name']}\n"
        f"  conditions: {len(result['trigger_conditions'])}\n"
        f"  actions: {len(result['actions'])}\n"
        f"  enabled: {result['enabled']}"
    )


def t3_policies() -> str:
    """List all policies."""
    from runtime.tier3_policies import get_policies

    policies = get_policies()
    if not policies:
        return "No Tier-3 policies."

    lines = [f"Tier-3 policies ({len(policies)}):"]
    for p in policies:
        flag = "ON" if p.get("enabled") else "OFF"
        last = p.get("last_eval_result") or "never"
        lines.append(
            f"  {p['policy_id'][:8]}..  {p['name']}  "
            f"[{flag}]  last={last}  "
            f"proposals={p.get('proposals_generated', 0)}  "
            f"plans={p.get('plans_generated', 0)}"
        )
    return "\n".join(lines)


def t3_policy(policy_id: str) -> str:
    """Show detailed policy information."""
    from runtime.tier3_policies import get_policy

    pol = get_policy(policy_id)
    if pol is None:
        return f"Policy '{policy_id}' not found."

    flag = "enabled" if pol.get("enabled") else "disabled"
    lines = [f"Policy '{pol['name']}' ({policy_id[:8]}..):"]
    lines.append(f"  status: {flag}")
    lines.append(f"  description: {pol['description']}")
    lines.append(f"  conditions ({len(pol['trigger_conditions'])}):")
    for c in pol["trigger_conditions"]:
        lines.append(f"    - {c.get('type', '?')}: {_format_condition(c)}")
    lines.append(f"  actions ({len(pol['actions'])}):")
    for a in pol["actions"]:
        lines.append(f"    - {a.get('type', '?')}")
    lines.append(f"  last eval: {pol.get('last_eval_result') or 'never'}")
    lines.append(f"  proposals generated: {pol.get('proposals_generated', 0)}")
    lines.append(f"  plans generated: {pol.get('plans_generated', 0)}")
    return "\n".join(lines)


def _format_condition(cond: Dict[str, Any]) -> str:
    ctype = cond.get("type", "?")
    if ctype == "setting_equals":
        return f"{cond.get('key', '?')} == {cond.get('value', '?')}"
    if ctype == "drift_above":
        return f"{cond.get('metric', '?')} > {cond.get('threshold', '?')}"
    if ctype == "proposal_count":
        return f"status={cond.get('status', '?')} >= {cond.get('min_count', '?')}"
    return str(cond)


def t3_policy_enable(policy_id: str) -> str:
    """Enable a policy."""
    from runtime.tier3_policies import set_policy_enabled

    result = set_policy_enabled(policy_id, True)
    if result.get("updated"):
        return f"Policy {policy_id[:8]}.. enabled."
    return f"Enable failed: {result.get('reason', 'unknown')}"


def t3_policy_disable(policy_id: str) -> str:
    """Disable a policy."""
    from runtime.tier3_policies import set_policy_enabled

    result = set_policy_enabled(policy_id, False)
    if result.get("updated"):
        return f"Policy {policy_id[:8]}.. disabled."
    return f"Disable failed: {result.get('reason', 'unknown')}"


def t3_policy_eval() -> str:
    """Manually trigger evaluation of all enabled policies."""
    from runtime.tier3_policies import evaluate_policies

    summary = evaluate_policies()
    lines = [f"Policy evaluation complete:"]
    lines.append(f"  evaluated: {summary['total_evaluated']}")
    lines.append(f"  skipped (disabled): {summary['total_skipped']}")
    lines.append(f"  triggered: {summary['total_triggered']}")

    for pr in summary.get("policy_results", []):
        pid = pr.get("policy_id", "?")[:8]
        name = pr.get("policy_name", "?")
        result = pr.get("result", "?")
        n_actions = len(pr.get("actions", []))
        lines.append(f"    {pid}..  {name}  {result}  actions={n_actions}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 39: scheduled policy evaluation cockpit
# ------------------------------------------------------------------

def t3_policy_schedule() -> str:
    """Manually invoke scheduled evaluation (respects intervals, windows, rate limits)."""
    from runtime.tier3_policies import evaluate_policies_scheduled

    summary = evaluate_policies_scheduled()
    lines = ["Scheduled policy evaluation complete:"]
    lines.append(f"  evaluated: {summary['total_evaluated']}")
    lines.append(f"  skipped (disabled): {summary['total_skipped_disabled']}")
    lines.append(f"  skipped (schedule): {summary['total_skipped_schedule']}")
    lines.append(f"  triggered: {summary['total_triggered']}")

    for pr in summary.get("policy_results", []):
        pid = pr.get("policy_id", "?")[:8]
        name = pr.get("policy_name", "?")
        result = pr.get("result", "?")
        lines.append(f"    {pid}..  {name}  {result}")

    for sk in summary.get("schedule_skips", []):
        pid = sk.get("policy_id", "?")[:8]
        name = sk.get("policy_name", "?")
        reason = sk.get("reason", "?")
        lines.append(f"    {pid}..  {name}  SKIPPED ({reason})")

    return "\n".join(lines)


def t3_policy_windows(policy_id: str) -> str:
    """Show allowed time windows for a policy."""
    from runtime.tier3_policies import get_policy

    pol = get_policy(policy_id)
    if pol is None:
        return f"Policy '{policy_id}' not found."

    windows = pol.get("allowed_windows") or []
    if not windows:
        return f"Policy {policy_id[:8]}.. has no time windows (always eligible)."

    lines = [f"Time windows for {policy_id[:8]}..:"]
    for w in windows:
        lines.append(f"  {w.get('start', '?')} - {w.get('end', '?')}")
    return "\n".join(lines)


def t3_policy_set_window(
    policy_id: str,
    windows: List[Dict[str, str]],
) -> str:
    """Set allowed time windows for a policy."""
    from runtime.tier3_policies import set_policy_window

    result = set_policy_window(policy_id, windows)
    if result.get("updated"):
        return f"Policy {policy_id[:8]}.. windows updated ({len(windows)} window(s))."
    return f"Update failed: {result.get('reason', 'unknown')}"


def t3_policy_set_interval(policy_id: str, seconds: int) -> str:
    """Set evaluation interval for a policy."""
    from runtime.tier3_policies import set_policy_interval

    result = set_policy_interval(policy_id, seconds)
    if result.get("updated"):
        return f"Policy {policy_id[:8]}.. interval set to {seconds}s."
    return f"Update failed: {result.get('reason', 'unknown')}"


def t3_policy_set_rate_limit(policy_id: str, limit: int) -> str:
    """Set rate limit (max triggers per hour) for a policy."""
    from runtime.tier3_policies import set_policy_rate_limit

    result = set_policy_rate_limit(policy_id, limit)
    if result.get("updated"):
        return f"Policy {policy_id[:8]}.. rate limit set to {limit}/hour."
    return f"Update failed: {result.get('reason', 'unknown')}"


def t3_policy_timers() -> str:
    """Show evaluation timestamps and next eligible times for all policies."""
    from runtime.tier3_policies import get_policies, get_next_eligible_time

    policies = get_policies()
    if not policies:
        return "No Tier-3 policies."

    lines = ["Policy timers:"]
    for p in policies:
        pid = p["policy_id"][:8]
        last = p.get("last_evaluated_at")
        last_str = f"{last:.1f}" if last else "never"
        nxt = get_next_eligible_time(p)
        nxt_str = f"{nxt:.1f}" if nxt else "anytime"
        interval = p.get("evaluation_interval_seconds")
        interval_str = f"{interval}s" if interval else "none"
        rl = p.get("rate_limit")
        rl_str = f"{rl}/hr" if rl else "none"
        tw = p.get("trigger_count_window") or []
        lines.append(
            f"  {pid}..  {p['name']}  "
            f"last={last_str}  next={nxt_str}  "
            f"interval={interval_str}  "
            f"rate={len(tw)}/{rl_str}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 40: adaptive insights cockpit
# ------------------------------------------------------------------

def t3_adapt() -> str:
    """Run adaptive analysis and generate insights."""
    from runtime.tier3_adaptive import generate_adaptive_insights

    result = generate_adaptive_insights()
    n = result["insights_generated"]
    total = result["total_insights"]

    if n == 0:
        return f"Adaptive analysis complete: no new insights ({total} total)."

    lines = [f"Adaptive analysis complete: {n} new insight(s) ({total} total):"]
    for ins in result.get("new_insights", []):
        iid = ins["insight_id"][:8]
        lines.append(f"  {iid}..  [{ins['insight_type']}]  {ins['summary']}")
    return "\n".join(lines)


def t3_insights() -> str:
    """List recent adaptive insights."""
    from runtime.tier3_adaptive import get_insights

    insights = get_insights(20)
    if not insights:
        return "No adaptive insights."

    lines = [f"Adaptive insights ({len(insights)}):"]
    for ins in insights:
        iid = ins["insight_id"][:8]
        lines.append(
            f"  {iid}..  [{ins['insight_type']}]  {ins['summary']}"
        )
    return "\n".join(lines)


def t3_insight(insight_id: str) -> str:
    """Show a detailed adaptive insight."""
    from runtime.tier3_adaptive import get_insight

    ins = get_insight(insight_id)
    if ins is None:
        return f"Insight '{insight_id}' not found."

    lines = [f"Insight {insight_id[:8]}.. [{ins['insight_type']}]:"]
    lines.append(f"  summary: {ins['summary']}")
    lines.append(f"  recommendation: {ins['recommended_action']}")
    if ins.get("related_policy_ids"):
        lines.append(f"  policies: {[p[:8] + '..' for p in ins['related_policy_ids']]}")
    if ins.get("related_proposal_ids"):
        lines.append(f"  proposals: {[p[:8] + '..' for p in ins['related_proposal_ids']]}")
    if ins.get("detail"):
        for k, v in ins["detail"].items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_insight_recommendations() -> str:
    """Show all recommended actions from recent insights."""
    from runtime.tier3_adaptive import get_insights

    insights = get_insights(50)
    if not insights:
        return "No recommendations."

    lines = [f"Recommendations ({len(insights)}):"]
    for ins in insights:
        iid = ins["insight_id"][:8]
        lines.append(f"  {iid}..  {ins['recommended_action']}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 41: adaptive bridge cockpit
# ------------------------------------------------------------------

def t3_recommend(insight_id: str) -> str:
    """Preview the recommendation for an adaptive insight."""
    from runtime.tier3_adaptive_bridge import preview_recommendation

    result = preview_recommendation(insight_id)
    if result.get("error"):
        return f"Error: {result.get('reason', '?')}"

    rec = result.get("recommendation", {})
    lines = [f"Recommendation for {insight_id[:8]}.. [{result.get('insight_type', '?')}]:"]
    lines.append(f"  summary: {result.get('summary', '')}")
    lines.append(f"  actionable: {rec.get('actionable', False)}")
    lines.append(f"  kind: {rec.get('action_kind', '?')}")

    if rec.get("action_kind") == "policy_edit":
        lines.append(f"  operation: {rec.get('operation', '?')}")
        if rec.get("target_policy_id"):
            lines.append(f"  target policy: {rec['target_policy_id'][:8]}..")
        if rec.get("policy_ids"):
            lines.append(f"  policies: {[p[:8] + '..' for p in rec['policy_ids']]}")
        if rec.get("overrides"):
            lines.append(f"  overrides: {rec['overrides']}")
    elif rec.get("action_kind") == "create_plan":
        lines.append(f"  plan name: {rec.get('plan_name', '?')}")
        ids = rec.get("proposal_ids") or []
        lines.append(f"  proposals: {[p[:8] + '..' for p in ids]}")
    elif rec.get("action_kind") == "create_proposal":
        lines.append(f"  action type: {rec.get('action_type', '?')}")
        lines.append(f"  title: {rec.get('title', '?')}")
    else:
        lines.append(f"  description: {rec.get('description', '')}")

    if rec.get("suggested_adjustment"):
        lines.append(f"  suggested adjustment: {rec['suggested_adjustment']}")

    lines.append(f"  (preview only -- use t3_apply_recommendation to create)")
    return "\n".join(lines)


def t3_apply_recommendation(insight_id: str) -> str:
    """Create a governed artifact from an adaptive insight."""
    from runtime.tier3_adaptive_bridge import apply_recommendation

    result = apply_recommendation(insight_id)
    if not result.get("applied"):
        reason = result.get("reason", "?")
        rec = result.get("recommendation")
        if rec and rec.get("action_kind") == "descriptive":
            return (f"Insight {insight_id[:8]}.. is descriptive only "
                    f"(not auto-actionable):\n  {rec.get('description', '')}")
        return f"Recommendation not applied: {reason}"

    artifact = result.get("artifact_type", "?")
    if artifact == "plan":
        return (f"Plan created from insight {insight_id[:8]}..:\n"
                f"  plan_id: {result.get('plan_id', '?')}\n"
                f"  adaptive_origin: {result.get('adaptive_origin', '?')[:8]}..")
    if artifact == "proposal":
        return (f"Proposal created from insight {insight_id[:8]}..:\n"
                f"  proposal_id: {result.get('proposal_id', '?')}\n"
                f"  adaptive_origin: {result.get('adaptive_origin', '?')[:8]}..")
    if artifact == "policy_edit":
        op = result.get("operation", "?")
        lines = [f"Policy edit applied from insight {insight_id[:8]}.. ({op}):"]
        if result.get("new_policy_id"):
            lines.append(f"  new policy: {result['new_policy_id'][:8]}.. (disabled)")
        if result.get("policy_id"):
            lines.append(f"  policy: {result['policy_id'][:8]}..")
        if result.get("retired_policy_ids"):
            lines.append(f"  retired: {[p[:8] + '..' for p in result['retired_policy_ids']]}")
        lines.append(f"  adaptive_origin: {result.get('adaptive_origin', '?')[:8]}..")
        return "\n".join(lines)

    return f"Artifact created: {result}"


def t3_recommendations() -> str:
    """List insights that have actionable recommendations."""
    from runtime.tier3_adaptive import get_insights, insight_to_recommendation_action

    insights = get_insights(50)
    if not insights:
        return "No adaptive insights."

    actionable = []
    descriptive = []
    for ins in insights:
        rec = insight_to_recommendation_action(ins)
        if rec.get("actionable"):
            actionable.append((ins, rec))
        else:
            descriptive.append((ins, rec))

    lines = []
    if actionable:
        lines.append(f"Actionable recommendations ({len(actionable)}):")
        for ins, rec in actionable:
            iid = ins["insight_id"][:8]
            lines.append(f"  {iid}..  [{ins['insight_type']}]  "
                         f"{rec.get('action_kind')}: {ins['summary']}")

    if descriptive:
        lines.append(f"Descriptive recommendations ({len(descriptive)}):")
        for ins, rec in descriptive:
            iid = ins["insight_id"][:8]
            adj = rec.get("suggested_adjustment", "")
            adj_str = f"  ({adj})" if adj else ""
            lines.append(f"  {iid}..  [{ins['insight_type']}]  "
                         f"{ins.get('recommended_action', '')}{adj_str}")

    if not lines:
        return "No recommendations."
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 42: policy diff cockpit
# ------------------------------------------------------------------

def t3_policy_diff(policy_id: str) -> str:
    """Show structural diff between a policy and its adaptive recommendation."""
    from runtime.tier3_policies import get_policy
    from runtime.tier3_adaptive import get_insights, insight_to_recommendation_action

    pol = get_policy(policy_id)
    if pol is None:
        return f"Policy '{policy_id}' not found."

    matching_recs = []
    for ins in get_insights(50):
        pids = ins.get("related_policy_ids") or []
        if policy_id in pids:
            rec = insight_to_recommendation_action(ins)
            if rec.get("action_kind") == "policy_edit":
                matching_recs.append((ins, rec))

    if not matching_recs:
        return f"No policy-edit recommendations found for {policy_id[:8]}.."

    lines = [f"Policy diff for {policy_id[:8]}.. ('{pol.get('name', '?')}'):"]
    lines.append(f"  current state: {'retired' if pol.get('retired') else 'enabled' if pol.get('enabled') else 'disabled'}")

    for ins, rec in matching_recs:
        iid = ins["insight_id"][:8]
        op = rec.get("operation", "?")
        lines.append(f"  [{iid}..] recommended: {op}")

        if op == "retire_policy":
            lines.append(f"    - enabled: {pol.get('enabled')} -> False")
            lines.append(f"    - retired: {pol.get('retired', False)} -> True")
        elif op == "clone_and_tune_policy":
            overrides = rec.get("overrides") or {}
            lines.append(f"    + new clone (disabled) with overrides:")
            for k, v in overrides.items():
                lines.append(f"      {k}: {pol.get(k, '?')} -> {v}")
        elif op == "merge_policies":
            pids = rec.get("policy_ids") or []
            lines.append(f"    + merge {len(pids)} policies into new clone (disabled)")
            lines.append(f"    - retire originals: {[p[:8] + '..' for p in pids]}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Governance profiles
# ------------------------------------------------------------------

def t3_profile_create(
    name: str,
    description: str,
    attached_policy_ids: list | None = None,
    scheduling_overrides: dict | None = None,
    tier3_feature_flags: dict | None = None,
) -> str:
    from runtime.tier3_profiles import create_profile

    result = create_profile(
        name=name,
        description=description,
        attached_policy_ids=attached_policy_ids,
        scheduling_overrides=scheduling_overrides,
        tier3_feature_flags=tier3_feature_flags,
    )
    pid = result["profile_id"]
    flags = result.get("tier3_feature_flags", {})
    flag_str = "  ".join(f"{k}={v}" for k, v in flags.items())
    return (
        f"Profile created: {pid[:8]}.. '{name}' (inactive)\n"
        f"  policies: {len(result.get('attached_policy_ids', []))}  "
        f"flags: {flag_str}"
    )


def t3_profiles() -> str:
    from runtime.tier3_profiles import list_profiles, get_active_profile

    profiles = list_profiles()
    if not profiles:
        return "No governance profiles."

    active = get_active_profile()
    active_id = active["profile_id"] if active else None

    lines = [f"Governance profiles ({len(profiles)}):"]
    for p in profiles:
        pid = p["profile_id"][:8]
        marker = " *" if p["profile_id"] == active_id else ""
        lines.append(
            f"  {pid}..  '{p['name']}'  {p['status']}{marker}  "
            f"policies={len(p.get('attached_policy_ids', []))}"
        )
    return "\n".join(lines)


def t3_profile(profile_id: str) -> str:
    from runtime.tier3_profiles import get_profile

    p = get_profile(profile_id)
    if p is None:
        return f"Profile '{profile_id}' not found."

    flags = p.get("tier3_feature_flags", {})
    overrides = p.get("scheduling_overrides", {})
    lines = [
        f"Profile: {p['profile_id'][:8]}.. '{p['name']}'  [{p['status']}]",
        f"  description: {p.get('description', '-')}",
        f"  policies: {len(p.get('attached_policy_ids', []))}",
        f"  flags: {'  '.join(f'{k}={v}' for k, v in flags.items())}",
        f"  scheduling overrides: {len(overrides)} policies",
    ]
    for pol_id, ov in overrides.items():
        lines.append(f"    {pol_id[:8]}.. {ov}")
    return "\n".join(lines)


def t3_profile_activate(profile_id: str) -> str:
    from runtime.tier3_profiles import activate_profile

    result = activate_profile(profile_id)
    if not result.get("activated"):
        return f"Activation failed: {result.get('reason', '?')}"

    prev = result.get("previous_profile_id")
    prev_str = f" (was {prev[:8]}..)" if prev else ""
    return f"Profile {profile_id[:8]}.. activated.{prev_str}"


def t3_profile_deactivate() -> str:
    from runtime.tier3_profiles import deactivate_profile

    result = deactivate_profile()
    if not result.get("deactivated"):
        return f"Deactivation failed: {result.get('reason', '?')}"
    return f"Profile {result['profile_id'][:8]}.. deactivated. No active profile."


def t3_profile_status() -> str:
    from runtime.tier3_profiles import get_active_profile

    profile = get_active_profile()
    if profile is None:
        return "No active governance profile. All policies in scope, default flags apply."

    flags = profile.get("tier3_feature_flags", {})
    lines = [
        f"Active profile: {profile['profile_id'][:8]}.. '{profile['name']}'",
        f"  policies in scope: {len(profile.get('attached_policy_ids', []))}",
        f"  flags: {'  '.join(f'{k}={v}' for k, v in flags.items())}",
    ]
    overrides = profile.get("scheduling_overrides", {})
    if overrides:
        lines.append(f"  scheduling overrides for {len(overrides)} policies")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Runbooks
# ------------------------------------------------------------------

def t3_runbook_create(
    name: str,
    description: str,
    steps: list,
) -> str:
    from runtime.tier3_runbooks import create_runbook

    result = create_runbook(name=name, description=description, steps=steps)
    if result.get("error"):
        reasons = result.get("reasons", [])
        return "Runbook creation failed:\n" + "\n".join(f"  - {r}" for r in reasons)
    rid = result["runbook_id"]
    return (
        f"Runbook created: {rid[:8]}.. '{name}' (draft)\n"
        f"  steps: {len(result.get('steps', []))}"
    )


def t3_runbooks() -> str:
    from runtime.tier3_runbooks import list_runbooks

    runbooks = list_runbooks()
    if not runbooks:
        return "No runbooks defined."

    lines = [f"Runbooks ({len(runbooks)}):"]
    for r in runbooks:
        rid = r["runbook_id"][:8]
        n_steps = len(r.get("steps", []))
        sr = r.get("step_results") or []
        ok = sum(1 for s in sr if s.get("status") == "success")
        fail = sum(1 for s in sr if s.get("status") == "failed")
        lines.append(
            f"  {rid}..  '{r['name']}'  [{r['status']}]  "
            f"steps={n_steps}  ok={ok} fail={fail}"
        )
    return "\n".join(lines)


def t3_runbook(runbook_id: str) -> str:
    from runtime.tier3_runbooks import get_runbook

    r = get_runbook(runbook_id)
    if r is None:
        return f"Runbook '{runbook_id}' not found."

    lines = [
        f"Runbook: {r['runbook_id'][:8]}.. '{r['name']}'  [{r['status']}]",
        f"  description: {r.get('description', '-')}",
        f"  steps ({len(r.get('steps', []))}):",
    ]
    for i, step in enumerate(r.get("steps", [])):
        stype = step.get("type", "?")
        detail_parts = [f"{k}={v}" for k, v in step.items() if k != "type"]
        detail = "  " + "  ".join(detail_parts) if detail_parts else ""
        lines.append(f"    [{i}] {stype}{detail}")

    sr = r.get("step_results") or []
    if sr:
        lines.append("  results:")
        for res in sr:
            idx = res.get("step_index", "?")
            st = res.get("status", "?")
            reason = res.get("reason", "")
            reason_str = f"  ({reason})" if reason else ""
            lines.append(f"    [{idx}] {res.get('type', '?')}  {st}{reason_str}")

    if r.get("last_executed_at"):
        lines.append(f"  last executed: t={r['last_executed_at']:.1f}")

    return "\n".join(lines)


def t3_runbook_execute(runbook_id: str) -> str:
    from runtime.tier3_runbooks import execute_runbook

    result = execute_runbook(runbook_id)
    if not result.get("executed"):
        return f"Runbook execution failed: {result.get('reason', '?')}"

    status = result["status"]
    ok = result.get("succeeded", 0)
    fail = result.get("failed", 0)
    skip = result.get("skipped", 0)
    total = result.get("total_steps", 0)

    lines = [
        f"Runbook {runbook_id[:8]}.. {status}  "
        f"({ok} ok, {fail} failed, {skip} skipped / {total} total)",
    ]
    for sr in result.get("step_results", []):
        idx = sr.get("step_index", "?")
        st = sr.get("status", "?")
        reason = sr.get("reason", "")
        reason_str = f"  ({reason})" if reason else ""
        lines.append(f"  [{idx}] {sr.get('type', '?')}  {st}{reason_str}")
    return "\n".join(lines)


def t3_runbook_history() -> str:
    from runtime.tier3_runbooks import list_runbooks

    runbooks = list_runbooks()
    executed = [r for r in runbooks if r.get("last_executed_at")]
    executed.sort(key=lambda r: r.get("last_executed_at", 0), reverse=True)

    if not executed:
        return "No runbook executions yet."

    lines = [f"Recent runbook executions ({len(executed)}):"]
    for r in executed[:10]:
        rid = r["runbook_id"][:8]
        sr = r.get("step_results") or []
        ok = sum(1 for s in sr if s.get("status") == "success")
        fail = sum(1 for s in sr if s.get("status") == "failed")
        ts = r.get("last_executed_at", 0)
        lines.append(
            f"  {rid}..  '{r['name']}'  [{r['status']}]  "
            f"ok={ok} fail={fail}  t={ts:.1f}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------
# Runbook templates
# ------------------------------------------------------------------

def t3_template_create(
    name: str,
    description: str,
    parameter_schema: dict,
    step_blueprints: list,
) -> str:
    from runtime.tier3_runbook_templates import create_template

    t = create_template(
        name=name,
        description=description,
        parameter_schema=parameter_schema,
        step_blueprints=step_blueprints,
    )
    tid = t["template_id"]
    n_steps = len(t.get("step_blueprints", []))
    n_params = len(t.get("parameter_schema", {}).get("properties", {}))
    return (
        f"Template created: {tid[:8]}.. '{name}'\n"
        f"  steps: {n_steps}  parameters: {n_params}"
    )


def t3_templates() -> str:
    from runtime.tier3_runbook_templates import list_templates

    templates = list_templates()
    if not templates:
        return "No runbook templates."

    lines = [f"Runbook templates ({len(templates)}):"]
    for t in templates:
        tid = t["template_id"][:8]
        n_steps = len(t.get("step_blueprints", []))
        n_params = len(t.get("parameter_schema", {}).get("properties", {}))
        lines.append(f"  {tid}..  '{t['name']}'  steps={n_steps}  params={n_params}")
    return "\n".join(lines)


def t3_template(template_id: str) -> str:
    from runtime.tier3_runbook_templates import get_template

    t = get_template(template_id)
    if t is None:
        return f"Template '{template_id}' not found."

    schema = t.get("parameter_schema", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines = [
        f"Template: {t['template_id'][:8]}.. '{t['name']}'",
        f"  description: {t.get('description', '-')}",
        f"  parameters ({len(props)}):",
    ]
    for pname, pspec in props.items():
        req = " (required)" if pname in required else ""
        default = f"  default={pspec['default']}" if "default" in pspec else ""
        lines.append(f"    {pname}: {pspec.get('type', '?')}{req}{default}")

    lines.append(f"  step blueprints ({len(t.get('step_blueprints', []))}):")
    for i, step in enumerate(t.get("step_blueprints", [])):
        stype = step.get("type", "?")
        detail_parts = [f"{k}={v}" for k, v in step.items() if k != "type"]
        detail = "  " + "  ".join(detail_parts) if detail_parts else ""
        lines.append(f"    [{i}] {stype}{detail}")

    return "\n".join(lines)


def t3_template_instantiate(template_id: str, parameters: dict | None = None) -> str:
    from runtime.tier3_runbook_templates import instantiate_template

    result = instantiate_template(template_id, parameters)
    if result.get("error"):
        reasons = result.get("reasons") or [result.get("reason", "?")]
        return "Instantiation failed:\n" + "\n".join(f"  - {r}" for r in reasons)

    rid = result["runbook_id"]
    origin = result.get("template_origin", {})
    return (
        f"Runbook instantiated: {rid[:8]}.. (draft)\n"
        f"  from template: {origin.get('template_name', '?')}\n"
        f"  parameters: {origin.get('parameters', {})}"
    )


# ------------------------------------------------------------------
# Scenario presets
# ------------------------------------------------------------------

def t3_scenarios() -> str:
    from runtime.tier3_scenarios import list_scenarios

    scenarios = list_scenarios()
    if not scenarios:
        return "No scenario presets."

    lines = [f"Scenario presets ({len(scenarios)}):"]
    for s in scenarios:
        tid = s.get("template_id")
        tid_str = f"  template={tid[:8]}.." if tid else ""
        lines.append(f"  '{s['name']}': {s['description'][:60]}{tid_str}")
    return "\n".join(lines)


def t3_scenario_run(name: str, overrides: dict | None = None) -> str:
    from runtime.tier3_scenarios import run_scenario

    result = run_scenario(name, overrides)
    if result.get("error"):
        reasons = result.get("reasons") or [result.get("reason", "?")]
        return "Scenario failed:\n" + "\n".join(f"  - {r}" for r in reasons)

    rid = result["runbook_id"]
    origin = result.get("scenario_origin", {})
    n_steps = len(result.get("steps", []))
    return (
        f"Scenario '{name}' created runbook {rid[:8]}.. (draft, {n_steps} steps)\n"
        f"  overrides: {origin.get('overrides', {})}\n"
        f"  Execute with: t3_runbook_execute('{rid}')"
    )


# ------------------------------------------------------------------
# Environments
# ------------------------------------------------------------------

def t3_env_create(
    name: str,
    description: str,
    default_profile_id: str | None = None,
    allowed_profile_ids: list | None = None,
    allowed_policy_ids: list | None = None,
    allowed_runbook_template_ids: list | None = None,
) -> str:
    from runtime.tier3_environments import create_environment

    env = create_environment(
        name=name,
        description=description,
        default_profile_id=default_profile_id,
        allowed_profile_ids=allowed_profile_ids,
        allowed_policy_ids=allowed_policy_ids,
        allowed_runbook_template_ids=allowed_runbook_template_ids,
    )
    eid = env["env_id"]
    n_prof = len(env.get("allowed_profile_ids", []))
    n_pol = len(env.get("allowed_policy_ids", []))
    n_tmpl = len(env.get("allowed_runbook_template_ids", []))
    dp = env.get("default_profile_id")
    dp_str = f"  default_profile={dp[:8]}.." if dp else ""
    return (
        f"Environment created: {eid[:8]}.. '{name}' (inactive)\n"
        f"  profiles={n_prof}  policies={n_pol}  templates={n_tmpl}{dp_str}"
    )


def t3_envs() -> str:
    from runtime.tier3_environments import list_environments, get_active_environment

    envs = list_environments()
    if not envs:
        return "No environments defined."

    active = get_active_environment()
    active_id = active["env_id"] if active else None

    lines = [f"Environments ({len(envs)}):"]
    for e in envs:
        eid = e["env_id"][:8]
        marker = " *" if e["env_id"] == active_id else ""
        n_prof = len(e.get("allowed_profile_ids", []))
        n_pol = len(e.get("allowed_policy_ids", []))
        lines.append(
            f"  {eid}..  '{e['name']}'  [{e['status']}]{marker}  "
            f"profiles={n_prof} policies={n_pol}"
        )
    return "\n".join(lines)


def t3_env(env_id: str) -> str:
    from runtime.tier3_environments import get_environment

    e = get_environment(env_id)
    if e is None:
        return f"Environment '{env_id}' not found."

    dp = e.get("default_profile_id")
    dp_str = dp[:8] + ".." if dp else "none"
    lines = [
        f"Environment: {e['env_id'][:8]}.. '{e['name']}'  [{e['status']}]",
        f"  description: {e.get('description', '-')}",
        f"  default profile: {dp_str}",
        f"  allowed profiles: {len(e.get('allowed_profile_ids', []))}",
        f"  allowed policies: {len(e.get('allowed_policy_ids', []))}",
        f"  allowed templates: {len(e.get('allowed_runbook_template_ids', []))}",
    ]
    return "\n".join(lines)


def t3_env_activate(env_id: str) -> str:
    from runtime.tier3_environments import activate_environment

    result = activate_environment(env_id)
    if not result.get("activated"):
        return f"Activation failed: {result.get('reason', '?')}"

    prev = result.get("previous_env_id")
    prev_str = f" (was {prev[:8]}..)" if prev else ""
    dp = result.get("default_profile_id")
    dp_str = f"\n  Suggested profile: {dp[:8]}.. (activate manually)" if dp else ""
    return f"Environment {env_id[:8]}.. activated.{prev_str}{dp_str}"


def t3_env_deactivate() -> str:
    from runtime.tier3_environments import deactivate_environment

    result = deactivate_environment()
    if not result.get("deactivated"):
        return f"Deactivation failed: {result.get('reason', '?')}"
    return f"Environment {result['env_id'][:8]}.. deactivated. No active environment."


def t3_env_status() -> str:
    from runtime.tier3_environments import get_active_environment

    env = get_active_environment()
    if env is None:
        return "No active environment. All profiles, policies, and templates are unrestricted."

    dp = env.get("default_profile_id")
    dp_str = dp[:8] + ".." if dp else "none"
    lines = [
        f"Active environment: {env['env_id'][:8]}.. '{env['name']}'",
        f"  allowed profiles: {len(env.get('allowed_profile_ids', []))}",
        f"  allowed policies: {len(env.get('allowed_policy_ids', []))}",
        f"  allowed templates: {len(env.get('allowed_runbook_template_ids', []))}",
        f"  default profile: {dp_str}",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------
# Environment relations & promotion
# ------------------------------------------------------------------

def t3_env_relations(env_id: str) -> str:
    from runtime.tier3_environments import get_environment

    e = get_environment(env_id)
    if e is None:
        return f"Environment '{env_id}' not found."

    up = e.get("upstream_env_id")
    down = e.get("downstream_env_ids") or []
    up_str = up[:8] + ".." if up else "none"
    down_str = ", ".join(d[:8] + ".." for d in down) if down else "none"
    return (
        f"Relations for {e['env_id'][:8]}.. '{e['name']}':\n"
        f"  upstream: {up_str}\n"
        f"  downstream: [{down_str}]"
    )


def t3_env_set_relations(
    env_id: str,
    upstream_env_id: str | None = None,
    downstream_env_ids: list | None = None,
) -> str:
    from runtime.tier3_environments import set_environment_relations

    result = set_environment_relations(env_id, upstream_env_id, downstream_env_ids)
    if not result.get("updated"):
        return f"Failed: {result.get('reason', '?')}"
    up = result.get("upstream_env_id")
    down = result.get("downstream_env_ids") or []
    up_str = up[:8] + ".." if up else "none"
    down_str = ", ".join(d[:8] + ".." for d in down) if down else "none"
    return f"Relations updated for {env_id[:8]}..\n  upstream: {up_str}\n  downstream: [{down_str}]"


def t3_env_compare(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_promotion import compare_envs

    result = compare_envs(source_env_id, target_env_id, scope)
    if result.get("error"):
        return f"Comparison failed: {result.get('reason', '?')}"

    if scope == "all":
        lines = [f"Comparison: {source_env_id[:8]}.. vs {target_env_id[:8]}.."]
        for s, comp in result.get("comparisons", {}).items():
            src_only = comp.get("only_in_source", [])
            tgt_only = comp.get("only_in_target", [])
            both = comp.get("in_both", [])
            lines.append(
                f"  {s}: source_only={len(src_only)}  "
                f"target_only={len(tgt_only)}  shared={len(both)}"
            )
        return "\n".join(lines)

    src_only = result.get("only_in_source", [])
    tgt_only = result.get("only_in_target", [])
    both = result.get("in_both", [])
    lines = [
        f"Comparison ({scope}): {source_env_id[:8]}.. vs {target_env_id[:8]}..",
        f"  only in source ({len(src_only)}):",
    ]
    for item in src_only[:5]:
        lines.append(f"    {item[:12]}..")
    lines.append(f"  only in target ({len(tgt_only)}):")
    for item in tgt_only[:5]:
        lines.append(f"    {item[:12]}..")
    lines.append(f"  shared: {len(both)}")
    return "\n".join(lines)


def t3_env_promotion_plan(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_promotion import plan_promotion

    plan = plan_promotion(source_env_id, target_env_id, scope)
    if plan.get("error"):
        return f"Plan failed: {plan.get('reason', '?')}"

    ops = plan.get("operations", [])
    conflicts = plan.get("conflicts", [])
    path = plan.get("promotion_path")
    path_str = " -> ".join(p[:8] + ".." for p in path) if path else "no direct path"

    lines = [
        f"Promotion plan: {plan['plan_id'][:8]}..  {source_env_id[:8]}.. -> {target_env_id[:8]}..",
        f"  scope: {scope}  path: {path_str}",
        f"  operations: {len(ops)}",
    ]
    for op in ops[:10]:
        lines.append(f"    {op['scope']}: {op['operation']}  item={op['item_id'][:12]}..")
    if conflicts:
        lines.append(f"  conflicts: {len(conflicts)}")
        for c in conflicts:
            lines.append(f"    - {c}")
    return "\n".join(lines)


def t3_env_promotion_runbook(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_promotion import plan_promotion, create_promotion_runbook_from_plan

    plan = plan_promotion(source_env_id, target_env_id, scope)
    if plan.get("error"):
        return f"Plan failed: {plan.get('reason', '?')}"

    result = create_promotion_runbook_from_plan(plan)
    if result.get("error"):
        return f"Runbook creation failed: {result.get('reason', '?')}"

    rid = result["runbook_id"]
    n_steps = len(result.get("steps", []))
    n_ops = len(plan.get("operations", []))
    return (
        f"Promotion runbook created: {rid[:8]}.. (draft, {n_steps} steps)\n"
        f"  {n_ops} promotion operations from {source_env_id[:8]}.. -> {target_env_id[:8]}..\n"
        f"  Execute with: t3_runbook_execute('{rid}')"
    )


# ------------------------------------------------------------------
# Environment governance packs
# ------------------------------------------------------------------

def t3_envpack_create(
    name: str,
    description: str,
    profile_ids: list | None = None,
    policy_ids: list | None = None,
    scheduling_overrides: dict | None = None,
    feature_flag_overrides: dict | None = None,
) -> str:
    from runtime.tier3_envpacks import create_envpack

    pack = create_envpack(
        name=name,
        description=description,
        profile_ids=profile_ids,
        policy_ids=policy_ids,
        scheduling_overrides=scheduling_overrides,
        feature_flag_overrides=feature_flag_overrides,
    )
    pid = pack["pack_id"]
    n_pol = len(pack.get("policy_ids", []))
    n_prof = len(pack.get("profile_ids", []))
    n_flags = len(pack.get("feature_flag_overrides", {}))
    return (
        f"Governance pack created: {pid[:8]}.. '{name}'\n"
        f"  profiles={n_prof}  policies={n_pol}  flags={n_flags}"
    )


def t3_envpacks() -> str:
    from runtime.tier3_envpacks import list_envpacks

    packs = list_envpacks()
    if not packs:
        return "No governance packs defined."

    lines = [f"Governance packs ({len(packs)}):"]
    for p in packs:
        pid = p["pack_id"][:8]
        n_pol = len(p.get("policy_ids", []))
        n_prof = len(p.get("profile_ids", []))
        n_flags = len(p.get("feature_flag_overrides", {}))
        lines.append(
            f"  {pid}..  '{p['name']}'  "
            f"profiles={n_prof} policies={n_pol} flags={n_flags}"
        )
    return "\n".join(lines)


def t3_envpack(pack_id: str) -> str:
    from runtime.tier3_envpacks import get_envpack

    p = get_envpack(pack_id)
    if p is None:
        return f"Pack '{pack_id}' not found."

    lines = [
        f"Pack: {p['pack_id'][:8]}.. '{p['name']}'",
        f"  description: {p.get('description', '-')}",
        f"  profiles: {p.get('profile_ids', [])}",
        f"  policies: {p.get('policy_ids', [])}",
        f"  scheduling overrides: {len(p.get('scheduling_overrides', {}))} policies",
        f"  feature flags: {p.get('feature_flag_overrides', {})}",
    ]
    return "\n".join(lines)


def t3_envpack_apply(env_id: str, pack_id: str) -> str:
    from runtime.tier3_envpacks import apply_pack_to_environment

    result = apply_pack_to_environment(env_id, pack_id)
    if not result.get("applied"):
        return f"Apply failed: {result.get('reason', '?')}"
    return f"Pack {pack_id[:8]}.. applied to environment {env_id[:8]}.."


def t3_env_defaults(env_id: str) -> str:
    from runtime.tier3_environments import get_environment

    env = get_environment(env_id)
    if env is None:
        return f"Environment '{env_id}' not found."

    dp = env.get("default_profile_id")
    dp_str = dp[:8] + ".." if dp else "none"
    d_pols = env.get("default_policy_ids", [])
    d_sched = env.get("default_scheduling_overrides", {})
    d_flags = env.get("default_feature_flags", {})
    packs = env.get("applied_pack_ids", [])

    lines = [
        f"Defaults for {env['env_id'][:8]}.. '{env['name']}':",
        f"  default profile: {dp_str}",
        f"  default policies: {len(d_pols)}",
    ]
    for pid in d_pols[:10]:
        lines.append(f"    {pid}")
    lines.append(f"  scheduling overrides: {len(d_sched)} policies")
    if d_flags:
        flag_str = "  ".join(f"{k}={v}" for k, v in d_flags.items())
        lines.append(f"  feature flags: {flag_str}")
    else:
        lines.append("  feature flags: none")
    lines.append(f"  applied packs: {len(packs)}")
    for pk in packs:
        lines.append(f"    {pk[:8]}..")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Environment drift detection & health
# ------------------------------------------------------------------

def t3_env_drift(env_a_id: str, env_b_id: str) -> str:
    from runtime.tier3_env_drift import detect_full_env_drift

    report = detect_full_env_drift(env_a_id, env_b_id)
    if report.get("error"):
        return f"Drift error: {report.get('reason', '?')}"

    lines = [
        f"Drift: {env_a_id[:8]}.. vs {env_b_id[:8]}..  "
        f"drift={'YES' if report['has_drift'] else 'none'}"
    ]

    for scope in ("policies", "profiles", "templates"):
        section = report.get(scope, {})
        if section.get("error"):
            lines.append(f"  {scope}: error")
            continue
        only_a = section.get("only_in_a", [])
        only_b = section.get("only_in_b", [])
        shared = section.get("shared", [])
        lines.append(
            f"  {scope}: only_a={len(only_a)} only_b={len(only_b)} "
            f"shared={len(shared)}"
        )

    ff = report.get("feature_flags", {})
    if not ff.get("error"):
        diff = ff.get("different", {})
        only_a = ff.get("only_in_a", {})
        only_b = ff.get("only_in_b", {})
        lines.append(
            f"  flags: only_a={len(only_a)} only_b={len(only_b)} "
            f"different={len(diff)}"
        )
        for k, v in diff.items():
            lines.append(f"    {k}: a={v['a']} b={v['b']}")

    return "\n".join(lines)


def t3_envpack_validate(pack_id: str, env_id: str) -> str:
    from runtime.tier3_envpacks import validate_envpack_against_environment

    result = validate_envpack_against_environment(pack_id, env_id)
    if result.get("reason"):
        return f"Validation error: {result['reason']}"

    if result["valid"]:
        return f"Pack {pack_id[:8]}.. is valid for environment {env_id[:8]}.."

    lines = [
        f"Pack {pack_id[:8]}.. has {len(result['issues'])} issue(s) "
        f"for environment {env_id[:8]}..:"
    ]
    for issue in result["issues"]:
        lines.append(f"  [{issue['scope']}] {issue['id']}: {issue['issue']}")
    return "\n".join(lines)


def t3_env_health(env_id: str) -> str:
    from runtime.tier3_env_health import compute_environment_health

    report = compute_environment_health(env_id)
    if report.get("error"):
        return f"Health error: {report.get('reason', '?')}"

    lines = [
        f"Health: {env_id[:8]}.. '{report['env_name']}'  "
        f"grade={report['grade']}",
        f"  policies={report['effective_policies']}  "
        f"profiles={report['effective_profiles']}  "
        f"templates={report['effective_templates']}  "
        f"packs={report['applied_packs']}",
    ]

    findings = report.get("findings", [])
    if findings:
        lines.append(f"  Findings ({len(findings)}):")
        for f in findings[:10]:
            lines.append(f"    [{f['category']}] {f['detail']}")

    drift = report.get("upstream_drift", {})
    if drift.get("has_upstream"):
        if drift.get("has_drift"):
            ds = drift.get("drift_summary", {})
            lines.append(
                f"  Upstream drift vs {drift['upstream_env_id'][:8]}..:"
                f"  pol={ds.get('policies_only_upstream', 0)}↑"
                f"/{ds.get('policies_only_here', 0)}↓"
                f"  flags_diff={ds.get('flag_differences', 0)}"
            )
        else:
            lines.append(
                f"  Upstream {drift['upstream_env_id'][:8]}..: in sync"
            )
    return "\n".join(lines)


def t3_env_health_all() -> str:
    from runtime.tier3_env_health import compute_all_environment_health

    reports = compute_all_environment_health()
    if not reports:
        return "No environments registered."

    lines = [f"Environment health ({len(reports)}):"]
    for r in reports:
        if r.get("error"):
            lines.append(f"  {r.get('env_id', '?')[:8]}..  error")
            continue
        n_findings = len(r.get("findings", []))
        drift_flag = "drift" if r.get("upstream_drift", {}).get("has_drift") else "-"
        lines.append(
            f"  {r['env_id'][:8]}.. '{r['env_name']}'  "
            f"grade={r['grade']}  findings={n_findings}  {drift_flag}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------
# Promotion readiness & guardrails
# ------------------------------------------------------------------

def t3_env_promotion_readiness(
    source_env_id: str,
    target_env_id: str,
) -> str:
    from runtime.tier3_env_health import compute_promotion_readiness

    r = compute_promotion_readiness(source_env_id, target_env_id)
    if r.get("error"):
        return f"Readiness error: {r.get('reason', '?')}"

    lines = [
        f"Promotion readiness: {source_env_id[:8]}.. -> {target_env_id[:8]}..  "
        f"score={r['readiness_score']}/100",
        f"  source={r.get('source_grade', '?')}  "
        f"target={r.get('target_grade', '?')}",
    ]
    for b in r.get("blockers", []):
        lines.append(f"  [BLOCKER] {b}")
    for w in r.get("warnings", []):
        lines.append(f"  [WARNING] {w}")
    for rec in r.get("recommendations", []):
        lines.append(f"  [RECOMMEND] {rec}")
    return "\n".join(lines)


def t3_env_guardrails(env_id: str) -> str:
    from runtime.tier3_env_guardrails import (
        list_guardrail_categories, get_guardrail_log,
    )

    cats = list_guardrail_categories()
    log = get_guardrail_log(10)
    env_log = [e for e in log if True]  # show all recent

    lines = [
        f"Guardrail categories ({len(cats)}): {', '.join(cats)}",
    ]
    if env_log:
        lines.append(f"Recent evaluations ({len(env_log)}):")
        for e in env_log[-5:]:
            status = "PASS" if e.get("allowed") else "BLOCK"
            n_block = len(e.get("blocking_reasons", []))
            n_warn = len(e.get("warnings", []))
            ts = e.get("timestamp", 0)
            lines.append(
                f"  {e.get('action', '?')}  {status}  "
                f"blockers={n_block} warnings={n_warn}  t={ts:.1f}"
            )
    else:
        lines.append("No recent evaluations.")
    return "\n".join(lines)


def t3_env_guardrail_check(action: str, parameters: dict) -> str:
    from runtime.tier3_env_guardrails import run_guardrail_check

    r = run_guardrail_check(action, parameters)
    status = "ALLOWED" if r.get("allowed") else "BLOCKED"
    lines = [f"Guardrail check: {action}  -> {status}"]
    for b in r.get("blocking_reasons", []):
        lines.append(f"  [BLOCKER] {b}")
    for w in r.get("warnings", []):
        lines.append(f"  [WARNING] {w}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Lineage & multi-environment orchestration
# ------------------------------------------------------------------

def t3_lineage(
    object_type: str | None = None,
    object_id: str | None = None,
) -> str:
    from runtime.tier3_lineage import get_lineage

    records = get_lineage(object_type=object_type, object_id=object_id)
    if not records:
        return "No lineage records found."

    lines = [f"Lineage ({len(records)} records):"]
    for r in records[-10:]:
        oid = r["object_id"][:12] if len(r["object_id"]) > 12 else r["object_id"]
        origin = r["origin_env_id"][:8]
        derived = r["derived_env_id"][:8]
        ts = r.get("timestamp", 0)
        lines.append(
            f"  {r['object_type']}  {oid}  "
            f"{origin}..→{derived}..  {r['operation']}  t={ts:.1f}"
        )
    return "\n".join(lines)


def t3_multi_env_path(
    source_env_id: str,
    target_env_id: str,
) -> str:
    from runtime.tier3_environments import get_promotion_path, get_environment

    result = get_promotion_path(source_env_id, target_env_id)
    if result.get("error"):
        return f"Path error: {result.get('reason', '?')}"

    path = result["path"]
    names = []
    for eid in path:
        env = get_environment(eid)
        names.append(env["name"] if env else eid[:8])

    return f"Promotion path ({len(path)} envs): {' -> '.join(names)}"


def t3_multi_env_compare(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_multi_env import compare_across_path

    report = compare_across_path(source_env_id, target_env_id, scope)
    if report.get("error"):
        return f"Compare error: {report.get('reason', '?')}"

    path = report.get("path", [])
    hops = report.get("hops", [])
    lines = [
        f"Multi-env comparison: {len(path)} envs, {len(hops)} hops, "
        f"scope={scope}"
    ]
    for h in hops:
        fr = h["from_env"][:8]
        to = h["to_env"][:8]
        comp = h.get("comparison", {})
        if comp.get("error"):
            lines.append(f"  {fr}..→{to}..  error")
        elif comp.get("comparisons"):
            for s, c in comp["comparisons"].items():
                n_src = len(c.get("only_in_source", []))
                n_tgt = len(c.get("only_in_target", []))
                lines.append(
                    f"  {fr}..→{to}..  {s}: "
                    f"only_source={n_src} only_target={n_tgt}"
                )
        else:
            n_src = len(comp.get("only_in_source", []))
            n_tgt = len(comp.get("only_in_target", []))
            lines.append(
                f"  {fr}..→{to}..  {comp.get('scope', '?')}: "
                f"only_source={n_src} only_target={n_tgt}"
            )
    return "\n".join(lines)


def t3_multi_env_promotion_plan(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_multi_env import generate_multi_env_promotion_plan

    plan = generate_multi_env_promotion_plan(
        source_env_id, target_env_id, scope)
    if plan.get("error"):
        return f"Plan error: {plan.get('reason', '?')}"

    n_hops = len(plan.get("hop_plans", []))
    n_ops = plan.get("total_operations", 0)
    n_gf = len(plan.get("guardrail_failures", []))
    pid = plan.get("multi_plan_id", "?")[:8]

    lines = [
        f"Multi-env plan: {pid}..  {n_hops} hops, {n_ops} operations",
        f"  path: {' -> '.join(e[:8] for e in plan.get('path', []))}",
    ]
    if n_gf:
        lines.append(f"  guardrail failures: {n_gf}")
    for h in plan.get("hop_plans", []):
        hp = h.get("plan", {})
        fr = h["from_env"][:8]
        to = h["to_env"][:8]
        ops = len(hp.get("operations", []))
        lines.append(f"  {fr}..→{to}..  ops={ops}")
    return "\n".join(lines)


def t3_multi_env_promotion_runbook(
    source_env_id: str,
    target_env_id: str,
    scope: str = "all",
) -> str:
    from runtime.tier3_multi_env import (
        generate_multi_env_promotion_plan,
        create_multi_env_promotion_runbook,
    )

    plan = generate_multi_env_promotion_plan(
        source_env_id, target_env_id, scope)
    if plan.get("error"):
        return f"Plan error: {plan.get('reason', '?')}"

    runbook = create_multi_env_promotion_runbook(plan)
    if runbook.get("error"):
        return f"Runbook error: {runbook.get('reason', '?')}"

    rid = runbook["runbook_id"][:8]
    n_steps = len(runbook.get("steps", []))
    n_hops = len(plan.get("hop_plans", []))
    return (
        f"Multi-env runbook created: {rid}.. (draft, {n_steps} steps)\n"
        f"  {n_hops} hops, {plan.get('total_operations', 0)} operations\n"
        f"  Execute with: t3_runbook_execute('{runbook['runbook_id']}')"
    )


# ------------------------------------------------------------------
# Governance snapshots
# ------------------------------------------------------------------

def t3_snapshot_create(label: str, description: str = "") -> str:
    from runtime.tier3_snapshots import create_snapshot

    result = create_snapshot(label, description)
    sid = result["snapshot_id"][:8]
    s = result.get("summary", {})
    return (
        f"Snapshot created: {sid}.. '{label}'\n"
        f"  envs={s.get('environments', 0)} profiles={s.get('profiles', 0)} "
        f"policies={s.get('policies', 0)} templates={s.get('templates', 0)} "
        f"runbooks={s.get('runbooks', 0)} packs={s.get('packs', 0)} "
        f"lineage={s.get('lineage', 0)}"
    )


def t3_snapshots() -> str:
    from runtime.tier3_snapshots import list_snapshots

    snaps = list_snapshots()
    if not snaps:
        return "No snapshots."

    lines = [f"Snapshots ({len(snaps)}):"]
    for s in snaps:
        sid = s["snapshot_id"][:8]
        sm = s.get("summary", {})
        total = sum(sm.values())
        ts = s.get("created_at", 0)
        lines.append(
            f"  {sid}..  '{s['label']}'  objects={total}  t={ts:.1f}"
        )
    return "\n".join(lines)


def t3_snapshot(snapshot_id: str) -> str:
    from runtime.tier3_snapshots import get_snapshot

    s = get_snapshot(snapshot_id)
    if s is None:
        return f"Snapshot '{snapshot_id}' not found."

    from runtime.tier3_snapshots import _summarize
    sm = _summarize(s["state"])
    lines = [
        f"Snapshot: {s['snapshot_id'][:8]}.. '{s['label']}'",
        f"  description: {s.get('description', '-')}",
        f"  created_at: {s['created_at']:.1f}",
    ]
    for k, v in sm.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_snapshot_diff(snapshot_a: str, snapshot_b: str) -> str:
    from runtime.tier3_snapshot_diff import diff_snapshots

    result = diff_snapshots(snapshot_a, snapshot_b)
    if result.get("error"):
        return f"Diff error: {result.get('reason', '?')}"
    return _format_diff(result, f"{snapshot_a[:8]}.. vs {snapshot_b[:8]}..")


def t3_snapshot_diff_current(snapshot_id: str) -> str:
    from runtime.tier3_snapshot_diff import diff_snapshot_to_current

    result = diff_snapshot_to_current(snapshot_id)
    if result.get("error"):
        return f"Diff error: {result.get('reason', '?')}"
    return _format_diff(result, f"{snapshot_id[:8]}.. vs current")


def _format_diff(result: dict, header: str) -> str:
    lines = [
        f"Diff: {header}  "
        f"changes={'YES' if result.get('has_changes') else 'none'}"
    ]
    dims = result.get("dimensions", {})
    for dim, d in dims.items():
        if dim == "lineage":
            ne = d.get("new_entries", 0)
            lines.append(
                f"  {dim}: a={d.get('count_a', 0)} b={d.get('count_b', 0)} "
                f"new={ne}"
            )
        else:
            added = d.get("added", [])
            removed = d.get("removed", [])
            changed = d.get("changed_count", 0)
            lines.append(
                f"  {dim}: +{len(added)} -{len(removed)} ~{changed}"
            )
    return "\n".join(lines)


# ------------------------------------------------------------------
# Governance audits
# ------------------------------------------------------------------

def t3_audit() -> str:
    from runtime.tier3_audit import generate_governance_audit

    r = generate_governance_audit()
    lines = [
        "Governance audit:",
        f"  environments={r.get('total_environments', 0)}  "
        f"profiles={r.get('total_profiles', 0)}  "
        f"policies={r.get('total_policies', 0)} "
        f"(enabled={r.get('enabled_policies', 0)}, "
        f"retired={r.get('retired_policies', 0)})",
        f"  templates={r.get('total_templates', 0)}  "
        f"runbooks={r.get('total_runbooks', 0)}  "
        f"packs={r.get('total_packs', 0)}",
        f"  lineage={r.get('total_lineage_records', 0)}  "
        f"snapshots={r.get('total_snapshots', 0)}",
    ]
    for h in r.get("environment_health", []):
        eid = h["env_id"][:8]
        lines.append(
            f"  env {eid}.. '{h.get('env_name', '?')}'  "
            f"grade={h.get('grade', '?')}  findings={h.get('findings', 0)}"
        )
    return "\n".join(lines)


def t3_audit_env(env_id: str) -> str:
    from runtime.tier3_audit import generate_environment_audit

    r = generate_environment_audit(env_id)
    if r.get("error"):
        return f"Audit error: {r.get('reason', '?')}"

    health = r.get("health", {})
    lines = [
        f"Environment audit: {env_id[:8]}.. '{r.get('env_name', '?')}'",
        f"  status={r.get('status', '?')}  "
        f"profiles={r.get('allowed_profiles', 0)}  "
        f"policies={r.get('allowed_policies', 0)}  "
        f"templates={r.get('allowed_templates', 0)}",
        f"  default_policies={r.get('default_policies', 0)}  "
        f"packs={r.get('applied_packs', 0)}  "
        f"lineage={r.get('lineage_records', 0)}",
        f"  health: {health.get('grade', '?')} "
        f"({len(health.get('findings', []))} findings)",
    ]
    for pv in r.get("pack_validation", []):
        pid = pv["pack_id"][:8]
        v = "OK" if pv.get("valid") else f"{pv.get('issues', 0)} issues"
        lines.append(f"  pack {pid}..  {v}")
    return "\n".join(lines)


def t3_audit_policy(policy_id: str) -> str:
    from runtime.tier3_audit import generate_policy_audit

    r = generate_policy_audit(policy_id)
    if r.get("error"):
        return f"Audit error: {r.get('reason', '?')}"

    lines = [
        f"Policy audit: '{r.get('name', '?')}'",
        f"  enabled={r.get('enabled')}  retired={r.get('retired')}  "
        f"conditions={r.get('conditions', 0)}  actions={r.get('actions', 0)}",
        f"  environments: {len(r.get('present_in_environments', []))}  "
        f"lineage: {r.get('lineage_records', 0)}",
    ]
    return "\n".join(lines)


def t3_audit_profile(profile_id: str) -> str:
    from runtime.tier3_audit import generate_profile_audit

    r = generate_profile_audit(profile_id)
    if r.get("error"):
        return f"Audit error: {r.get('reason', '?')}"

    lines = [
        f"Profile audit: '{r.get('name', '?')}'",
        f"  status={r.get('status', '?')}  "
        f"policies={r.get('attached_policies', 0)}  "
        f"overrides={r.get('scheduling_overrides', 0)}",
        f"  environments: {len(r.get('present_in_environments', []))}  "
        f"lineage: {r.get('lineage_records', 0)}",
    ]
    return "\n".join(lines)


def t3_audit_template(template_id: str) -> str:
    from runtime.tier3_audit import generate_template_audit

    r = generate_template_audit(template_id)
    if r.get("error"):
        return f"Audit error: {r.get('reason', '?')}"

    lines = [
        f"Template audit: '{r.get('name', '?')}'",
        f"  parameters={r.get('parameters', 0)}  "
        f"steps={r.get('steps', 0)}",
        f"  environments: {len(r.get('present_in_environments', []))}  "
        f"lineage: {r.get('lineage_records', 0)}",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------
# Forecasting & anomaly detection
# ------------------------------------------------------------------

def t3_forecast_env(env_id: str, horizon: int = 5) -> str:
    from runtime.tier3_forecast import forecast_environment_drift

    r = forecast_environment_drift(env_id, horizon)
    lines = [
        f"Drift forecast: {env_id[:8]}..  horizon={horizon}",
        f"  prediction={r['prediction']}  confidence={r['confidence']}",
        f"  drift_trend={r['drift_trend']}  health_trend={r['health_trend']}",
        f"  samples={r['samples']}",
    ]
    for f in r.get("factors", []):
        lines.append(f"  • {f}")
    return "\n".join(lines)


def t3_forecast_policy(policy_id: str, horizon: int = 5) -> str:
    from runtime.tier3_forecast import forecast_policy_activity

    r = forecast_policy_activity(policy_id, horizon)
    lines = [
        f"Policy forecast: {policy_id[:12]}  horizon={horizon}",
        f"  prediction={r['prediction']}  confidence={r['confidence']}",
        f"  trigger_trend={r['trigger_trend']}  "
        f"trigger_rate={r['trigger_rate']:.1%}",
        f"  samples={r['samples']}",
    ]
    for f in r.get("factors", []):
        lines.append(f"  • {f}")
    return "\n".join(lines)


def t3_forecast_promotion(
    source_env_id: str,
    target_env_id: str,
    horizon: int = 5,
) -> str:
    from runtime.tier3_forecast import forecast_promotion_readiness

    r = forecast_promotion_readiness(source_env_id, target_env_id, horizon)
    src = source_env_id[:8]
    tgt = target_env_id[:8]
    score_str = str(r["current_score"]) if r["current_score"] is not None else "?"
    lines = [
        f"Promotion forecast: {src}.. -> {tgt}..  horizon={horizon}",
        f"  prediction={r['prediction']}  confidence={r['confidence']}",
        f"  score_trend={r['score_trend']}  blocker_trend={r['blocker_trend']}",
        f"  current_score={score_str}  samples={r['samples']}",
    ]
    for f in r.get("factors", []):
        lines.append(f"  • {f}")
    return "\n".join(lines)


def t3_anomalies() -> str:
    from runtime.tier3_anomaly import detect_all_anomalies

    r = detect_all_anomalies()
    if r["total"] == 0:
        return "No anomalies detected."

    lines = [
        f"Anomalies detected: {r['total']}  "
        f"(policy={r['policy']} env={r['environment']} "
        f"pack={r['pack']} lineage={r['lineage']})"
    ]
    for a in r["anomalies"][:15]:
        sev = a.get("severity", "?")
        lines.append(f"  [{sev}] {a.get('anomaly_type', '?')}: {a.get('detail', '?')}")
    return "\n".join(lines)


def t3_anomaly_detail(insight_id: str) -> str:
    from runtime.tier3_anomaly import get_governance_insight

    i = get_governance_insight(insight_id)
    if i is None:
        return f"Insight '{insight_id}' not found."

    lines = [
        f"Insight: {i['insight_id'][:8]}..  type={i['insight_type']}",
        f"  summary: {i['summary']}",
        f"  related: {i.get('related_ids', [])}",
        f"  timestamp: {i.get('timestamp', 0):.1f}",
    ]
    details = i.get("details", {})
    for k, v in details.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_governance_insights() -> str:
    from runtime.tier3_anomaly import get_governance_insights

    insights = get_governance_insights()
    if not insights:
        return "No governance insights."

    lines = [f"Governance insights ({len(insights)}):"]
    for i in insights[-10:]:
        iid = i["insight_id"][:8]
        itype = i["insight_type"]
        ts = i.get("timestamp", 0)
        lines.append(f"  {iid}..  [{itype}] {i['summary'][:60]}  t={ts:.1f}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 54 — Strategic modeling, optimization, simulation
# ------------------------------------------------------------------


def t3_strategy(horizon: int = 10) -> str:
    from runtime.tier3_strategy import model_governance_trajectory

    r = model_governance_trajectory(horizon)
    projs = r.get("projections", [])
    lines = [
        f"Governance trajectory (horizon={horizon}, "
        f"confidence={r.get('confidence', '?')}):"
    ]
    for p in projs:
        lines.append(f"  {p['projection']}: {p.get('detail', '')}")
    if r.get("factors"):
        lines.append(f"Factors: {', '.join(r['factors'])}")
    return "\n".join(lines)


def t3_strategy_env(env_id: str, horizon: int = 10) -> str:
    from runtime.tier3_strategy import model_environment_evolution

    r = model_environment_evolution(env_id, horizon)
    if r.get("error"):
        return r["reason"]
    projs = r.get("projections", [])
    lines = [
        f"Env '{r.get('env_name', '?')}' evolution "
        f"(horizon={horizon}, confidence={r.get('confidence', '?')}):"
    ]
    for p in projs:
        lines.append(f"  {p['projection']}: {p.get('detail', '')}")
    if r.get("factors"):
        lines.append(f"Factors: {', '.join(r['factors'])}")
    return "\n".join(lines)


def t3_strategy_policy(policy_id: str, horizon: int = 10) -> str:
    from runtime.tier3_strategy import model_policy_lifecycle

    r = model_policy_lifecycle(policy_id, horizon)
    if r.get("error"):
        return r["reason"]
    projs = r.get("projections", [])
    lines = [
        f"Policy '{r.get('policy_name', '?')}' lifecycle "
        f"(horizon={horizon}, confidence={r.get('confidence', '?')}):"
    ]
    for p in projs:
        lines.append(f"  {p['projection']}: {p.get('detail', '')}")
    if r.get("factors"):
        lines.append(f"Factors: {', '.join(r['factors'])}")
    return "\n".join(lines)


def t3_optimize() -> str:
    from runtime.tier3_strategy import suggest_governance_optimizations

    r = suggest_governance_optimizations()
    suggestions = r.get("suggestions", [])
    if not suggestions:
        return "No optimization suggestions."
    lines = [f"Governance optimizations ({len(suggestions)}):"]
    for s in suggestions:
        lines.append(f"  [{s['category']}] {s['suggestion']}")
    return "\n".join(lines)


def t3_optimize_env(env_id: str) -> str:
    from runtime.tier3_strategy import suggest_environment_optimizations

    r = suggest_environment_optimizations(env_id)
    if r.get("error"):
        return r["reason"]
    suggestions = r.get("suggestions", [])
    if not suggestions:
        return f"No optimizations for environment '{r.get('env_name', '?')}'."
    lines = [
        f"Optimizations for '{r.get('env_name', '?')}' ({len(suggestions)}):"
    ]
    for s in suggestions:
        lines.append(f"  [{s['category']}] {s['suggestion']}")
    return "\n".join(lines)


def t3_optimize_policy(policy_id: str) -> str:
    from runtime.tier3_strategy import suggest_policy_optimizations

    r = suggest_policy_optimizations(policy_id)
    if r.get("error"):
        return r["reason"]
    suggestions = r.get("suggestions", [])
    if not suggestions:
        return f"No optimizations for policy '{r.get('policy_name', '?')}'."
    lines = [
        f"Optimizations for '{r.get('policy_name', '?')}' ({len(suggestions)}):"
    ]
    for s in suggestions:
        lines.append(f"  [{s['category']}] {s['suggestion']}")
    return "\n".join(lines)


def t3_simulate_policy(
    policy_id: str,
    hypothetical_changes: dict | None = None,
) -> str:
    from runtime.tier3_scenario_sim import simulate_policy_change

    r = simulate_policy_change(policy_id, hypothetical_changes or {})
    if r.get("error"):
        return r["reason"]
    impacts = r.get("impacts", [])
    lines = [f"Simulated policy change for '{r.get('policy_name', '?')}':"]
    for i in impacts:
        lines.append(f"  {i['impact']}: {i.get('detail', '')}")
    lines.append(f"Environments affected: {r.get('environments_affected', 0)}")
    return "\n".join(lines)


def t3_simulate_pack(
    pack_id: str,
    hypothetical_changes: dict | None = None,
) -> str:
    from runtime.tier3_scenario_sim import simulate_pack_change

    r = simulate_pack_change(pack_id, hypothetical_changes or {})
    if r.get("error"):
        return r["reason"]
    impacts = r.get("impacts", [])
    lines = [f"Simulated pack change for '{r.get('pack_name', '?')}':"]
    for i in impacts:
        lines.append(f"  {i['impact']}: {i.get('detail', '')}")
    lines.append(f"Environments affected: {r.get('environments_affected', 0)}")
    return "\n".join(lines)


def t3_simulate_env(
    env_id: str,
    hypothetical_changes: dict | None = None,
) -> str:
    from runtime.tier3_scenario_sim import simulate_environment_change

    r = simulate_environment_change(env_id, hypothetical_changes or {})
    if r.get("error"):
        return r["reason"]
    impacts = r.get("impacts", [])
    lines = [f"Simulated env change for '{r.get('env_name', '?')}':"]
    for i in impacts:
        lines.append(f"  {i['impact']}: {i.get('detail', '')}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 55 — Governance planning, strategic runbooks, plan simulation
# ------------------------------------------------------------------


def t3_plan(horizon: int = 10) -> str:
    from runtime.tier3_planning import generate_governance_plan

    r = generate_governance_plan(horizon)
    phases = r.get("phases", [])
    lines = [
        f"Governance plan {r['plan_id'][:8]}.. "
        f"(horizon={horizon}, {len(phases)} phase(s), "
        f"confidence={r.get('confidence', '?')}):"
    ]
    for p in phases:
        lines.append(f"  Phase {p['phase']}: {p['goal']}")
        for a in p.get("recommended_actions", [])[:3]:
            lines.append(f"    - [{a.get('action', '?')}] {a.get('detail', '')[:60]}")
    if r.get("risk_considerations"):
        lines.append(f"Risks: {'; '.join(r['risk_considerations'][:3])}")
    return "\n".join(lines)


def t3_plan_env(env_id: str, horizon: int = 10) -> str:
    from runtime.tier3_planning import generate_environment_plan

    r = generate_environment_plan(env_id, horizon)
    if r.get("error"):
        return r["reason"]
    phases = r.get("phases", [])
    lines = [
        f"Env plan {r['plan_id'][:8]}.. for '{r.get('scope_name', '?')}' "
        f"(horizon={horizon}, {len(phases)} phase(s), "
        f"confidence={r.get('confidence', '?')}):"
    ]
    for p in phases:
        lines.append(f"  Phase {p['phase']}: {p['goal']}")
        for a in p.get("recommended_actions", [])[:3]:
            lines.append(f"    - [{a.get('action', '?')}] {a.get('detail', '')[:60]}")
    return "\n".join(lines)


def t3_plan_policy(policy_id: str, horizon: int = 10) -> str:
    from runtime.tier3_planning import generate_policy_plan

    r = generate_policy_plan(policy_id, horizon)
    if r.get("error"):
        return r["reason"]
    phases = r.get("phases", [])
    lines = [
        f"Policy plan {r['plan_id'][:8]}.. for '{r.get('scope_name', '?')}' "
        f"(horizon={horizon}, {len(phases)} phase(s), "
        f"confidence={r.get('confidence', '?')}):"
    ]
    for p in phases:
        lines.append(f"  Phase {p['phase']}: {p['goal']}")
        for a in p.get("recommended_actions", [])[:3]:
            lines.append(f"    - [{a.get('action', '?')}] {a.get('detail', '')[:60]}")
    return "\n".join(lines)


def t3_plan_detail(plan_id: str) -> str:
    from runtime.tier3_planning import get_governance_plan

    plan = get_governance_plan(plan_id)
    if plan is None:
        return f"Plan '{plan_id}' not found."
    lines = [
        f"Plan {plan['plan_id'][:8]}..  scope={plan.get('scope', '?')}  "
        f"horizon={plan.get('horizon', '?')}  "
        f"confidence={plan.get('confidence', '?')}"
    ]
    for p in plan.get("phases", []):
        lines.append(f"  Phase {p['phase']}: {p['goal']}")
        lines.append(f"    Rationale: {p.get('rationale', '?')}")
        for a in p.get("recommended_actions", []):
            lines.append(f"    - [{a.get('action', '?')}] {a.get('detail', '')}")
    deps = plan.get("dependencies", [])
    if deps:
        dep_str = ", ".join(
            f"phase {d['phase']} -> phase {d['depends_on']}" for d in deps
        )
        lines.append(f"Dependencies: {dep_str}")
    risks = plan.get("risk_considerations", [])
    if risks:
        lines.append(f"Risks: {'; '.join(risks)}")
    return "\n".join(lines)


def t3_plan_runbook(plan_id: str) -> str:
    from runtime.tier3_planning import generate_strategic_runbook

    r = generate_strategic_runbook(plan_id)
    if r.get("error"):
        return r.get("reason", "unknown error")
    rid = r.get("runbook_id", "?")[:8]
    n = len(r.get("steps", []))
    return (
        f"Strategic runbook {rid}.. created (draft) from plan "
        f"{plan_id[:8]}.. with {n} step(s)."
    )


def t3_plan_simulate(plan_id: str) -> str:
    from runtime.tier3_planning_sim import simulate_plan_impact

    r = simulate_plan_impact(plan_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Plan {plan_id[:8]}.. impact simulation "
        f"(confidence={r.get('confidence', '?')}):"
    ]
    lines.append(
        f"  Drift reduction: ~{r.get('estimated_drift_reduction_pct', 0)}%"
    )
    lines.append(
        f"  Readiness improvement: ~{r.get('estimated_readiness_improvement_pct', 0)}%"
    )
    lines.append(
        f"  Anomaly reduction: ~{r.get('estimated_anomaly_reduction_pct', 0)}%"
    )
    risks = r.get("risk_tradeoffs", [])
    if risks:
        lines.append(f"  Risks: {'; '.join(risks[:3])}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 56 — KPIs, scorecards, strategic dashboard
# ------------------------------------------------------------------


def t3_kpis() -> str:
    from runtime.tier3_kpis import compute_system_kpis

    r = compute_system_kpis()
    kpis = r.get("kpis", {})
    lines = [
        f"System KPIs ({r.get('n_environments', 0)} envs, "
        f"{r.get('n_policies', 0)} policies, "
        f"{r.get('n_anomalies', 0)} anomalies):"
    ]
    for k, v in kpis.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_kpis_env(env_id: str) -> str:
    from runtime.tier3_kpis import compute_environment_kpis

    r = compute_environment_kpis(env_id)
    if r.get("error"):
        return r["reason"]
    kpis = r.get("kpis", {})
    lines = [f"Env '{r.get('env_name', '?')}' KPIs:"]
    for k, v in kpis.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_kpis_policy(policy_id: str) -> str:
    from runtime.tier3_kpis import compute_policy_kpis

    r = compute_policy_kpis(policy_id)
    if r.get("error"):
        return r["reason"]
    kpis = r.get("kpis", {})
    lines = [f"Policy '{r.get('policy_name', '?')}' KPIs:"]
    for k, v in kpis.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_scorecard() -> str:
    from runtime.tier3_scorecards import generate_system_scorecard

    r = generate_system_scorecard()
    lines = [f"System scorecard: {r.get('grade', '?')} ({r.get('score', '?')}/100)"]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    kpis = r.get("kpis", {})
    if kpis:
        lines.append("KPIs:")
        for k, v in kpis.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_scorecard_env(env_id: str) -> str:
    from runtime.tier3_scorecards import generate_environment_scorecard

    r = generate_environment_scorecard(env_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' scorecard: "
        f"{r.get('grade', '?')} ({r.get('score', '?')}/100)"
    ]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    return "\n".join(lines)


def t3_scorecard_policy(policy_id: str) -> str:
    from runtime.tier3_scorecards import generate_policy_scorecard

    r = generate_policy_scorecard(policy_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Policy '{r.get('policy_name', '?')}' scorecard: "
        f"{r.get('grade', '?')} ({r.get('score', '?')}/100)"
    ]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    return "\n".join(lines)


def t3_dashboard() -> str:
    from runtime.tier3_strategic_dashboard import build_strategic_dashboard

    d = build_strategic_dashboard()
    sc = d.get("system_scorecard") or {}
    lines = [
        f"Strategic dashboard  grade={sc.get('grade', '?')}  "
        f"score={sc.get('score', '?')}/100"
    ]

    sk = d.get("system_kpis") or {}
    kpis = sk.get("kpis", {})
    if kpis:
        lines.append("System KPIs:")
        for k, v in kpis.items():
            lines.append(f"  {k}: {v}")

    plans = d.get("recent_plans") or []
    if plans:
        lines.append(f"Recent plans ({len(plans)}):")
        for p in plans[-3:]:
            pid = p.get("plan_id", "?")[:8]
            scope = p.get("scope", "?")
            lines.append(f"  {pid}..  scope={scope}")

    anomalies = d.get("recent_anomalies") or []
    if anomalies:
        lines.append(f"Recent anomalies ({len(anomalies)}):")
        for a in anomalies[-3:]:
            lines.append(f"  [{a.get('severity', '?')}] {a.get('detail', '?')[:50]}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 57 — SLAs, risk, heatmaps, executive reporting
# ------------------------------------------------------------------


def t3_sla() -> str:
    from runtime.tier3_sla import evaluate_system_sla

    r = evaluate_system_sla()
    status = "PASS" if r.get("passed") else "FAIL"
    lines = [f"System SLA: {status} ({r.get('failures', 0)} failure(s))"]
    for c in r.get("checks", []):
        mark = "ok" if c["passed"] else "FAIL"
        lines.append(f"  [{mark}] {c['metric']}: {c['value']} {c['op']} {c['threshold']}")
    if r.get("warnings"):
        lines.append(f"Warnings: {', '.join(r['warnings'])}")
    return "\n".join(lines)


def t3_sla_env(env_id: str) -> str:
    from runtime.tier3_sla import evaluate_environment_sla

    r = evaluate_environment_sla(env_id)
    if r.get("error"):
        return r["reason"]
    status = "PASS" if r.get("passed") else "FAIL"
    lines = [
        f"Env '{r.get('env_name', '?')}' SLA: {status} "
        f"({r.get('failures', 0)} failure(s))"
    ]
    for c in r.get("checks", []):
        mark = "ok" if c["passed"] else "FAIL"
        lines.append(f"  [{mark}] {c['metric']}: {c['value']} {c['op']} {c['threshold']}")
    return "\n".join(lines)


def t3_sla_policy(policy_id: str) -> str:
    from runtime.tier3_sla import evaluate_policy_sla

    r = evaluate_policy_sla(policy_id)
    if r.get("error"):
        return r["reason"]
    status = "PASS" if r.get("passed") else "FAIL"
    lines = [
        f"Policy '{r.get('policy_name', '?')}' SLA: {status} "
        f"({r.get('failures', 0)} failure(s))"
    ]
    for c in r.get("checks", []):
        mark = "ok" if c["passed"] else "FAIL"
        lines.append(f"  [{mark}] {c['metric']}: {c['value']} {c['op']} {c['threshold']}")
    return "\n".join(lines)


def t3_risk() -> str:
    from runtime.tier3_risk import compute_system_risk

    r = compute_system_risk()
    lines = [
        f"System risk: {r.get('risk_tier', '?')} ({r.get('risk_score', '?')}/100)"
    ]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    return "\n".join(lines)


def t3_risk_env(env_id: str) -> str:
    from runtime.tier3_risk import compute_environment_risk

    r = compute_environment_risk(env_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' risk: "
        f"{r.get('risk_tier', '?')} ({r.get('risk_score', '?')}/100)"
    ]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    return "\n".join(lines)


def t3_risk_policy(policy_id: str) -> str:
    from runtime.tier3_risk import compute_policy_risk

    r = compute_policy_risk(policy_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Policy '{r.get('policy_name', '?')}' risk: "
        f"{r.get('risk_tier', '?')} ({r.get('risk_score', '?')}/100)"
    ]
    for f in r.get("factors", []):
        lines.append(f"  - {f}")
    return "\n".join(lines)


def t3_heatmap() -> str:
    from runtime.tier3_heatmap import generate_system_heatmap

    r = generate_system_heatmap()
    cells = r.get("cells", [])
    lines = [
        f"System heatmap: {len(cells)} env(s), "
        f"{r.get('n_hot', 0)} hot/critical"
    ]
    for c in cells:
        dims = c.get("dimensions", {})
        dim_str = "  ".join(f"{k}={v}" for k, v in dims.items())
        lines.append(f"  [{c['heat']}] {c['env_name']}  {dim_str}")
    return "\n".join(lines)


def t3_heatmap_env(env_id: str) -> str:
    from runtime.tier3_heatmap import generate_environment_heatmap

    r = generate_environment_heatmap(env_id)
    if r.get("error"):
        return r["reason"]
    dims = r.get("dimensions", {})
    lines = [
        f"Env '{r.get('env_name', '?')}' heatmap: [{r.get('heat', '?')}]  "
        f"risk={r.get('risk_score', '?')}"
    ]
    for k, v in dims.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def t3_exec_report() -> str:
    from runtime.tier3_exec_report import generate_executive_report

    r = generate_executive_report()
    h = r.get("headline", {})
    lines = [
        f"Executive report  grade={h.get('grade', '?')}  "
        f"SLA={h.get('sla_status', '?')}  risk={h.get('risk_tier', '?')}"
    ]

    sk = r.get("system_kpis") or {}
    kpis = sk.get("kpis", {})
    if kpis:
        lines.append("KPIs:")
        for k, v in kpis.items():
            lines.append(f"  {k}: {v}")

    hm = r.get("system_heatmap") or {}
    cells = hm.get("cells", [])
    if cells:
        lines.append(f"Heatmap: {len(cells)} env(s), {hm.get('n_hot', 0)} hot/critical")

    plans = r.get("recent_plans") or []
    if plans:
        lines.append(f"Plans: {len(plans)}")

    anomalies = r.get("recent_anomalies") or []
    if anomalies:
        lines.append(f"Anomalies: {len(anomalies)}")

    lineage = r.get("recent_lineage") or []
    if lineage:
        lines.append(f"Lineage records: {len(lineage)}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 58 — Benchmarking, maturity, comparisons
# ------------------------------------------------------------------


def t3_benchmark() -> str:
    from runtime.tier3_benchmark import benchmark_system

    r = benchmark_system()
    lines = [
        f"System benchmark: {r.get('scorecard_grade', '?')} "
        f"({r.get('scorecard_score', '?')}/100)  "
        f"risk={r.get('risk_tier', '?')}"
    ]
    metrics = r.get("metrics", {})
    for k, m in metrics.items():
        lines.append(
            f"  {k}: {m['current']}  avg={m['historical_avg']}  "
            f"trend={m['trend']}  pct={m['percentile']}"
        )
    if r.get("strengths"):
        lines.append(f"Strengths: {', '.join(r['strengths'])}")
    if r.get("weaknesses"):
        lines.append(f"Weaknesses: {', '.join(r['weaknesses'])}")
    return "\n".join(lines)


def t3_benchmark_env(env_id: str) -> str:
    from runtime.tier3_benchmark import benchmark_environment

    r = benchmark_environment(env_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' benchmark: "
        f"{r.get('scorecard_grade', '?')} ({r.get('scorecard_score', '?')}/100)"
    ]
    for k, m in r.get("metrics", {}).items():
        lines.append(
            f"  {k}: {m['current']}  avg={m['historical_avg']}  "
            f"trend={m['trend']}"
        )
    if r.get("strengths"):
        lines.append(f"Strengths: {', '.join(r['strengths'])}")
    if r.get("weaknesses"):
        lines.append(f"Weaknesses: {', '.join(r['weaknesses'])}")
    return "\n".join(lines)


def t3_benchmark_policy(policy_id: str) -> str:
    from runtime.tier3_benchmark import benchmark_policy

    r = benchmark_policy(policy_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Policy '{r.get('policy_name', '?')}' benchmark: "
        f"{r.get('scorecard_grade', '?')} ({r.get('scorecard_score', '?')}/100)"
    ]
    for k, m in r.get("metrics", {}).items():
        lines.append(
            f"  {k}: {m['current']}  avg={m['historical_avg']}  "
            f"trend={m['trend']}"
        )
    return "\n".join(lines)


def t3_maturity() -> str:
    from runtime.tier3_maturity import compute_system_maturity

    r = compute_system_maturity()
    lines = [
        f"System maturity: {r.get('maturity_tier', '?')} "
        f"({r.get('maturity_score', '?')}/100)"
    ]
    for k, v in r.get("dimension_scores", {}).items():
        lines.append(f"  {k}: {v}")
    if r.get("contributing_factors"):
        lines.append(f"Factors: {', '.join(r['contributing_factors'])}")
    if r.get("recommended_focus"):
        lines.append(f"Focus: {', '.join(r['recommended_focus'])}")
    return "\n".join(lines)


def t3_maturity_env(env_id: str) -> str:
    from runtime.tier3_maturity import compute_environment_maturity

    r = compute_environment_maturity(env_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' maturity: "
        f"{r.get('maturity_tier', '?')} ({r.get('maturity_score', '?')}/100)"
    ]
    for k, v in r.get("dimension_scores", {}).items():
        lines.append(f"  {k}: {v}")
    if r.get("recommended_focus"):
        lines.append(f"Focus: {', '.join(r['recommended_focus'])}")
    return "\n".join(lines)


def t3_maturity_policy(policy_id: str) -> str:
    from runtime.tier3_maturity import compute_policy_maturity

    r = compute_policy_maturity(policy_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Policy '{r.get('policy_name', '?')}' maturity: "
        f"{r.get('maturity_tier', '?')} ({r.get('maturity_score', '?')}/100)"
    ]
    for k, v in r.get("dimension_scores", {}).items():
        lines.append(f"  {k}: {v}")
    if r.get("recommended_focus"):
        lines.append(f"Focus: {', '.join(r['recommended_focus'])}")
    return "\n".join(lines)


def t3_compare_env(env_a_id: str, env_b_id: str) -> str:
    from runtime.tier3_comparison import compare_environments

    r = compare_environments(env_a_id, env_b_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Comparison: '{r.get('env_a_name', '?')}' vs "
        f"'{r.get('env_b_name', '?')}'"
    ]
    for k, d in r.get("kpi_deltas", {}).items():
        lines.append(f"  {k}: A={d['a']}  B={d['b']}  delta={d['delta']}")
    rd = r.get("risk_deltas", {})
    if rd:
        lines.append(f"  risk: A={rd.get('a', '?')}  B={rd.get('b', '?')}  delta={rd.get('delta', '?')}")
    md = r.get("maturity_deltas", {})
    if md:
        lines.append(f"  maturity: A={md.get('a', '?')}  B={md.get('b', '?')}  delta={md.get('delta', '?')}")
    return "\n".join(lines)


def t3_compare_env_baseline(env_id: str, snapshot_id: str) -> str:
    from runtime.tier3_comparison import compare_environment_to_baseline

    r = compare_environment_to_baseline(env_id, snapshot_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' vs snapshot {snapshot_id[:8]}.."
    ]
    if r.get("baseline_note"):
        lines.append(f"  Note: {r['baseline_note']}")
    for k, d in r.get("kpi_deltas", {}).items():
        lines.append(f"  {k}: now={d['a']}  baseline={d['b']}  delta={d['delta']}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 59 — Objectives, alignment, meta-governance
# ------------------------------------------------------------------


def t3_objective_create(
    name: str,
    description: str,
    targets: Dict[str, Any] | None = None,
    target_maturity_tier: str | None = None,
    target_risk_tier: str | None = None,
    target_sla_pass_rate: float | None = None,
) -> str:
    from runtime.tier3_objectives import create_objective

    obj = create_objective(
        name=name,
        description=description,
        target_metrics=targets,
        target_maturity_tier=target_maturity_tier,
        target_risk_tier=target_risk_tier,
        target_sla_pass_rate=target_sla_pass_rate,
    )
    return f"Objective created: {obj['objective_id'][:8]}.. '{obj['name']}'"


def t3_objectives() -> str:
    from runtime.tier3_objectives import list_objectives

    objs = list_objectives()
    if not objs:
        return "No governance objectives defined."
    lines = [f"Governance objectives ({len(objs)}):"]
    for o in objs:
        lines.append(
            f"  {o['objective_id'][:8]}.. '{o['name']}'  {o['description'][:60]}"
        )
    return "\n".join(lines)


def t3_objective(objective_id: str) -> str:
    from runtime.tier3_objectives import get_objective

    o = get_objective(objective_id)
    if not o:
        return f"Objective '{objective_id}' not found."
    lines = [f"Objective: {o['name']}"]
    lines.append(f"  ID: {o['objective_id']}")
    lines.append(f"  Description: {o['description']}")
    tm = o.get("target_metrics") or {}
    if tm:
        lines.append(f"  Target metrics: {tm}")
    if o.get("target_maturity_tier"):
        lines.append(f"  Target maturity: {o['target_maturity_tier']}")
    if o.get("target_risk_tier"):
        lines.append(f"  Target risk: {o['target_risk_tier']}")
    if o.get("target_sla_pass_rate") is not None:
        lines.append(f"  Target SLA pass rate: {o['target_sla_pass_rate']}")
    return "\n".join(lines)


def t3_alignment(objective_id: str) -> str:
    from runtime.tier3_alignment import evaluate_system_alignment

    r = evaluate_system_alignment(objective_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"System alignment to '{r.get('objective_name', '?')}': "
        f"{r.get('alignment_score', '?')}/100  "
        f"({r.get('checks_met', 0)}/{r.get('checks_total', 0)} met)"
    ]
    for g in r.get("blocking_gaps", []):
        lines.append(
            f"  GAP {g.get('metric', '?')}: "
            f"current={g.get('current')} target={g.get('target')}"
        )
    if r.get("recommended_focus"):
        lines.append(f"Focus: {', '.join(r['recommended_focus'])}")
    return "\n".join(lines)


def t3_alignment_env(env_id: str, objective_id: str) -> str:
    from runtime.tier3_alignment import evaluate_environment_alignment

    r = evaluate_environment_alignment(env_id, objective_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Env '{r.get('env_name', '?')}' alignment to "
        f"'{r.get('objective_name', '?')}': "
        f"{r.get('alignment_score', '?')}/100"
    ]
    for g in r.get("blocking_gaps", []):
        lines.append(
            f"  GAP {g.get('metric', '?')}: "
            f"current={g.get('current')} target={g.get('target')}"
        )
    if r.get("recommended_focus"):
        lines.append(f"Focus: {', '.join(r['recommended_focus'])}")
    return "\n".join(lines)


def t3_alignment_policy(policy_id: str, objective_id: str) -> str:
    from runtime.tier3_alignment import evaluate_policy_alignment

    r = evaluate_policy_alignment(policy_id, objective_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Policy '{r.get('policy_name', '?')}' alignment to "
        f"'{r.get('objective_name', '?')}': "
        f"{r.get('alignment_score', '?')}/100"
    ]
    for g in r.get("blocking_gaps", []):
        lines.append(
            f"  GAP {g.get('metric', '?')}: "
            f"current={g.get('current')} target={g.get('target')}"
        )
    return "\n".join(lines)


def t3_objective_trajectory(objective_id: str, horizon: str = "30d") -> str:
    from runtime.tier3_meta_model import model_objective_trajectory

    r = model_objective_trajectory(objective_id, horizon)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Objective '{r.get('objective_name', '?')}' trajectory ({horizon}): "
        f"{r.get('trajectory', '?')}  confidence={r.get('confidence', '?')}  "
        f"alignment={r.get('current_alignment', '?')}/100"
    ]
    if r.get("structural_blockers"):
        lines.append("Blockers:")
        for b in r["structural_blockers"]:
            lines.append(f"  - {b}")
    return "\n".join(lines)


def t3_objective_feasibility(objective_id: str) -> str:
    from runtime.tier3_meta_model import model_objective_feasibility

    r = model_objective_feasibility(objective_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Objective '{r.get('objective_name', '?')}' feasibility: "
        f"{r.get('feasibility', '?')}"
    ]
    if r.get("structural_issues"):
        lines.append("Issues:")
        for i in r["structural_issues"]:
            lines.append(f"  - {i}")
    if r.get("structural_strengths"):
        lines.append("Strengths:")
        for s in r["structural_strengths"]:
            lines.append(f"  + {s}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Identity introspection
# ------------------------------------------------------------------


def identity_introspect() -> str:
    from runtime.self_description import describe_current_state
    s = describe_current_state()
    lines = ["Identity introspection:"]
    lines.append(f"  Posture: {s.get('posture_id', '?')}")
    lines.append(f"  Tier: {s.get('autonomy_tier', '?')}")
    oc = s.get("operator_context") or {}
    lines.append(f"  Intent: {oc.get('interaction_intent', '?')}  "
                 f"Focus: {oc.get('operator_focus_level', '?')}  "
                 f"Style: {oc.get('operator_engagement_style', '?')}")
    cs = s.get("continuity_state") or {}
    lines.append(f"  Continuity: {cs.get('continuity_strength', '?')} "
                 f"(active={cs.get('continuity_active', '?')})")
    coh = s.get("coherence_state") or {}
    lines.append(f"  Coherence: {coh.get('coherence_score', '?')}/100 "
                 f"(mismatches={coh.get('mismatches', 0)})")
    ss = s.get("stability_state") or {}
    lines.append(f"  Stability: {ss.get('stability_score', '?')}/100 "
                 f"osc={ss.get('oscillation_index', '?')} "
                 f"jit={ss.get('jitter_index', '?')}")
    rs = s.get("resonance_state") or {}
    lines.append(f"  Resonance: intensity={rs.get('intensity', '?')} "
                 f"color={rs.get('color', '?')} "
                 f"blend={rs.get('blend_factor', '?')}")
    gs = s.get("governance_state") or {}
    lines.append(f"  Governance: score={gs.get('governance_score', '?')}")
    if s.get("suppressed"):
        lines.append("  [posture-suppressed: some layers inactive]")
    return "\n".join(lines)


def identity_layers() -> str:
    from runtime.self_description import (
        describe_posture, describe_autonomy, describe_governance,
        describe_expression_stack,
    )
    from runtime.self_description import (
        _safe_operator_context, _safe_continuity_state,
        _safe_coherence_state, _safe_stability_state, _safe_resonance_state,
    )
    lines = ["Identity layers:"]

    p = describe_posture()
    lines.append(f"  Posture: {p.get('posture_id', '?')} ({p.get('name', '?')})")

    a = describe_autonomy()
    lines.append(f"  Autonomy: {a.get('tier_id', '?')} ({a.get('tier_name', '?')})")

    oc = _safe_operator_context()
    lines.append(f"  Operator: intent={oc.get('interaction_intent', '?')} "
                 f"focus={oc.get('operator_focus_level', '?')}")

    cs = _safe_continuity_state()
    lines.append(f"  Continuity: {cs.get('continuity_strength', '?')}")

    coh = _safe_coherence_state()
    lines.append(f"  Coherence: {coh.get('coherence_score', '?')}/100")

    ss = _safe_stability_state()
    lines.append(f"  Stability: {ss.get('stability_score', '?')}/100")

    rs = _safe_resonance_state()
    lines.append(f"  Resonance: {rs.get('intensity', '?')} ({rs.get('color', '?')})")

    g = describe_governance()
    lines.append(f"  Governance: {g.get('persona_id', '?')}/{g.get('mode_id', '?')} "
                 f"health={g.get('governance_score', '?')}")
    return "\n".join(lines)


def identity_posture() -> str:
    from runtime.self_description import describe_posture
    p = describe_posture()
    lines = [f"Posture: {p.get('posture_id', '?')} ({p.get('name', '?')})"]
    lines.append(f"  Category: {p.get('category', '?')}")
    lines.append(f"  Expression: {p.get('expression_level', '?')}")
    lines.append(f"  Autonomy: {p.get('autonomy_level', '?')}")
    lines.append(f"  Safety flags: {p.get('safety_flags', [])}")
    lines.append(f"  Reason: {p.get('reason', '?')}")
    return "\n".join(lines)


def identity_autonomy() -> str:
    from runtime.self_description import describe_autonomy
    a = describe_autonomy()
    lines = [f"Autonomy tier: {a.get('tier_id', '?')} ({a.get('tier_name', '?')})"]
    lines.append(f"  Allowed: {', '.join(a.get('allowed_action_categories', []))}")
    lines.append(f"  Disallowed: {', '.join(a.get('disallowed_action_categories', []))}")
    lines.append(f"  Posture-forced: {a.get('posture_forced_tier', 'none')}")
    lines.append(f"  Operator override: {a.get('operator_override', False)}")
    return "\n".join(lines)


def identity_governance() -> str:
    from runtime.self_description import describe_governance
    g = describe_governance()
    lines = [f"Governance: {g.get('persona_id', '?')}/{g.get('mode_id', '?')}"]
    lines.append(f"  Persona: {g.get('persona_name', '?')}")
    lines.append(f"  Mode: {g.get('mode_name', '?')}")
    lines.append(f"  Risk ceiling: {g.get('risk_ceiling', '?')}")
    lines.append(f"  Approval: {g.get('patch_approval_threshold', '?')}")
    lines.append(f"  Health: {g.get('governance_score', '?')}/100")
    lines.append(f"  Kill switch: {g.get('kill_switch', False)}")
    lines.append(f"  Circuit breaker: {g.get('circuit_breaker', False)}")
    drift = g.get("drift") or {}
    if drift:
        lines.append(f"  Drift: total={drift.get('total_drift_score', '?')} "
                     f"alert={drift.get('alert', False)}")
    return "\n".join(lines)


def identity_expression() -> str:
    from runtime.self_description import describe_expression_stack
    e = describe_expression_stack()
    lines = [f"Expression stack ({e.get('posture_id', '?')}):"]
    if e.get("suppressed"):
        lines.append("  [suppressed by current posture]")
    ep = e.get("expression_profile") or {}
    lines.append(f"  Tone: {ep.get('tone', '?')}  Verbosity: {ep.get('verbosity', '?')}")
    lines.append(f"  Comfort: {ep.get('comfort_layer', False)}  "
                 f"Attunement: {ep.get('operator_attunement', False)}")
    rp = e.get("resonance_profile") or {}
    lines.append(f"  Resonance: intensity={rp.get('intensity', '?')} "
                 f"color={rp.get('color', '?')} decay={rp.get('decay_rate', '?')}")
    lines.append(f"  Continuity weight: {e.get('continuity_weight', '?')}")
    la = e.get("long_arc_smoothing") or {}
    if not la.get("suppressed"):
        lines.append(f"  Long-arc: stability={la.get('stability_score', '?')} "
                     f"events={la.get('recent_events', 0)}")
    ac = e.get("alignment_corrections") or {}
    if not ac.get("suppressed"):
        lines.append(f"  Alignment: score={ac.get('recent_score', '?')} "
                     f"applied={ac.get('recent_applied', 0)}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Governance layer
# ------------------------------------------------------------------


def governance_state() -> str:
    from governance.kernel import get_kernel_state
    ks = get_kernel_state()
    lines = ["Governance state:"]
    p = ks.get("persona") or {}
    m = ks.get("mode") or {}
    h = ks.get("health") or {}
    lines.append(f"  Persona: {p.get('persona_id', '?')} ({p.get('name', '?')})")
    lines.append(f"  Mode: {m.get('mode_id', '?')} ({m.get('name', '?')})")
    lines.append(f"  Health: {h.get('governance_score', '?')}/100")
    lines.append(f"  Kill switch: {ks.get('kill_switch', False)}")
    lines.append(f"  Circuit breaker: {ks.get('circuit_breaker', False)}")
    lines.append(f"  Stabilise: {ks.get('stabilise_mode', False)}")
    return "\n".join(lines)


def governance_persona(persona_id: str | None = None) -> str:
    if persona_id:
        from governance.personas import get_persona
        p = get_persona(persona_id)
        if not p:
            return f"Unknown persona: {persona_id}"
        lines = [f"Governance persona: {p.get('name', '?')}"]
        lines.append(f"  Style: {p.get('decision_style', '?')}")
        lines.append(f"  Risk: {p.get('risk_posture', '?')}")
        lines.append(f"  Allowed: {', '.join(p.get('allowed_operations', []))}")
        return "\n".join(lines)
    from governance.personas import get_active_persona
    p = get_active_persona()
    return f"Active governance persona: {p.get('persona_id', '?')} ({p.get('name', '?')})"


def governance_mode(mode_id: str | None = None) -> str:
    if mode_id:
        from governance.modes import get_mode
        m = get_mode(mode_id)
        if not m:
            return f"Unknown mode: {mode_id}"
        lines = [f"Governance mode: {m.get('name', '?')}"]
        lines.append(f"  Drift sensitivity: {m.get('drift_sensitivity', '?')}")
        lines.append(f"  Safety multiplier: {m.get('safety_multiplier', '?')}")
        lines.append(f"  Approval: {m.get('patch_approval_threshold', '?')}")
        return "\n".join(lines)
    from governance.modes import get_active_mode
    m = get_active_mode()
    return f"Active governance mode: {m.get('mode_id', '?')} ({m.get('name', '?')})"


def governance_envelope() -> str:
    from governance.envelopes import compute_envelope
    env = compute_envelope()
    lines = ["Governance envelope:"]
    lines.append(f"  Persona: {env.get('persona_id', '?')}")
    lines.append(f"  Mode: {env.get('mode_id', '?')}")
    lines.append(f"  Risk ceiling: {env.get('risk_ceiling', '?')}")
    lines.append(f"  Approval: {env.get('patch_approval_threshold', '?')}")
    lines.append(f"  Reversibility required: {env.get('reversibility_required', '?')}")
    lines.append(f"  Allowed ops: {', '.join(env.get('allowed_operations', []))}")
    lines.append(f"  Forbidden ops: {', '.join(env.get('forbidden_operations', []))}")
    return "\n".join(lines)


def governance_drift() -> str:
    from governance.drift_detector import compute_drift_report
    dr = compute_drift_report()
    lines = ["Governance drift report:"]
    lines.append(f"  Total: {dr.get('total_drift_score', '?')}")
    lines.append(f"  Average: {dr.get('average_drift_score', '?')}")
    lines.append(f"  Alert: {dr.get('alert', False)}")
    dims = dr.get("dimensions") or {}
    for name, info in dims.items():
        lines.append(f"  {name}: {info.get('drift_score', '?')} ({info.get('detail', '')})")
    return "\n".join(lines)


def governance_proposals(status: str | None = None) -> str:
    from governance.proposal_engine import get_proposals
    ps = get_proposals(status=status, limit=10)
    if not ps:
        return "No governance proposals."
    lines = [f"Governance proposals ({len(ps)}):"]
    for p in ps:
        lines.append(
            f"  {p.get('proposal_id', '?')}: {p.get('title', '?')} "
            f"[{p.get('status', '?')}] risk={p.get('risk_score', '?')}"
        )
    return "\n".join(lines)


def governance_patches(status: str | None = None) -> str:
    from governance.patch_lifecycle import get_patches
    ps = get_patches(status=status, limit=10)
    if not ps:
        return "No governance patches."
    lines = [f"Governance patches ({len(ps)}):"]
    for p in ps:
        lines.append(
            f"  {p.get('patch_id', '?')}: {p.get('description', '?')} "
            f"[{p.get('status', '?')}]"
        )
    return "\n".join(lines)


def governance_audit(limit: int = 20) -> str:
    from governance.audit_log import get_log
    entries = get_log(limit)
    if not entries:
        return "No governance audit entries."
    lines = [f"Governance audit log ({len(entries)} entries):"]
    for e in entries[-10:]:
        lines.append(f"  {e.get('event_type', '?')}: {e.get('details', {})}")
    return "\n".join(lines)


def governance_kernel_state() -> str:
    from governance.kernel import get_kernel_state
    ks = get_kernel_state()
    lines = ["Governance kernel state:"]
    h = ks.get("health") or {}
    lines.append(f"  Score: {h.get('governance_score', '?')}/100")
    lines.append(f"  Kill switch: {ks.get('kill_switch', False)}")
    lines.append(f"  Circuit breaker: {ks.get('circuit_breaker', False)}")
    lines.append(f"  Stabilise: {ks.get('stabilise_mode', False)}")
    recent = ks.get("recent_decisions") or []
    if recent:
        lines.append(f"  Recent decisions ({len(recent)}):")
        for d in recent[-3:]:
            lines.append(f"    {d.get('action', '?')}: {d.get('reason', '')}")
    return "\n".join(lines)


def governance_reset(reason: str = "operator") -> str:
    from governance.kernel import reset_kernel
    result = reset_kernel(reason)
    return f"Governance kernel reset: {result.get('success', False)}"


# ------------------------------------------------------------------
# Phase 68 — Expressive resonance
# ------------------------------------------------------------------


def resonance_profile_cmd(posture_id: str | None = None) -> str:
    from runtime.resonance_profiles import get_resonance_profile

    if posture_id is None:
        try:
            from runtime.posture_state import get_current_posture
            posture_id = get_current_posture()["posture_id"]
        except Exception:
            posture_id = "COMPANION"

    p = get_resonance_profile(posture_id)
    lines = [f"Resonance profile ({posture_id}):"]
    lines.append(f"  Intensity: {p.get('resonance_intensity', '?')}")
    lines.append(f"  Color: {p.get('resonance_color', '?')}")
    lines.append(f"  Decay rate: {p.get('resonance_decay_rate', '?')}")
    br = p.get("resonance_blend_rules") or {}
    if br:
        lines.append(f"  Blend rules: {', '.join(f'{k}={v}' for k, v in br.items())}")
    else:
        lines.append(f"  Blend rules: none")
    sm = p.get("signature_modulation") or {}
    if sm:
        lines.append(f"  Signature: {', '.join(f'{k}={v}' for k, v in sm.items())}")
    return "\n".join(lines)


def resonance_summary_cmd() -> str:
    from runtime.resonance_engine import resonance_summary

    s = resonance_summary()
    lines = ["Resonance summary:"]
    lines.append(f"  Posture: {s.get('posture_id', '?')}")
    lines.append(f"  Previous: {s.get('previous_posture_id', 'none')}")
    lines.append(f"  Intensity: {s.get('resonance_intensity', '?')}")
    lines.append(f"  Color: {s.get('resonance_color', '?')}")
    lines.append(f"  Decay rate: {s.get('resonance_decay_rate', '?')}")
    lines.append(f"  Blend factor: {s.get('blend_factor', '?')}")
    lines.append(f"  Stability: {s.get('stability_score', '?')}")
    recent = s.get("recent_log") or []
    if recent:
        lines.append(f"  Recent ({len(recent)}):")
        for r in recent[-3:]:
            lines.append(
                f"    {r.get('posture_id', '?')}  "
                f"eff={r.get('effective_intensity', '?')}  "
                f"blend={r.get('blend_factor', '?')}  "
                f"{r.get('action', '?')}"
            )
    return "\n".join(lines)


def resonance_preview_cmd(posture_id: str, sample_text: str) -> str:
    from runtime.resonance_engine import apply_resonance
    from runtime.posture_engine import request_posture, get_active_posture

    original_posture = get_active_posture()["posture_id"]
    try:
        request_posture(posture_id, "resonance_preview")
        shaped = apply_resonance(sample_text, posture_id=posture_id)
    finally:
        request_posture(original_posture, "restore_after_preview")

    lines = [f"Resonance preview ({posture_id}):"]
    lines.append(shaped)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 67 — Expressive stability
# ------------------------------------------------------------------


def stability_state_cmd() -> str:
    from runtime.stability_regulator import get_stability_state

    s = get_stability_state()
    lines = ["Expressive stability:"]
    lines.append(f"  Score: {s.get('stability_score', '?')}")
    lines.append(f"  Oscillation: {s.get('oscillation_index', '?')}")
    lines.append(f"  Jitter: {s.get('jitter_index', '?')}")
    lines.append(f"  Updates: {s.get('update_count', 0)}")
    rp = s.get("recent_postures") or []
    if rp:
        lines.append(f"  Recent postures: {', '.join(str(p) for p in rp[-5:])}")
    rt = s.get("recent_tiers") or []
    if rt:
        lines.append(f"  Recent tiers: {', '.join(str(t) for t in rt[-5:])}")
    rcs = s.get("recent_continuity_strengths") or []
    if rcs:
        lines.append(f"  Recent continuity: {', '.join(str(c) for c in rcs[-5:])}")
    rch = s.get("recent_coherence_scores") or []
    if rch:
        lines.append(f"  Recent coherence: {', '.join(f'{c:.1f}' for c in rch[-5:])}")
    return "\n".join(lines)


def stability_summary_cmd() -> str:
    from runtime.long_arc_engine import long_arc_summary

    s = long_arc_summary()
    lines = ["Long-arc stability summary:"]
    lines.append(f"  Score: {s.get('stability_score', '?')}")
    lines.append(f"  Oscillation: {s.get('oscillation_index', '?')}")
    lines.append(f"  Jitter: {s.get('jitter_index', '?')}")
    lines.append(f"  Updates: {s.get('update_count', 0)}")
    recent = s.get("recent_smoothing") or []
    if recent:
        lines.append(f"  Recent smoothing ({len(recent)}):")
        for r in recent[-3:]:
            lines.append(
                f"    {r.get('target', '?')}  {r.get('posture_id', '?')}  "
                f"stab={r.get('stability_score', '?')}  "
                f"osc={r.get('oscillation_index', '?')}  "
                f"len={r.get('original_len', 0)}->{r.get('smoothed_len', 0)}"
            )
    return "\n".join(lines)


def stability_reset_cmd() -> str:
    from runtime.stability_regulator import reset_stability

    reset_stability()
    return "Expressive stability regulator reset to defaults."


# ------------------------------------------------------------------
# Phase 66 — Identity coherence
# ------------------------------------------------------------------


def coherence_state_cmd() -> str:
    from runtime.identity_coherence import compute_coherence_state
    from runtime.session_continuity import get_continuity_state

    pid = "COMPANION"
    tid = None
    op_ctx: dict = {}
    try:
        from runtime.posture_state import get_current_posture
        pid = get_current_posture()["posture_id"]
    except Exception:
        pass
    try:
        from runtime.autonomy_engine import get_effective_tier
        tid = get_effective_tier().get("tier_id")
    except Exception:
        pass
    try:
        from runtime.operator_context import get_context
        op_ctx = get_context()
    except Exception:
        pass

    cstate = get_continuity_state()
    coh = compute_coherence_state(pid, tid, op_ctx, cstate)

    lines = [f"Identity coherence score: {coh.get('coherence_score', '?')}"]
    lines.append(f"  Posture: {pid}  Tier: {tid or '?'}")
    lines.append(f"  Mismatches: {coh.get('n_mismatches', 0)}")
    for m in coh.get("mismatches", []):
        lines.append(f"    [{m.get('severity', '?')}] {m.get('type', '?')}: {m.get('detail', '?')}")
    resolutions = coh.get("resolutions", [])
    if resolutions:
        lines.append(f"  Resolutions ({len(resolutions)}):")
        for r in resolutions:
            lines.append(f"    {r.get('action', '?')} ({r.get('source_mismatch', '?')})")
    return "\n".join(lines)


def coherence_mismatches_cmd() -> str:
    from runtime.identity_coherence import detect_mismatches

    pid = "COMPANION"
    op_ctx: dict = {}
    try:
        from runtime.posture_state import get_current_posture
        pid = get_current_posture()["posture_id"]
    except Exception:
        pass
    try:
        from runtime.operator_context import get_context
        op_ctx = get_context()
    except Exception:
        pass
    try:
        from runtime.session_continuity import get_continuity_state
        cstate = get_continuity_state()
    except Exception:
        cstate = {}

    mismatches = detect_mismatches(pid, operator_context=op_ctx, continuity_state=cstate)
    if not mismatches:
        return "No identity coherence mismatches detected."
    lines = [f"Detected {len(mismatches)} mismatch(es):"]
    for m in mismatches:
        lines.append(
            f"  [{m.get('severity', '?')}] {m.get('type', '?')}: "
            f"{m.get('detail', '?')} -> {m.get('resolution', '?')}"
        )
    return "\n".join(lines)


def coherence_summary_cmd() -> str:
    from runtime.identity_coherence import get_coherence_summary
    from runtime.self_alignment_engine import get_alignment_summary

    cs = get_coherence_summary()
    als = get_alignment_summary()
    lines = ["Identity coherence summary:"]
    lines.append(f"  Last score: {cs.get('last_score', '?')}")
    lines.append(f"  Last mismatches: {cs.get('last_n_mismatches', 0)}")
    lines.append(f"  Last resolutions: {', '.join(cs.get('last_resolutions', [])) or 'none'}")
    lines.append(f"  Total evaluations: {cs.get('total_evaluations', 0)}")
    lines.append(f"Alignment summary:")
    lines.append(f"  Last coherence score: {als.get('last_coherence_score', '?')}")
    lines.append(f"  Last corrections: {als.get('last_corrections_applied', 0)}")
    lines.append(f"  Total alignments: {als.get('total_alignments', 0)}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 65 — Identity continuity
# ------------------------------------------------------------------


def continuity_state() -> str:
    from runtime.session_continuity import get_continuity_state

    s = get_continuity_state()
    lines = ["Session continuity:"]
    lines.append(f"  Active: {s.get('continuity_active', False)}")
    lines.append(f"  Strength: {s.get('continuity_strength', 'low')}")
    lines.append(f"  Last posture: {s.get('last_posture_id', 'none')}")
    lines.append(f"  Last tier: {s.get('last_tier_id', 'none')}")
    lines.append(f"  Last intent: {s.get('last_interaction_intent', 'none')}")
    lines.append(f"  Last focus: {s.get('last_focus_level', 'none')}")
    lines.append(f"  Last style: {s.get('last_engagement_style', 'none')}")
    lines.append(f"  Updates: {s.get('update_count', 0)}")
    ts = s.get("last_update_timestamp")
    lines.append(f"  Last update: {ts:.1f}" if ts else "  Last update: none")
    return "\n".join(lines)


def continuity_summary_cmd() -> str:
    from runtime.identity_continuity_engine import continuity_summary

    s = continuity_summary()
    lines = ["Identity continuity engine:"]
    lines.append(f"  Posture: {s.get('posture_id', '?')}")
    lines.append(f"  Active: {s.get('continuity_active', False)}")
    lines.append(f"  Strength: {s.get('continuity_strength', 'low')}")
    lines.append(f"  Weight: {s.get('continuity_weight', 0.0)}")
    lines.append(f"  Last posture: {s.get('last_posture_id', 'none')}")
    lines.append(f"  Last tier: {s.get('last_tier_id', 'none')}")
    lines.append(f"  Last intent: {s.get('last_interaction_intent', 'none')}")
    lines.append(f"  Last focus: {s.get('last_focus_level', 'none')}")
    recent = s.get("recent_shaped") or []
    if recent:
        lines.append(f"  Recent shaped ({len(recent)}):")
        for r in recent[-3:]:
            lines.append(
                f"    {r.get('posture_id', '?')}  w={r.get('weight', 0):.2f}  "
                f"{r.get('action', '?')}  "
                f"len={r.get('original_len', 0)}->{r.get('shaped_len', 0)}"
            )
    return "\n".join(lines)


def continuity_reset() -> str:
    from runtime.session_continuity import reset_continuity

    reset_continuity()
    return "Session continuity reset to defaults."


# ------------------------------------------------------------------
# Phase 64 — Operator interaction model
# ------------------------------------------------------------------


def operator_context() -> str:
    from runtime.operator_context import get_context

    ctx = get_context()
    lines = ["Operator context:"]
    lines.append(f"  Intent: {ctx.get('interaction_intent', '?')}")
    lines.append(f"  Focus: {ctx.get('operator_focus_level', '?')}")
    lines.append(f"  Style: {ctx.get('operator_engagement_style', '?')}")
    lines.append(f"  Continuity window: {ctx.get('continuity_window_active', False)}")
    ts = ctx.get("last_interaction_timestamp")
    lines.append(f"  Last interaction: {ts:.1f}" if ts else "  Last interaction: none")
    return "\n".join(lines)


def interaction_summary() -> str:
    from runtime.interaction_model import get_interaction_summary

    s = get_interaction_summary()
    ctx = s.get("operator_context", {})
    rules = s.get("flow_rules", {})
    lines = ["Interaction model summary:"]
    lines.append(f"  Posture: {s.get('posture_id', '?')}")
    lines.append(f"  Tier: {s.get('tier_id', '?')}")
    lines.append(f"  Intent: {ctx.get('interaction_intent', '?')}")
    lines.append(f"  Focus: {ctx.get('operator_focus_level', '?')}")
    lines.append(f"  Style: {ctx.get('operator_engagement_style', '?')}")
    lines.append(f"  Comfort layer: {rules.get('comfort_layer', False)}")
    lines.append(f"  Continuity cues: {rules.get('continuity_cues', False)}")
    lines.append(f"  Soft transitions: {rules.get('soft_transitions', False)}")
    recent = s.get("recent_interactions") or []
    if recent:
        lines.append(f"  Recent interactions ({len(recent)}):")
        for r in recent[-3:]:
            lines.append(
                f"    {r.get('posture_id', '?')}  {r.get('action', '?')}  "
                f"len={r.get('original_len', 0)}->{r.get('shaped_len', 0)}"
            )
    return "\n".join(lines)


def interaction_reset() -> str:
    from runtime.operator_context import reset_context

    reset_context()
    return "Operator context reset to defaults."


# ------------------------------------------------------------------
# Phase 63 — Autonomy tiers
# ------------------------------------------------------------------


def autonomy_current() -> str:
    from runtime.autonomy_engine import get_effective_tier

    t = get_effective_tier()
    lines = [
        f"Autonomy tier: {t.get('name', '?')} ({t.get('tier_id', '?')})"
    ]
    lines.append(f"  Reason: {t.get('reason', '?')}")
    allowed = t.get("allowed_action_categories", [])
    disallowed = t.get("disallowed_action_categories", [])
    lines.append(f"  Allowed: {', '.join(allowed) if allowed else 'none'}")
    lines.append(f"  Disallowed: {', '.join(disallowed) if disallowed else 'none'}")
    flags = t.get("safety_flags", [])
    if flags:
        lines.append(f"  Safety flags: {', '.join(flags)}")
    forced = t.get("metadata", {}).get("posture_forced")
    if forced:
        lines.append(f"  Posture-forced: yes")
    if t.get("metadata", {}).get("operator_override"):
        lines.append(f"  Operator override: yes")
    return "\n".join(lines)


def autonomy_history(limit: int = 10) -> str:
    from runtime.autonomy_state import get_tier_history

    hist = get_tier_history(limit)
    if not hist:
        return "No autonomy tier transitions recorded."
    lines = [f"Autonomy tier history ({len(hist)} transitions):"]
    for h in hist:
        lines.append(
            f"  {h.get('from_tier', '?')} -> {h.get('to_tier', '?')}  "
            f"reason={h.get('reason', '?')}  t={h.get('timestamp', 0):.1f}"
        )
    return "\n".join(lines)


def autonomy_set(tier_id: str, reason: str) -> str:
    from runtime.autonomy_engine import request_tier

    r = request_tier(tier_id, reason)
    if r.get("success"):
        return (
            f"Autonomy tier changed: {r.get('from_tier', '?')} -> "
            f"{r.get('to_tier', '?')}  reason={reason}"
        )
    return f"Autonomy tier change rejected: {r.get('rationale', '?')}"


def autonomy_explain() -> str:
    from runtime.autonomy_engine import explain_tier

    e = explain_tier()
    lines = [
        f"Autonomy tier: {e.get('tier_name', '?')} ({e.get('tier_id', '?')})"
    ]
    lines.append(f"  Reason: {e.get('reason', '?')}")
    lines.append(f"  Allowed: {', '.join(e.get('allowed_action_categories', []))}")
    lines.append(f"  Disallowed: {', '.join(e.get('disallowed_action_categories', []))}")
    flags = e.get("safety_flags", [])
    if flags:
        lines.append(f"  Safety flags: {', '.join(flags)}")
    if e.get("posture_forced_tier"):
        lines.append(f"  Posture-forced tier: {e['posture_forced_tier']}")
    lines.append(f"  Posture: {e.get('posture_id', '?')}")
    if e.get("operator_override"):
        lines.append(f"  Operator override: yes")

    pp = e.get("posture_profile", {})
    if pp and not pp.get("error"):
        cats = pp.get("allowed_categories", [])
        lines.append(f"  Posture categories: {', '.join(cats) if cats else 'none'}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 62 — Expression framework
# ------------------------------------------------------------------


def expression_profile(posture_id: str | None = None) -> str:
    if posture_id is None:
        from runtime.posture_state import get_current_posture
        posture_id = get_current_posture()["posture_id"]

    from runtime.expression_profiles import get_profile

    p = get_profile(posture_id)
    lines = [f"Expression profile: {p.get('posture_id', '?')}"]
    lines.append(f"  Tone: {p.get('tone', '?')}")
    lines.append(f"  Verbosity: {p.get('verbosity', '?')}")
    lines.append(f"  Framing: {p.get('framing_style', '?')}")
    lines.append(f"  Continuity cues: {p.get('continuity_cues', False)}")
    lines.append(f"  Comfort layer: {p.get('comfort_layer', False)}")
    lines.append(f"  Operator attunement: {p.get('operator_attunement', False)}")
    rules = p.get("micro_modulation_rules") or {}
    if rules:
        lines.append(f"  Micro-modulation: {rules}")
    return "\n".join(lines)


def expression_preview(posture_id: str, sample_text: str) -> str:
    from runtime.posture_engine import request_posture, get_active_posture
    from runtime.posture_expression import apply_expression_profile
    from runtime.interaction_cycle import shape_interaction

    original_posture = get_active_posture()["posture_id"]
    try:
        request_posture(posture_id, "expression_preview")
        shaped = apply_expression_profile(sample_text, {"source": "preview"})
        shaped = shape_interaction(shaped, posture_id)
    finally:
        request_posture(original_posture, "restore_after_preview")

    lines = [f"Preview ({posture_id}):"]
    lines.append(shaped)
    return "\n".join(lines)


def interaction_cycle_state() -> str:
    from runtime.interaction_cycle import get_cycle_state

    s = get_cycle_state()
    lines = ["Interaction cycle state:"]
    lines.append(f"  Interactions: {s.get('interaction_count', 0)}")
    lines.append(f"  Last event: {s.get('last_event', 'none')}")
    lines.append(f"  Last posture: {s.get('last_posture_id', 'none')}")
    ts = s.get("last_timestamp")
    lines.append(f"  Last timestamp: {ts:.1f}" if ts else "  Last timestamp: none")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 61 — Posture engine
# ------------------------------------------------------------------


def posture_current() -> str:
    from runtime.posture_engine import get_active_posture

    p = get_active_posture()
    lines = [
        f"Posture: {p.get('name', '?')} ({p.get('posture_id', '?')})"
    ]
    lines.append(f"  Category: {p.get('category', '?')}")
    lines.append(f"  Reason: {p.get('reason', '?')}")
    lines.append(f"  Expression: {p.get('allowed_expression_level', '?')}")
    lines.append(f"  Autonomy: {p.get('allowed_autonomy_level', '?')}")
    flags = p.get("safety_flags", [])
    if flags:
        lines.append(f"  Safety flags: {', '.join(flags)}")
    return "\n".join(lines)


def posture_history(limit: int = 10) -> str:
    from runtime.posture_state import get_posture_history

    hist = get_posture_history(limit)
    if not hist:
        return "No posture transitions recorded."
    lines = [f"Posture history ({len(hist)} transitions):"]
    for h in hist:
        lines.append(
            f"  {h.get('from_posture', '?')} -> {h.get('to_posture', '?')}  "
            f"reason={h.get('reason', '?')}  t={h.get('timestamp', 0):.1f}"
        )
    return "\n".join(lines)


def posture_set(posture_id: str, reason: str) -> str:
    from runtime.posture_engine import request_posture

    r = request_posture(posture_id, reason)
    if r.get("success"):
        return (
            f"Posture changed: {r.get('from_posture', '?')} -> "
            f"{r.get('to_posture', '?')}  reason={reason}"
        )
    return f"Posture change rejected: {r.get('rationale', '?')}"


def posture_explain() -> str:
    from runtime.posture_engine import explain_posture

    e = explain_posture()
    lines = [
        f"Posture: {e.get('name', '?')} ({e.get('posture_id', '?')})"
    ]
    lines.append(f"  Category: {e.get('category', '?')}")
    lines.append(f"  Reason: {e.get('reason', '?')}")
    lines.append(f"  Expression level: {e.get('expression_level', '?')}")
    lines.append(f"  Autonomy level: {e.get('autonomy_level', '?')}")
    flags = e.get("safety_flags", [])
    if flags:
        lines.append(f"  Safety flags: {', '.join(flags)}")

    expr = e.get("expression_profile", {})
    if expr and not expr.get("error"):
        lines.append(f"  Expression: tone={expr.get('tone', '?')}  "
                      f"verbosity={expr.get('verbosity', '?')}  "
                      f"framing={expr.get('framing', '?')}")

    auto = e.get("autonomy_profile", {})
    if auto and not auto.get("error"):
        cats = auto.get("allowed_categories", [])
        lines.append(f"  Autonomy categories: {', '.join(cats) if cats else 'none'}")
        lines.append(f"  Autonomy notes: {auto.get('notes', '?')}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Phase 60 — Personas, modes, envelopes
# ------------------------------------------------------------------


def t3_persona_create(
    name: str,
    description: str,
    weighting_profile: Dict[str, float] | None = None,
    objective_bindings: List[str] | None = None,
) -> str:
    from runtime.tier3_personas import create_persona

    p = create_persona(
        name=name,
        description=description,
        weighting_profile=weighting_profile,
        objective_bindings=objective_bindings,
    )
    return f"Persona created: {p['persona_id'][:8]}.. '{p['name']}'"


def t3_personas() -> str:
    from runtime.tier3_personas import list_personas

    ps = list_personas()
    if not ps:
        return "No governance personas defined."
    lines = [f"Governance personas ({len(ps)}):"]
    for p in ps:
        bindings = len(p.get("objective_bindings", []))
        lines.append(
            f"  {p['persona_id'][:8]}.. '{p['name']}'  "
            f"objectives={bindings}"
        )
    return "\n".join(lines)


def t3_persona(persona_id: str) -> str:
    from runtime.tier3_personas import get_persona

    p = get_persona(persona_id)
    if not p:
        return f"Persona '{persona_id}' not found."
    lines = [f"Persona: {p['name']}"]
    lines.append(f"  ID: {p['persona_id']}")
    lines.append(f"  Description: {p['description']}")
    wp = p.get("weighting_profile", {})
    lines.append(f"  Weights: {wp}")
    ob = p.get("objective_bindings", [])
    if ob:
        lines.append(f"  Objective bindings: {ob}")
    return "\n".join(lines)


def t3_mode_create(
    name: str,
    description: str,
    constraints: Dict[str, Any] | None = None,
    persona_id: str | None = None,
) -> str:
    from runtime.tier3_modes import create_mode

    m = create_mode(
        name=name,
        description=description,
        constraints=constraints,
        persona_id=persona_id,
    )
    return f"Mode created: {m['mode_id'][:8]}.. '{m['name']}'"


def t3_modes() -> str:
    from runtime.tier3_modes import list_modes

    ms = list_modes()
    if not ms:
        return "No orchestration modes defined."
    lines = [f"Orchestration modes ({len(ms)}):"]
    for m in ms:
        lines.append(
            f"  {m['mode_id'][:8]}.. '{m['name']}'  "
            f"persona={m.get('persona_id', 'none')[:8] if m.get('persona_id') else 'none'}"
        )
    return "\n".join(lines)


def t3_mode(mode_id: str) -> str:
    from runtime.tier3_modes import get_mode

    m = get_mode(mode_id)
    if not m:
        return f"Mode '{mode_id}' not found."
    lines = [f"Mode: {m['name']}"]
    lines.append(f"  ID: {m['mode_id']}")
    lines.append(f"  Description: {m['description']}")
    lines.append(f"  Constraints: {m.get('constraints', {})}")
    if m.get("persona_id"):
        lines.append(f"  Persona: {m['persona_id']}")
    return "\n".join(lines)


def t3_envelope(persona_id: str, mode_id: str) -> str:
    from runtime.tier3_envelope import build_governance_envelope

    r = build_governance_envelope(persona_id, mode_id)
    if r.get("error"):
        return r["reason"]
    lines = [
        f"Governance envelope: '{r.get('persona_name', '?')}' + "
        f"'{r.get('mode_name', '?')}'  "
        f"composite={r.get('composite_score', '?')}/100"
    ]
    lines.append(f"  Constraints: {r.get('constraints_met', 0)}/"
                 f"{r.get('constraints_total', 0)} met")
    for dim, val in r.get("dimension_scores", {}).items():
        lines.append(f"  {dim}: {val}")
    if r.get("pressure_points"):
        lines.append("Pressure points:")
        for pp in r["pressure_points"]:
            lines.append(f"  - {pp}")
    if r.get("conflicts"):
        lines.append("Conflicts:")
        for c in r["conflicts"]:
            lines.append(f"  ! {c}")
    oa = r.get("objective_alignments", [])
    if oa:
        lines.append("Objective alignments:")
        for a in oa:
            lines.append(
                f"  '{a.get('objective_name', '?')}': "
                f"{a.get('alignment_score', '?')}/100  "
                f"gaps={a.get('gaps', 0)}"
            )
    return "\n".join(lines)
