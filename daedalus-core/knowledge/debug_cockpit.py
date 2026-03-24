# knowledge/debug_cockpit.py

"""
Debugging Cockpit

Central place to:
- capture pipeline snapshots
- record improvement cycles
- record candidates
- record decisions

Backed by simple JSON logs under data/cockpit/.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Any, Optional

COCKPIT_DIR = os.path.join("data", "cockpit")
os.makedirs(COCKPIT_DIR, exist_ok=True)


def _write_json(filename: str, payload: Dict[str, Any]) -> str:
    path = os.path.join(COCKPIT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return path


def capture_pipeline_snapshot(label: str, context: Dict[str, Any]) -> Dict[str, Any]:
    ts = time.time()
    snapshot_id = f"{label}-{int(ts)}"
    payload = {
        "id": snapshot_id,
        "label": label,
        "timestamp": ts,
        "context": context,
    }
    filename = f"snapshot-{snapshot_id}.json"
    path = _write_json(filename, payload)
    return {"id": snapshot_id, "path": path}


def record_improvement_cycle(
    cycle_id: str,
    phase: str,
    goal: str,
    baseline_snapshot_id: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    cockpit_snapshot_id: Optional[str] = None,
) -> None:
    ts = time.time()
    payload = {
        "type": "improvement_cycle",
        "cycle_id": cycle_id,
        "phase": phase,
        "goal": goal,
        "baseline_snapshot_id": baseline_snapshot_id,
        "result": result,
        "cockpit_snapshot_id": cockpit_snapshot_id,
        "timestamp": ts,
    }
    filename = f"cycle-{cycle_id}-{phase}-{int(ts)}.json"
    _write_json(filename, payload)


def record_improvement_candidate(
    cycle_id: str,
    candidate_label: str,
    status: str,
    candidate: Optional[Dict[str, Any]] = None,
    sandbox_result: Optional[Dict[str, Any]] = None,
    cockpit_snapshot_id: Optional[str] = None,
) -> None:
    ts = time.time()
    payload = {
        "type": "improvement_candidate",
        "cycle_id": cycle_id,
        "candidate_label": candidate_label,
        "status": status,
        "candidate": candidate,
        "sandbox_result": sandbox_result,
        "cockpit_snapshot_id": cockpit_snapshot_id,
        "timestamp": ts,
    }
    filename = f"candidate-{cycle_id}-{candidate_label}-{int(ts)}.json"
    _write_json(filename, payload)


def record_improvement_decision(
    cycle_id: str,
    decision: str,
    best_candidate: Optional[Dict[str, Any]] = None,
    all_candidates: Optional[Any] = None,
    candidate_snapshot_id: Optional[str] = None,
    cockpit_snapshot_id: Optional[str] = None,
) -> None:
    ts = time.time()
    payload = {
        "type": "improvement_decision",
        "cycle_id": cycle_id,
        "decision": decision,
        "best_candidate": best_candidate,
        "all_candidates": all_candidates,
        "candidate_snapshot_id": candidate_snapshot_id,
        "cockpit_snapshot_id": cockpit_snapshot_id,
        "timestamp": ts,
    }
    filename = f"decision-{cycle_id}-{decision}-{int(ts)}.json"
    _write_json(filename, payload)
