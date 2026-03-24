"""
Debug Tools — Unified Debug Surface for REPL 3.0

Provides:
- Last command inspection
- State diffing
- Context before/after views
- Timing summaries
- Watchpoint alerts + history
- Semantic + contextual resolver traces
- Centralized DebugState flags (including cockpit mode)
"""

from __future__ import annotations
from typing import Any, Dict, List
import json
import difflib


# ------------------------------------------------------------
# JSON / PRETTY HELPERS
# ------------------------------------------------------------

def pretty_json(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


# ------------------------------------------------------------
# LAST COMMAND DEBUG
# ------------------------------------------------------------

def debug_last(entry: Dict[str, Any]) -> str:
    """Pretty‑print the last recorded action entry."""
    return pretty_json(entry)


# ------------------------------------------------------------
# STATE DIFF
# ------------------------------------------------------------

def _json_lines(obj: Any) -> List[str]:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False).splitlines()
    except Exception:
        return str(obj).splitlines()


def debug_state_diff(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    """Produce a unified diff between two state snapshots."""
    before_lines = _json_lines(before)
    after_lines = _json_lines(after)

    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="state_before",
        tofile="state_after",
        lineterm="",
    )
    return "\n".join(diff)


# ------------------------------------------------------------
# CONTEXT RESOLVER BEFORE/AFTER
# ------------------------------------------------------------

def debug_context(cmd_before: Dict[str, Any], cmd_after: Dict[str, Any]) -> str:
    """Show the before/after of context resolution."""
    return (
        "=== Context Before ===\n"
        f"{pretty_json(cmd_before)}\n\n"
        "=== Context After ===\n"
        f"{pretty_json(cmd_after)}"
    )


# ------------------------------------------------------------
# TIMING SUMMARY
# ------------------------------------------------------------

def debug_timing_summary(timing: Dict[str, float]) -> str:
    """Pretty‑print timing information for pipeline stages."""
    lines = ["=== Timing Summary ==="]
    for stage, duration in timing.items():
        try:
            lines.append(f"{stage}: {duration:.4f}s")
        except Exception:
            lines.append(f"{stage}: {duration}")
    return "\n".join(lines)


# ------------------------------------------------------------
# WATCHPOINT ALERTS (required by watch_monitor.py)
# ------------------------------------------------------------

def debug_watch_alerts(watch_state: Dict[str, Any]) -> str:
    """
    Return a human-readable summary of watchpoint alerts.

    - Return "" when there are NO alerts.
    - Return a non-empty string ONLY when real alerts exist.
    """
    if not watch_state:
        return ""

    alerts = watch_state.get("alerts") or []
    if not alerts:
        return ""

    lines = ["=== Watchpoint Alerts ==="]
    for alert in alerts:
        try:
            lines.append(json.dumps(alert, indent=2, ensure_ascii=False))
        except Exception:
            lines.append(str(alert))

    return "\n".join(lines)


# ------------------------------------------------------------
# WATCHPOINT HISTORY
# ------------------------------------------------------------

def debug_watch_history(history: List[Dict[str, Any]]) -> str:
    """Pretty‑print watchpoint trigger history."""
    if not history:
        return "No watchpoint history."

    return (
        "=== Watchpoint History ===\n" +
        "\n".join(pretty_json(entry) for entry in history)
    )


# ------------------------------------------------------------
# RAW HISTORY (required by repl_context.py)
# ------------------------------------------------------------

def debug_history(state: Dict[str, Any]) -> str:
    """
    Return raw history data for pretty_debug_history() to format.

    - Returns "" if no history exists.
    - Returns JSON-formatted history otherwise.
    """
    history = state.get("history") or []
    if not history:
        return ""

    try:
        return json.dumps(history, indent=2, ensure_ascii=False)
    except Exception:
        return str(history)


# ------------------------------------------------------------
# SEMANTIC + CONTEXTUAL RESOLVER TRACE
# ------------------------------------------------------------

def debug_semantic_contextual(
    nlu_cmd: Dict[str, Any],
    contextual_trace: List[Dict[str, Any]],
    before_cmd: Dict[str, Any],
    after_cmd: Dict[str, Any],
) -> str:
    """Show NLU → Firewall → Context → Contextual resolution trace."""
    return (
        "=== NLU Command ===\n"
        f"{pretty_json(nlu_cmd)}\n\n"
        "=== Contextual Trace ===\n"
        f"{pretty_json(contextual_trace)}\n\n"
        "=== Before ===\n"
        f"{pretty_json(before_cmd)}\n\n"
        "=== After ===\n"
        f"{pretty_json(after_cmd)}"
    )


# ------------------------------------------------------------
# CONTEXT TRACE (required by repl_context.py)
# ------------------------------------------------------------

def debug_context_trace(trace: List[Dict[str, Any]]) -> str:
    """
    Pretty‑print a contextual resolver trace.

    This is a lighter-weight view than debug_semantic_contextual,
    focused just on the contextual steps.
    """
    if not trace:
        return "No contextual trace."
    return "=== Context Trace ===\n" + pretty_json(trace)


# ------------------------------------------------------------
# CENTRALIZED DEBUG STATE
# ------------------------------------------------------------

class DebugState:
    """Centralized debug toggle container used by the REPL."""

    def __init__(self):
        self.nlu: bool = False
        self.context: bool = False
        self.diff: bool = False
        self.history: bool = False
        self.context_trace: bool = False

        # Persistent cockpit mode
        self.cockpit: bool = False

    def reset(self) -> None:
        """Reset all debug flags."""
        self.nlu = False
        self.context = False
        self.diff = False
        self.history = False
        self.context_trace = False
        self.cockpit = False
