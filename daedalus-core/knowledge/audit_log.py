# knowledge/audit_log.py

"""
Audit Log

A persistent, append‑only audit log for:
- governed actions (allowed + blocked)
- autonomy mode changes
- scheduler runs
- maintenance cycles
- concept evolution attempts
- verification attempts
- consistency scans
- storage maintenance
- reasoning requests (optional)

This module NEVER deletes or overwrites entries.
It is the system's long‑term accountability layer.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

_log_lock = threading.Lock()

# ------------------------------------------------------------
# STORAGE
# ------------------------------------------------------------

AUDIT_DIR = Path("data/audit")
AUDIT_FILE = AUDIT_DIR / "audit_log.jsonl"   # JSON Lines format


def _ensure_storage():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.write_text("", encoding="utf-8")


# ------------------------------------------------------------
# CORE LOGGING
# ------------------------------------------------------------

def log_event(event_type: str, payload: Dict[str, Any]):
    """
    Appends a single audit event to the log.
    Each event is timestamped and immutable.
    """
    _ensure_storage()

    entry = {
        "timestamp": time.time(),
        "event_type": event_type,
        "payload": payload,
    }

    with _log_lock:
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# ------------------------------------------------------------
# HIGH‑LEVEL HELPERS
# ------------------------------------------------------------

def log_governed_action(action_type: str, result: Dict[str, Any]):
    """
    Logs any action routed through the autonomy governor.
    """
    log_event("governed_action", {
        "action_type": action_type,
        "allowed": result.get("allowed"),
        "requires_approval": result.get("requires_approval"),
        "reason": result.get("reason"),
        "mode": result.get("mode"),
        "result": result.get("result"),
    })


def log_autonomy_change(change_result: Dict[str, Any]):
    """
    Logs changes to autonomy mode.
    """
    log_event("autonomy_change", change_result)


def log_scheduler_run(report: Dict[str, Any]):
    """
    Logs a full scheduler cycle.
    """
    log_event("scheduler_run", report)


def log_verification(claim: str, result: Dict[str, Any]):
    """
    Logs verification attempts.
    """
    log_event("verification", {
        "claim": claim,
        "result": result,
    })


def log_concept_evolution(result: Dict[str, Any]):
    """
    Logs concept evolution cycles.
    """
    log_event("concept_evolution", result)


def log_consistency_scan(result: Dict[str, Any]):
    """
    Logs consistency scans.
    """
    log_event("consistency_scan", result)


def log_storage_maintenance(result: Dict[str, Any]):
    """
    Logs storage maintenance cycles.
    """
    log_event("storage_maintenance", result)


# ------------------------------------------------------------
# RETRIEVAL
# ------------------------------------------------------------

def read_audit_log(limit: Optional[int] = None) -> list[Dict[str, Any]]:
    """
    Reads the audit log (optionally limited to last N entries).
    """
    _ensure_storage()

    entries = []
    with AUDIT_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue

    if limit is not None:
        return entries[-limit:]

    return entries
