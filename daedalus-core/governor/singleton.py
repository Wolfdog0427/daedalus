# governor/singleton.py

from __future__ import annotations

from typing import Any, Dict

from governor.autonomy_governor import AutonomyGovernor
from governor.governor_tuning import load_thresholds_silent


# ------------------------------------------------------------
# Create the singleton governor instance
# ------------------------------------------------------------
governor = AutonomyGovernor()


# ------------------------------------------------------------
# Load persisted thresholds (if available)
# ------------------------------------------------------------
# This version does NOT log errors or raise exceptions.
# It silently applies saved thresholds if they exist.
load_thresholds_silent(governor)


# ------------------------------------------------------------
# Read-only introspection (REPL / execution; no state mutation)
# ------------------------------------------------------------


def get_governor_status() -> Dict[str, Any]:
    """Return a minimal snapshot; delegates to :meth:`AutonomyGovernor.get_state`."""
    return {"status": "ok", "governor": governor.get_state()}


def get_current_tier() -> int:
    return governor.tier


def get_governor_report() -> Dict[str, Any]:
    return {"status": "ok", "report": governor.get_state()}


def format_governor_thresholds() -> str:
    """Multi-line string of current threshold fields only."""
    th = governor.get_state()["thresholds"]
    lines = [
        "=== GOVERNOR THRESHOLDS ===",
        f"  drift_escalate:         {th['drift_threshold_escalate']}",
        f"  drift_deescalate:       {th['drift_threshold_deescalate']}",
        f"  stability_escalate:     {th['stability_threshold_escalate']}",
        f"  stability_deescalate:   {th['stability_threshold_deescalate']}",
        f"  readiness_min_escalation:  {th['readiness_min_for_escalation']}",
        f"  readiness_min_autonomous:  {th['readiness_min_for_autonomous']}",
    ]
    return "\n".join(lines)


def summarize_governor() -> str:
    """Multi-line summary for REPL (tier, strict_mode, thresholds)."""
    st = governor.get_state()
    lines = [
        "=== GOVERNOR ===",
        f"tier:         {st['tier']}",
        f"strict_mode:  {st['strict_mode']}",
        "",
        format_governor_thresholds(),
    ]
    return "\n".join(lines)


__all__ = [
    "governor",
    "get_governor_status",
    "get_current_tier",
    "get_governor_report",
    "format_governor_thresholds",
    "summarize_governor",
]
