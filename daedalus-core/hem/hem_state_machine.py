from enum import Enum
from typing import Optional
from .hem_logging import hem_log_event

class HEMState(str, Enum):
    NORMAL_MODE = "NORMAL_MODE"
    HEM_ARMING = "HEM_ARMING"
    HEM_ACTIVE = "HEM_ACTIVE"
    HEM_POSTCHECK = "HEM_POSTCHECK"
    HEM_ROLLBACK = "HEM_ROLLBACK"
    HEM_EXIT = "HEM_EXIT"

_current_state: HEMState = HEMState.NORMAL_MODE
_current_snapshot_id: Optional[str] = None

def hem_get_state() -> HEMState:
    return _current_state

def hem_maybe_enter(trigger_reason: str, metadata: Optional[dict] = None) -> None:
    global _current_state, _current_snapshot_id
    if _current_state != HEMState.NORMAL_MODE:
        return
    _current_state = HEMState.HEM_ARMING
    hem_log_event({"type": "HEM_ENTER", "reason": trigger_reason, "metadata": metadata or {}})

    from .hem_snapshot_bridge import hem_take_snapshot
    _current_snapshot_id = hem_take_snapshot()

    _current_state = HEMState.HEM_ACTIVE

def hem_transition_to_postcheck() -> None:
    global _current_state
    if _current_state == HEMState.HEM_ACTIVE:
        _current_state = HEMState.HEM_POSTCHECK

def hem_run_post_engagement_checks() -> None:
    global _current_state
    if _current_state != HEMState.HEM_POSTCHECK:
        return

    from .hem_drift_bridge import hem_run_post_engagement_checks as _run_checks
    from .hem_snapshot_bridge import hem_rollback_to

    ok = _run_checks()
    if ok:
        _current_state = HEMState.HEM_EXIT
        hem_log_event({"type": "HEM_POSTCHECK_OK"})
    else:
        _current_state = HEMState.HEM_ROLLBACK
        hem_log_event({"type": "HEM_POSTCHECK_DRIFT"})
        hem_rollback_to()

    _current_state = HEMState.NORMAL_MODE
    hem_log_event({"type": "HEM_EXIT"})
