# governor/governor_trace.py

from __future__ import annotations
import threading
from typing import Dict, Any, List
import time

_MAX_TRACE = 500
_trace_log: List[Dict[str, Any]] = []
_trace_lock = threading.Lock()


def record_governor_event(event_type: str, details: Dict[str, Any]) -> None:
    entry = {
        "timestamp": time.time(),
        "event_type": event_type,
        "details": details,
    }
    with _trace_lock:
        _trace_log.append(entry)
        if len(_trace_log) > _MAX_TRACE:
            _trace_log[:] = _trace_log[-_MAX_TRACE:]


def get_governor_trace(limit: int = 50) -> List[Dict[str, Any]]:
    with _trace_lock:
        return list(_trace_log[-limit:])
