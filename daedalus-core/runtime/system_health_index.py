# runtime/system_health_index.py

from __future__ import annotations
from typing import Dict, Any, List
import math
import time


class RollingSeries:
    """
    Rolling series for long-term trend analysis.
    """

    def __init__(self, size: int = 100):
        self.size = size
        self.values: List[float] = []

    def add(self, value: float):
        self.values.append(value)
        if len(self.values) > self.size:
            self.values.pop(0)

    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    def trend(self) -> float:
        """
        Simple trend: last value - mean.
        Positive = improving, negative = degrading.
        """
        if not self.values:
            return 0.0
        return self.values[-1] - self.mean()


class SystemHealthIndex:
    """
    Computes a long-term composite health score for the system.

    Inputs:
      - drift score
      - stability score
      - readiness
      - tier volatility
      - governor decisions
      - SHO behavior patterns

    Output:
      - health_score (0 to 1)
      - health_level ("low", "medium", "high")
      - contributing_factors
      - long-term trends
    """

    def __init__(self):
        self.health_series = RollingSeries(size=200)
        self.tier_series = RollingSeries(size=200)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _normalize(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _level(self, score: float) -> str:
        if score < 0.33:
            return "low"
        if score < 0.66:
            return "medium"
        return "high"

    # ------------------------------------------------------------
    # Main Computation
    # ------------------------------------------------------------

    def compute(self, telemetry_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute a composite health score from telemetry.
        """

        metrics = telemetry_snapshot.get("metrics", {})
        drift = metrics.get("drift", {})
        stability = metrics.get("stability", {})
        readiness = metrics.get("readiness", 0.0)

        governor_state = telemetry_snapshot.get("governor", {})
        tier = governor_state.get("tier", 1)

        # Extract numeric signals
        drift_score = drift.get("score", 0.5)
        stability_score = stability.get("score", 0.5)
        readiness_score = readiness

        # Tier volatility (higher volatility = lower health)
        self.tier_series.add(float(tier))
        tier_volatility = abs(self.tier_series.trend())

        # Composite health score
        health_score = (
            (1 - drift_score) * 0.35 +      # lower drift = healthier
            stability_score * 0.35 +        # higher stability = healthier
            readiness_score * 0.20 +        # higher readiness = healthier
            (1 - tier_volatility) * 0.10    # lower volatility = healthier
        )

        health_score = self._normalize(health_score)

        # Track long-term trend
        self.health_series.add(health_score)
        trend = self.health_series.trend()

        return {
            "timestamp": time.time(),
            "health_score": health_score,
            "health_level": self._level(health_score),
            "trend": trend,
            "tier_volatility": tier_volatility,
            "contributing_factors": {
                "drift_score": drift_score,
                "stability_score": stability_score,
                "readiness_score": readiness_score,
                "tier_volatility": tier_volatility,
            },
        }


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
system_health_index = SystemHealthIndex()
