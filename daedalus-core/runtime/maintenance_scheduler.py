# runtime/maintenance_scheduler.py

from __future__ import annotations
from typing import Dict, Any
import time

from runtime.telemetry_history import telemetry_history
from runtime.system_health_index import system_health_index


class MaintenanceScheduler:
    """
    Maintenance Scheduler 1.0

    Responsibilities:
      - Monitor long-term system health
      - Detect anomalies or degradation
      - Recommend maintenance tasks
      - Prepare future SHO proposals (but never apply them)
      - Remain passive and safe

    This module does NOT:
      - Modify system state
      - Apply patches
      - Change thresholds
      - Escalate tiers
    """

    def __init__(self):
        self.last_check = 0.0
        self.interval = 10.0  # seconds between checks
        self.recommendations: Dict[str, Any] = {}

    # ------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------

    def _should_run(self) -> bool:
        now = time.time()
        if now - self.last_check >= self.interval:
            self.last_check = now
            return True
        return False

    def _analyze_health(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze long-term health and produce maintenance recommendations.
        """

        health = system_health_index.compute(snapshot)
        score = health["health_score"]
        trend = health["trend"]
        volatility = health["tier_volatility"]

        recommendations = {}

        # Low health → recommend diagnostics
        if score < 0.33:
            recommendations["priority"] = "high"
            recommendations["action"] = "run_full_diagnostics"
            recommendations["reason"] = "System health critically low."
            recommendations["details"] = health

        # Medium health but degrading → recommend stability tuning
        elif score < 0.66 and trend < 0:
            recommendations["priority"] = "medium"
            recommendations["action"] = "stability_tuning"
            recommendations["reason"] = "Health degrading over time."
            recommendations["details"] = health

        # High volatility → recommend governor threshold review
        if volatility > 0.25:
            recommendations["volatility_warning"] = {
                "action": "review_governor_thresholds",
                "reason": "Tier volatility elevated.",
                "volatility": volatility,
            }

        return recommendations

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """
        Run a maintenance check if enough time has passed.
        Returns the latest recommendations (may be empty).
        """

        if not self._should_run():
            return self.recommendations

        latest = telemetry_history.latest()
        if not latest:
            return {}

        snapshot = latest["snapshot"]
        self.recommendations = self._analyze_health(snapshot)

        return self.recommendations


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
maintenance_scheduler = MaintenanceScheduler()
