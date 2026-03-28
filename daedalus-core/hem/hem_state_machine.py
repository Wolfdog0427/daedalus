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

# Thread-local state: each request thread gets its own HEM lifecycle,
# so concurrent HTTP requests never interfere with each other's
# safety checks, snapshots, or rollback decisions.
_tls = threading.local()

# Atomic counter of threads currently inside an active HEM engagement,
# exposed via hem_active_count() for dashboard monitoring.
_active_counter_lock = threading.Lock()
_active_counter: int = 0


def _get_state() -> HEMState:
    return getattr(_tls, "state", HEMState.NORMAL_MODE)


def _set_state(state: HEMState) -> None:
    _tls.state = state


def _inc_active() -> None:
    global _active_counter
    with _active_counter_lock:
        _active_counter += 1


def _dec_active() -> None:
    global _active_counter
    with _active_counter_lock:
        _active_counter = max(0, _active_counter - 1)


def hem_get_state() -> HEMState:
    """Return the HEM state for the calling thread."""
    return _get_state()


def hem_active_count() -> int:
    """Number of threads currently inside an active HEM engagement."""
    with _active_counter_lock:
        return _active_counter


def hem_maybe_enter(trigger_reason: str, metadata: Optional[dict] = None) -> None:
    if _get_state() != HEMState.NORMAL_MODE:
        return
    _set_state(HEMState.HEM_ARMING)
    try:
        try:
            hem_log_event({"type": "HEM_ENTER", "reason": trigger_reason, "metadata": metadata or {}})
        except Exception:
            pass

        from .hem_snapshot_bridge import hem_take_snapshot
        hem_take_snapshot()

        try:
            from .hem_zero_trust_pipeline import hem_process_hostile_input, HostileInputRejected
            if isinstance(metadata, dict):
                hem_process_hostile_input(metadata)
        except ImportError:
            _set_state(HEMState.NORMAL_MODE)
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
            _set_state(HEMState.NORMAL_MODE)
            try:
                from .hem_snapshot_bridge import hem_clear_snapshot
                hem_clear_snapshot()
            except Exception:
                pass
            hem_log_event({"type": "HEM_REJECTED_HOSTILE", "reason": "zero_trust_pipeline"})
            return

        _set_state(HEMState.HEM_ACTIVE)
        _inc_active()
    except Exception:
        _set_state(HEMState.NORMAL_MODE)
        try:
            from .hem_snapshot_bridge import hem_clear_snapshot
            hem_clear_snapshot()
        except Exception:
            pass
        raise


def hem_transition_to_postcheck() -> None:
    if _get_state() == HEMState.HEM_ACTIVE:
        _set_state(HEMState.HEM_POSTCHECK)


def hem_run_post_engagement_checks() -> None:
    state = _get_state()
    if state != HEMState.HEM_POSTCHECK:
        if state == HEMState.HEM_ACTIVE:
            _set_state(HEMState.NORMAL_MODE)
            _dec_active()
            hem_log_event({"type": "HEM_EXIT_MISSED_POSTCHECK"})
        elif state in (HEMState.HEM_ARMING, HEMState.HEM_ROLLBACK, HEMState.HEM_EXIT):
            _set_state(HEMState.NORMAL_MODE)
            try:
                from .hem_snapshot_bridge import hem_clear_snapshot
                hem_clear_snapshot()
            except Exception:
                pass
            hem_log_event({"type": "HEM_CLEANUP_STALE_STATE", "was": state.value})
        return

    try:
        from .hem_drift_bridge import hem_run_post_engagement_checks as _run_checks
        from .hem_snapshot_bridge import hem_rollback_to

        ok = _run_checks()
        if ok:
            _set_state(HEMState.HEM_EXIT)
            hem_log_event({"type": "HEM_POSTCHECK_OK"})
        else:
            _set_state(HEMState.HEM_ROLLBACK)
            hem_rollback_to()
            hem_log_event({"type": "HEM_POSTCHECK_DRIFT"})
    finally:
        _set_state(HEMState.NORMAL_MODE)
        _dec_active()
        try:
            from .hem_snapshot_bridge import hem_clear_snapshot
            hem_clear_snapshot()
        except Exception:
            pass

    hem_log_event({"type": "HEM_EXIT"})


def hem_force_reset() -> None:
    """Emergency reset for the calling thread's HEM state."""
    was_active = _get_state() in (HEMState.HEM_ACTIVE, HEMState.HEM_POSTCHECK)
    _set_state(HEMState.NORMAL_MODE)
    if was_active:
        _dec_active()
    try:
        from .hem_snapshot_bridge import hem_clear_snapshot
        hem_clear_snapshot()
    except Exception:
        pass
