# runtime/diagnostics_bootstrap.py
"""
Bootstrap diagnostics API for REPL / execution compatibility.

Delegates to existing health and doctor modules. Does not alter scoring,
thresholds, or subsystem diagnostics logic.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.health_dashboard import summarize_health
from runtime.system_doctor import run_system_doctor


def run_diagnostics() -> Dict[str, Any]:
    """
    Bootstrap compatibility wrapper.

    Delegates to :func:`run_system_doctor` and returns a safe dict shape.
    """
    lines = run_system_doctor(auto=False)
    return {"status": "ok", "lines": lines}


def collect_health_report() -> Dict[str, Any]:
    """
    Bootstrap compatibility wrapper.

    Delegates to :func:`summarize_health` for a structured snapshot.
    """
    return {"status": "ok", "summary": summarize_health()}


def validate_internal_state() -> Dict[str, Any]:
    """Bootstrap compatibility placeholder; no state mutation."""
    return {"status": "ok", "valid": True}
