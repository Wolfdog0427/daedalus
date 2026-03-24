# runtime/metrics_engine.py

from __future__ import annotations
from typing import Dict, Any, List
import math


class RollingWindow:
    """
    Simple rolling window for storing numeric values.
    """

    def __init__(self, size: int = 20):
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

    def variance(self) -> float:
        if len(self.values) < 2:
            return 0.0
        m = self.mean()
        return sum((v - m) ** 2 for v in self.values) / len(self.values)

    def volatility(self) -> float:
        """
        Volatility = sqrt(variance)
        """
        return math.sqrt(self.variance())


class MetricsEngine:
    """
    Combined Drift + Stability Analyzer.

    Responsibilities:
      - Maintain rolling baselines
      - Compute drift (deviation from baseline)
      - Compute stability (variance + volatility)
      - Produce normalized scores and levels
      - Provide governor-ready metrics

    This engine is stateful and evolves over time.
    """

    def __init__(self):
        # Rolling windows for drift and stability
        self.drift_window = RollingWindow(size=30)
        self.stability_window = RollingWindow(size=30)

        # Baseline values
        self.baseline_drift = 0.5
        self.baseline_stability = 0.5

    # ------------------------------------------------------------
    # Normalization Helpers
    # ------------------------------------------------------------

    def _normalize_score(self, score: float) -> float:
        """
        Clamp score to [0, 1].
        """
        return max(0.0, min(1.0, score))

    def _level_from_score(self, score: float) -> str:
        """
        Convert numeric score to level.
        """
        if score < 0.33:
            return "low"
        if score < 0.66:
            return "medium"
        return "high"

    # ------------------------------------------------------------
    # Drift Computation
    # ------------------------------------------------------------

    def _compute_drift(self, pre: Dict[str, Any], post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drift = deviation from baseline behavior.
        For now, drift is based on a simple delta between pre and post metrics.
        """

        # Placeholder: compute a simple delta
        delta = abs(hash(str(pre)) - hash(str(post))) % 1000 / 1000.0

        # Update rolling window
        self.drift_window.add(delta)

        # Compute trend (difference from baseline)
        trend = delta - self.baseline_drift

        # Normalize score
        score = self._normalize_score(delta)

        return {
            "level": self._level_from_score(score),
            "score": score,
            "delta": delta,
            "trend": trend,
        }

    # ------------------------------------------------------------
    # Stability Computation
    # ------------------------------------------------------------

    def _compute_stability(self, pre: Dict[str, Any], post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stability = consistency of behavior.
        Lower variance = higher stability.
        """

        # Placeholder: compute a simple stability signal
        stability_signal = abs(hash(str(pre)) + hash(str(post))) % 1000 / 1000.0

        # Update rolling window
        self.stability_window.add(stability_signal)

        variance = self.stability_window.variance()
        volatility = self.stability_window.volatility()

        # Normalize score (lower volatility = higher stability)
        score = self._normalize_score(1.0 - volatility)

        return {
            "level": self._level_from_score(score),
            "score": score,
            "variance": variance,
            "volatility": volatility,
        }

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def compute(self, pre_metrics: Dict[str, Any], post_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute drift + stability metrics for a single SHO cycle.
        """

        drift = self._compute_drift(pre_metrics, post_metrics)
        stability = self._compute_stability(pre_metrics, post_metrics)

        return {
            "drift": drift,
            "stability": stability,
        }


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
metrics_engine = MetricsEngine()
