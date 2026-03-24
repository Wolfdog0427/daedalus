from typing import Optional
from runtime import snapshot_engine, rollback_engine
from .hem_logging import hem_log_event

_snapshot_id: Optional[str] = None

def hem_take_snapshot() -> str:
    global _snapshot_id
    _snapshot_id = snapshot_engine.create_snapshot()
    hem_log_event({"type": "HEM_SNAPSHOT_TAKEN", "snapshot_id": _snapshot_id})
    return _snapshot_id

def hem_rollback_to() -> None:
    global _snapshot_id
    if not _snapshot_id:
        hem_log_event({"type": "HEM_ROLLBACK_SKIPPED", "reason": "no_snapshot"})
        return
    rollback_engine.restore_snapshot(_snapshot_id)
    hem_log_event({"type": "HEM_ROLLBACK_DONE", "snapshot_id": _snapshot_id})
