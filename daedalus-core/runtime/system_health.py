# runtime/system_health.py

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

from runtime.logging_manager import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SystemHealth:
    """
    Aggregates system-wide health information:
    - Drift
    - Stability
    - Weakest subsystem
    - Autonomy governor state
    - Patch history
    - Proposal state
    - Rollback metadata
    - Reliability dashboard (subsystems + actions)
    """

    def __init__(self):
        self.state: Dict[str, Any] = {
            "drift": {},
            "stability": {},
            "diagnostics": {},
            "weakest_subsystem": {},
            "autonomy": {},
            "patch_history": {
                "total_cycles": 0,
                "successful_patches": 0,
                "failed_patches": 0,
                "reverted_patches": 0,
                "failed_high_level_cycles": 0,
                "failed_tier2_cycles": 0,
                "recent_failures": [],
            },
            "proposals": {
                "pending": [],
                "recent": [],
            },
            "rollback": {
                "last_rollback": None,
                "rollback_count": 0,
            },
            "reliability": {
                "subsystems": {},
                "actions": {},
            },
        }

    def get_snapshot(self) -> Dict[str, Any]:
        import copy
        log_event("system_health", "Snapshot requested")
        return copy.deepcopy(self.state)

    def update_patch_history(self, new_history: Dict[str, Any]) -> None:
        self.state["patch_history"] = new_history
        log_event("system_health", "Patch history updated")

    def record_rollback(self, subsystem: str, snapshot_dir: str) -> None:
        rb = self.state["rollback"]
        rb["last_rollback"] = {
            "timestamp": _now_iso(),
            "subsystem": subsystem,
            "snapshot_dir": snapshot_dir,
        }
        rb["rollback_count"] = rb.get("rollback_count", 0) + 1
        log_event(
            "system_health",
            f"Rollback recorded for subsystem {subsystem}",
            {"snapshot_dir": snapshot_dir},
        )

    def update_proposals(self, pending: list, recent: list) -> None:
        self.state["proposals"]["pending"] = pending
        self.state["proposals"]["recent"] = recent
        log_event("system_health", "Proposal state updated")

    def update_autonomy_state(self, autonomy_state: Dict[str, Any]) -> None:
        self.state["autonomy"] = autonomy_state
        log_event("system_health", "Autonomy state updated")

    def update_drift(self, drift: Dict[str, Any]) -> None:
        self.state["drift"] = drift
        log_event("system_health", "Drift updated")

    def update_stability(self, stability: Dict[str, Any]) -> None:
        self.state["stability"] = stability
        log_event("system_health", "Stability updated")

    def update_weakest_subsystem(self, ws: Dict[str, Any]) -> None:
        self.state["weakest_subsystem"] = ws
        log_event("system_health", "Weakest subsystem updated")

    def update_diagnostics(self, diagnostics: Dict[str, Any]) -> None:
        self.state["diagnostics"] = diagnostics
        log_event("system_health", "Diagnostics updated")

    def update_reliability(self, subsystems: Dict[str, Any], actions: Dict[str, Any]) -> None:
        self.state["reliability"]["subsystems"] = subsystems
        self.state["reliability"]["actions"] = actions
        log_event("system_health", "Reliability dashboard updated")
