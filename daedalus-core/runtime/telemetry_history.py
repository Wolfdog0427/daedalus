# runtime/telemetry_history.py

from __future__ import annotations
from typing import Dict, Any, List, Optional
import time


class TelemetryHistory:
    """
    Rolling history buffer for telemetry snapshots.

    Responsibilities:
      - Store recent telemetry snapshots
      - Provide long-term trend visibility
      - Enable retrospective debugging
      - Provide fast access to governor decisions, tier transitions,
        SHO behavior modes, and metric trends
      - Remain lightweight and in-memory
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Core storage
    # ------------------------------------------------------------

    def add(self, snapshot: Dict[str, Any]):
        """
        Add a telemetry snapshot to the history buffer.
        """
        snapshot_with_timestamp = {
            "recorded_at": time.time(),
            "snapshot": snapshot,
        }

        self.entries.append(snapshot_with_timestamp)

        # Enforce rolling window
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)

    def latest(self) -> Optional[Dict[str, Any]]:
        """
        Return the most recent telemetry snapshot.
        """
        if not self.entries:
            return None
        return self.entries[-1]

    def all(self) -> List[Dict[str, Any]]:
        """
        Return the full history buffer.
        """
        return list(self.entries)

    def recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """
        Return the last n snapshots.
        """
        return self.entries[-n:]

    # ------------------------------------------------------------
    # Trend helpers
    # ------------------------------------------------------------

    def _extract(self, key_path: List[str], n: Optional[int] = None) -> List[Any]:
        """
        Generic extractor for nested fields in snapshots.
        key_path example: ["metrics", "readiness"]
        """
        source = self.entries if n is None else self.entries[-n:]
        results = []

        for entry in source:
            snap = entry["snapshot"]
            value = snap
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            results.append(value)

        return results

    # ------------------------------------------------------------
    # Specific trend APIs
    # ------------------------------------------------------------

    def readiness_trend(self, n: int = 50) -> List[Any]:
        return self._extract(["metrics", "readiness"], n)

    def drift_trend(self, n: int = 50) -> List[Any]:
        return self._extract(["metrics", "drift"], n)

    def stability_trend(self, n: int = 50) -> List[Any]:
        return self._extract(["metrics", "stability"], n)

    def system_health_trend(self, n: int = 50) -> List[Any]:
        return self._extract(["system_health"], n)

    # ------------------------------------------------------------
    # Governor-specific history
    # ------------------------------------------------------------

    def governor_decisions(self, n: int = 50) -> List[Any]:
        return self._extract(["governor", "decision"], n)

    def governor_reasons(self, n: int = 50) -> List[Any]:
        return self._extract(["governor", "reason"], n)

    def tier_history(self, n: int = 50) -> List[Any]:
        return self._extract(["governor", "tier"], n)

    def tier_transitions(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Returns a list of {before, after, timestamp} for each tier change.
        """
        transitions = []
        recent_entries = self.entries[-n:]

        last_tier = None
        for entry in recent_entries:
            snap = entry["snapshot"]
            tier = snap.get("governor", {}).get("tier")

            if last_tier is not None and tier != last_tier:
                transitions.append({
                    "from": last_tier,
                    "to": tier,
                    "timestamp": entry["recorded_at"],
                })

            last_tier = tier

        return transitions

    # ------------------------------------------------------------
    # SHO behavior history
    # ------------------------------------------------------------

    def behavior_modes(self, n: int = 50) -> List[Any]:
        return self._extract(["sho_behavior", "mode"], n)

    def behavior_actions(self, n: int = 50) -> List[Any]:
        return self._extract(["sho_behavior", "actions"], n)


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
telemetry_history = TelemetryHistory()
