# governor/governor_trace.py

from __future__ import annotations
from typing import Dict, Any, List
import time

_trace_log: List[Dict[str, Any]] = []


def record_governor_event(event_type: str, details: Dict[str, Any]) -> None:
    entry = {
        "timestamp": time.time(),
        "event_type": event_type,
        "details": details,
    }
    _trace_log.append(entry)


def get_governor_trace(limit: int = 50) -> List[Dict[str, Any]]:
    return _trace_log[-limit:]
