# hem/hem_snapshot_bridge.py

"""
HEM Snapshot Bridge — take/restore snapshots during hostile engagements.

Uses the runtime SnapshotEngine for in-memory state snapshots and
RollbackEngine for proposal-based rollback.

Snapshot IDs are stored in thread-local storage so concurrent
HEM engagements on different request threads never share or
clobber each other's rollback targets.
"""

from __future__ import annotations

import threading
from typing import Optional

from runtime.snapshot_engine import snapshot_engine
from runtime.rollback_engine import rollback_engine
from .hem_logging import hem_log_event

_tls = threading.local()


def hem_take_snapshot() -> Optional[str]:
    """Capture the current system state before HEM engagement."""
    state = {"source": "hem_engagement", "phase": "pre_engagement"}
    sid = snapshot_engine.capture(state)
    _tls.snapshot_id = sid
    hem_log_event({"type": "HEM_SNAPSHOT_TAKEN", "snapshot_id": sid})
    return sid


def hem_rollback_to(proposal_id: Optional[str] = None) -> None:
    """
    Roll back after a failed HEM engagement.

    If a proposal_id is given, uses the RollbackEngine's proposal-based
    rollback. Otherwise logs that no rollback target was available.
    """
    sid = getattr(_tls, "snapshot_id", None)
    if proposal_id:
        result = rollback_engine.rollback(proposal_id)
        hem_log_event({"type": "HEM_ROLLBACK_DONE", "proposal_id": proposal_id, "result": str(result)})
        hem_clear_snapshot()
    elif sid:
        restored = snapshot_engine.restore(sid)
        hem_log_event({
            "type": "HEM_ROLLBACK_DONE",
            "snapshot_id": sid,
            "restored": restored is not None,
        })
        hem_clear_snapshot()
    else:
        hem_log_event({"type": "HEM_ROLLBACK_SKIPPED", "reason": "no_snapshot"})


def hem_clear_snapshot() -> None:
    """Discard the current thread's HEM snapshot reference."""
    _tls.snapshot_id = None
