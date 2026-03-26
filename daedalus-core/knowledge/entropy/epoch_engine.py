# knowledge/entropy/epoch_engine.py

"""
Epoch Engine

Converts long-horizon operation into bounded, comparable epochs.
Each epoch has a defined start, a runtime phase where deviations
are logged, and an end phase that triggers:
  1. Graph compaction (coherence fix)
  2. Drift Court session
  3. Entropy budget snapshot
  4. Renewal cycle
  5. Epoch archive

This prevents "one long life" drift by creating natural checkpoints
where the system can self-audit and shed accumulated entropy.

Epoch length is configurable (default: 24-72 hours in production,
much shorter in test/sim mode).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

EPOCH_DIR = Path("data/entropy/epochs")
CURRENT_EPOCH_FILE = EPOCH_DIR / "current.json"
EPOCH_ARCHIVE_DIR = EPOCH_DIR / "archive"


def _ensure_dir():
    EPOCH_DIR.mkdir(parents=True, exist_ok=True)
    EPOCH_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# EPOCH LIFECYCLE
# ------------------------------------------------------------------

def start_epoch(
    epoch_id: Optional[str] = None,
    duration_hours: float = 48.0,
) -> Dict[str, Any]:
    """
    Start a new operational epoch.

    If a current epoch exists and hasn't been ended, this will
    force-end it first (triggering end-of-epoch procedures).
    """
    _ensure_dir()

    if CURRENT_EPOCH_FILE.exists():
        try:
            current = json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
            if current.get("status") == "running":
                end_epoch()
        except Exception:
            pass

    from knowledge.entropy.canonical_template import load_template
    template = load_template()

    if epoch_id is None:
        epoch_id = f"epoch-{int(time.time())}"

    epoch: Dict[str, Any] = {
        "id": epoch_id,
        "start_time": time.time(),
        "target_end_time": time.time() + (duration_hours * 3600),
        "duration_hours": duration_hours,
        "canonical_version": template["version"],
        "status": "running",
        "deviations": [],
        "metrics_at_start": {},
        "metrics_at_end": {},
        "compaction_report": None,
        "drift_court_report": None,
        "renewal_report": None,
        "budget_report": None,
    }

    CURRENT_EPOCH_FILE.write_text(
        json.dumps(epoch, indent=2), encoding="utf-8"
    )
    return epoch


def record_epoch_deviation(deviation: Dict[str, Any]) -> Optional[str]:
    """
    Record a deviation during the current epoch.
    Also forwards to the drift court's deviation log.
    Returns the deviation ID.
    """
    _ensure_dir()
    if not CURRENT_EPOCH_FILE.exists():
        return None

    try:
        epoch = json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if epoch.get("status") != "running":
        return None

    from knowledge.entropy.drift_court import log_deviation
    dev_id = log_deviation(deviation)

    epoch["deviations"].append({
        "id": dev_id,
        "name": deviation.get("name"),
        "timestamp": time.time(),
    })

    CURRENT_EPOCH_FILE.write_text(
        json.dumps(epoch, indent=2), encoding="utf-8"
    )
    return dev_id


def capture_epoch_metrics(metrics: Dict[str, Any], phase: str = "start") -> None:
    """Snapshot system metrics at epoch start or end."""
    _ensure_dir()
    if not CURRENT_EPOCH_FILE.exists():
        return

    try:
        epoch = json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return

    key = f"metrics_at_{phase}"
    epoch[key] = metrics
    CURRENT_EPOCH_FILE.write_text(
        json.dumps(epoch, indent=2), encoding="utf-8"
    )


def is_epoch_expired() -> bool:
    """Check if the current epoch has exceeded its duration."""
    if not CURRENT_EPOCH_FILE.exists():
        return True
    try:
        epoch = json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
        return time.time() >= epoch.get("target_end_time", 0)
    except Exception:
        return True


def end_epoch() -> Dict[str, Any]:
    """
    End the current epoch and trigger the full end-of-epoch sequence:
    1. Graph compaction (coherence fix)
    2. Drift Court session
    3. Entropy budget snapshot
    4. Renewal cycle (prune expired transient state)
    5. Archive the completed epoch

    Each step is individually try/except'd so a failure in one
    doesn't prevent the others from running.
    """
    _ensure_dir()

    if not CURRENT_EPOCH_FILE.exists():
        return {"status": "no_epoch", "error": "no current epoch to end"}

    try:
        epoch = json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "error": f"failed to load epoch: {exc}"}

    epoch["status"] = "ending"
    epoch["end_time"] = time.time()
    epoch["actual_duration_hours"] = round(
        (epoch["end_time"] - epoch["start_time"]) / 3600, 2
    )

    # --- Phase 1: Graph Compaction (COHERENCE FIX) ---
    try:
        from knowledge.graph_compactor import run_compaction
        compaction = run_compaction()
        epoch["compaction_report"] = compaction
    except Exception as exc:
        epoch["compaction_report"] = {"status": "error", "error": str(exc)}

    # --- Phase 2: Drift Court ---
    try:
        from knowledge.entropy.drift_court import run_drift_court
        court = run_drift_court()
        epoch["drift_court_report"] = court
    except Exception as exc:
        epoch["drift_court_report"] = {"status": "error", "error": str(exc)}

    # --- Phase 3: Entropy Budget Snapshot ---
    try:
        from knowledge.entropy.entropy_budget import (
            compute_entropy_budget,
            record_budget_snapshot,
        )
        budget = compute_entropy_budget()
        record_budget_snapshot(budget)
        epoch["budget_report"] = budget
    except Exception as exc:
        epoch["budget_report"] = {"status": "error", "error": str(exc)}

    # --- Phase 4: Renewal ---
    try:
        from knowledge.entropy.renewal_layer import run_renewal
        renewal = run_renewal(dry_run=False)
        epoch["renewal_report"] = renewal
    except Exception as exc:
        epoch["renewal_report"] = {"status": "error", "error": str(exc)}

    # --- Phase 5: Archive ---
    epoch["status"] = "completed"
    archive_path = EPOCH_ARCHIVE_DIR / f"{epoch['id']}.json"
    archive_path.write_text(
        json.dumps(epoch, indent=2, default=str), encoding="utf-8"
    )

    CURRENT_EPOCH_FILE.write_text(
        json.dumps(epoch, indent=2, default=str), encoding="utf-8"
    )

    return epoch


def get_current_epoch() -> Optional[Dict[str, Any]]:
    """Return the current epoch data, or None if no epoch is running."""
    if not CURRENT_EPOCH_FILE.exists():
        return None
    try:
        return json.loads(CURRENT_EPOCH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_epoch_status() -> Dict[str, Any]:
    """Quick status check for meta-cognition."""
    epoch = get_current_epoch()
    if epoch is None:
        return {
            "active": False,
            "should_start": True,
            "reason": "no_epoch_running",
        }

    elapsed_hours = (time.time() - epoch.get("start_time", time.time())) / 3600
    expired = is_epoch_expired()
    deviation_count = len(epoch.get("deviations", []))

    return {
        "active": epoch.get("status") == "running",
        "epoch_id": epoch.get("id"),
        "elapsed_hours": round(elapsed_hours, 2),
        "target_hours": epoch.get("duration_hours", 48),
        "expired": expired,
        "should_end": expired,
        "should_start": epoch.get("status") != "running",
        "deviations_logged": deviation_count,
        "canonical_version": epoch.get("canonical_version"),
    }


def list_completed_epochs(limit: int = 20) -> List:
    """Return metadata from recent completed epochs."""
    _ensure_dir()
    from typing import List as L
    archives: L[Dict[str, Any]] = []
    if not EPOCH_ARCHIVE_DIR.exists():
        return archives

    files = sorted(EPOCH_ARCHIVE_DIR.glob("*.json"), reverse=True)[:limit]
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            archives.append({
                "id": data.get("id"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "duration_hours": data.get("actual_duration_hours"),
                "deviations": len(data.get("deviations", [])),
                "canonical_version": data.get("canonical_version"),
                "status": data.get("status"),
            })
        except Exception:
            continue
    return archives
