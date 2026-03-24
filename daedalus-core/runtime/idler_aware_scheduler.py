# runtime/idle_aware_scheduler.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time

from runtime.system_console import run_scheduler


class IdleAwareScheduler:
    """
    Idle-Aware Scheduler 1.0

    Responsibilities:
      - Run a single maintenance cycle when invoked
      - Track last run time and basic pacing
      - Be safe to call from:
          - mobile (local mode)
          - server daemon (server mode)
      - Avoid tight loops: caller decides when to invoke based on "idle" signals
    """

    def __init__(self, min_interval_seconds: float = 30.0):
        self.min_interval_seconds = min_interval_seconds
        self.last_run_timestamp: Optional[float] = None
        self.last_result: Optional[Dict[str, Any]] = None

    def can_run(self) -> bool:
        """
        Check if enough time has passed since the last run.
        Caller should ALSO check device/server "idle" conditions.
        """
        now = time.time()
        if self.last_run_timestamp is None:
            return True

        return (now - self.last_run_timestamp) >= self.min_interval_seconds

    def run_if_allowed(self) -> Optional[Dict[str, Any]]:
        """
        Run a single scheduler cycle if interval conditions are met.
        Returns the result or None if skipped.
        """
        if not self.can_run():
            return None

        result = run_scheduler()
        self.last_run_timestamp = time.time()
        self.last_result = result
        return result

    def force_run(self) -> Dict[str, Any]:
        """
        Force a scheduler cycle regardless of interval.
        Use sparingly (e.g., explicit user request).
        """
        result = run_scheduler()
        self.last_run_timestamp = time.time()
        self.last_result = result
        return result

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        return self.last_result


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
idle_aware_scheduler = IdleAwareScheduler()
