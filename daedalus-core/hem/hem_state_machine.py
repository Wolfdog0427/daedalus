import threading
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

_lock = threading.RLock()
_current_state: HEMState = HEMState.NORMAL_MODE


def hem_get_state() -> HEMState:
    return _current_state


def hem_maybe_enter(trigger_reason: str, metadata: Optional[dict] = None) -> None:
    global _current_state
    with _lock:
        if _current_state != HEMState.NORMAL_MODE:
            return
        _current_state = HEMState.HEM_ARMING
        try:
            try:
                hem_log_event({"type": "HEM_ENTER", "reason": trigger_reason, "metadata": metadata or {}})
            except Exception:
                pass

            from .hem_snapshot_bridge import hem_take_snapshot
            hem_take_snapshot()

            try:
                from .hem_zero_trust_pipeline import hem_process_hostile_input, HostileInputRejected
                if isinstance(metadata, dict) and metadata:
                    hem_process_hostile_input(metadata)
            except ImportError:
                _current_state = HEMState.NORMAL_MODE
                try:
                    from .hem_snapshot_bridge import hem_clear_snapshot
                    hem_clear_snapshot()
                except Exception:
                    pass
                try:
                    hem_log_event({"type": "HEM_ABORT_NO_ZEROTRUST",
                                   "reason": "zero_trust_pipeline_unavailable"})
                except Exception:
                    pass
                return
            except HostileInputRejected:
                _current_state = HEMState.NORMAL_MODE
                try:
                    from .hem_snapshot_bridge import hem_clear_snapshot
                    hem_clear_snapshot()
                except Exception:
                    pass
                hem_log_event({"type": "HEM_REJECTED_HOSTILE", "reason": "zero_trust_pipeline"})
                return

            _current_state = HEMState.HEM_ACTIVE
        except Exception:
            _current_state = HEMState.NORMAL_MODE
            raise


def hem_transition_to_postcheck() -> None:
    global _current_state
    with _lock:
        if _current_state == HEMState.HEM_ACTIVE:
            _current_state = HEMState.HEM_POSTCHECK


def hem_run_post_engagement_checks() -> None:
    global _current_state
    with _lock:
        if _current_state != HEMState.HEM_POSTCHECK:
            if _current_state == HEMState.HEM_ACTIVE:
                _current_state = HEMState.NORMAL_MODE
                hem_log_event({"type": "HEM_EXIT_MISSED_POSTCHECK"})
            return

        try:
            from .hem_drift_bridge import hem_run_post_engagement_checks as _run_checks
            from .hem_snapshot_bridge import hem_rollback_to

            ok = _run_checks()
            if ok:
                _current_state = HEMState.HEM_EXIT
                hem_log_event({"type": "HEM_POSTCHECK_OK"})
            else:
                _current_state = HEMState.HEM_ROLLBACK
                hem_rollback_to()
                hem_log_event({"type": "HEM_POSTCHECK_DRIFT"})
        finally:
            _current_state = HEMState.NORMAL_MODE
            try:
                from .hem_snapshot_bridge import hem_clear_snapshot
                hem_clear_snapshot()
            except Exception:
                pass

        hem_log_event({"type": "HEM_EXIT"})


def hem_force_reset() -> None:
    """Emergency reset if HEM gets stuck.  Always returns to NORMAL.

    Replaces the lock entirely so other threads can proceed even if
    the lock is held by a different thread.
    """
    global _current_state, _lock
    _current_state = HEMState.NORMAL_MODE
    _lock = threading.RLock()
    try:
        from .hem_snapshot_bridge import hem_clear_snapshot
        hem_clear_snapshot()
    except Exception:
        pass
