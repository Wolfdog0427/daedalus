from __future__ import annotations

import time
from collections import Counter
from typing import Dict, Any, List


_MAX_EVENTS = 500


class HealthMonitor:
    """
    Tracks subsystem health, error frequency, and performance anomalies.
    Keeps a rolling window of events and produces aggregated summaries.
    """

    def __init__(self, max_events: int = _MAX_EVENTS):
        self.events: List[Dict[str, Any]] = []
        self._max_events = max_events

    def record_event(self, event: Dict[str, Any]) -> None:
        event.setdefault("timestamp", time.time())
        self.events.append(event)
        if len(self.events) > self._max_events:
            self.events = self.events[-self._max_events:]

    def summarize(self) -> Dict[str, Any]:
        if not self.events:
            return {
                "total_events": 0,
                "error_count": 0,
                "warning_count": 0,
                "by_subsystem": {},
                "by_category": {},
                "health_score": 1.0,
            }

        error_count = sum(
            1 for e in self.events if e.get("level") in ("error", "critical")
        )
        warning_count = sum(
            1 for e in self.events if e.get("level") == "warning"
        )
        by_subsystem: Dict[str, int] = dict(
            Counter(e.get("subsystem", "unknown") for e in self.events)
        )
        by_category: Dict[str, int] = dict(
            Counter(e.get("category", "general") for e in self.events)
        )

        total = len(self.events)
        error_ratio = error_count / total if total else 0.0
        health_score = max(0.0, 1.0 - error_ratio * 2 - (warning_count / total) * 0.5)

        return {
            "total_events": total,
            "error_count": error_count,
            "warning_count": warning_count,
            "by_subsystem": by_subsystem,
            "by_category": by_category,
            "health_score": round(health_score, 4),
        }
