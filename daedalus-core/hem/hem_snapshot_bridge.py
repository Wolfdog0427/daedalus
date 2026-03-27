# hem/hem_snapshot_bridge.py

"""
HEM Snapshot Bridge — take/restore snapshots during hostile engagements.

Uses the runtime SnapshotEngine for in-memory state snapshots and
RollbackEngine for proposal-based rollback.
"""

from __future__ import annotations

from typing import Optional

from runtime.snapshot_engine import snapshot_engine
from runtime.rollback_engine import rollback_engine
from .hem_logging import hem_log_event

_snapshot_id: Optional[str] = None


def hem_take_snapshot() -> Optional[str]:
    """Capture the current system state before HEM engagement."""
    global _snapshot_id
    state = {"source": "hem_engagement", "phase": "pre_engagement"}
    _snapshot_id = snapshot_engine.capture(state)
    hem_log_event({"type": "HEM_SNAPSHOT_TAKEN", "snapshot_id": _snapshot_id})
    return _snapshot_id


def hem_rollback_to(proposal_id: Optional[str] = None) -> None:
    """
    Roll back after a failed HEM engagement.

    If a proposal_id is given, uses the RollbackEngine's proposal-based
    rollback. Otherwise logs that no rollback target was available.
    """
    global _snapshot_id
    if proposal_id:
        result = rollback_engine.rollback(proposal_id)
        hem_log_event({"type": "HEM_ROLLBACK_DONE", "proposal_id": proposal_id, "result": str(result)})
    elif _snapshot_id:
        hem_log_event({"type": "HEM_ROLLBACK_SYMBOLIC", "snapshot_id": _snapshot_id})
    else:
        hem_log_event({"type": "HEM_ROLLBACK_SKIPPED", "reason": "no_snapshot"})
