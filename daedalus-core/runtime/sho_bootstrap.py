# runtime/sho_bootstrap.py
"""
Bootstrap SHO API for REPL / execution compatibility.

Delegates to :func:`orchestrator.sho_cycle_orchestrator.run_sho_cycle` when possible.
Does not modify SHO decision logic; only wraps and caches last result for status views.
"""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any, Dict, Optional

from governor.singleton import governor
from orchestrator.sho_cycle_orchestrator import run_sho_cycle as _orch_run_sho_cycle

_last_sho_cycle_result: Optional[Dict[str, Any]] = None
_sho_lock = threading.Lock()


def run_sho_cycle() -> Dict[str, Any]:
    """
    Run one SHO cycle via the existing orchestrator and cache the outcome.

    On failure, returns a structured error dict (does not raise).
    """
    global _last_sho_cycle_result
    cycle_id = f"sho-{uuid.uuid4().hex[:12]}"
    try:
        result = _orch_run_sho_cycle(governor)
        out = {"status": "ok", "cycle_id": cycle_id, "result": result}
    except Exception as exc:
        out = {"status": "error", "error": str(exc), "cycle_id": cycle_id}
    with _sho_lock:
        _last_sho_cycle_result = out
    return out


def get_sho_status() -> Dict[str, Any]:
    """Minimal status snapshot (last cycle + governor tier)."""
    with _sho_lock:
        last = dict(_last_sho_cycle_result) if _last_sho_cycle_result else None
    return {
        "status": "ok",
        "last_cycle": last,
        "governor_tier": governor.tier,
    }


def get_sho_report() -> Dict[str, Any]:
    return {"status": "ok", "report": get_sho_status()}


def summarize_sho() -> str:
    """Human-readable summary for REPL."""
    st = get_sho_status()
    lines = [
        "=== SHO (Self-Healing Orchestrator) ===",
        f"governor tier: {st['governor_tier']}",
        f"last cycle: {'recorded' if st.get('last_cycle') else 'none'}",
    ]
    if st.get("last_cycle"):
        lines.append("")
        lines.append(json.dumps(st["last_cycle"], indent=2, default=str))
    return "\n".join(lines)
