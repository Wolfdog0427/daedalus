# runtime/snapshot_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time

# FIXED
from governor.singleton import governor


class SnapshotEngine:
    """
    Snapshot Engine 1.0

    Responsibilities:
      - Capture system state snapshots
      - Provide pre- and post-execution snapshots
      - Compute diffs between snapshots
      - Restore previous snapshots (future)
      - Maintain full snapshot history
      - Enforce governor safety rules
    """

    def __init__(self):
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self.snapshot_order: list[str] = []
        self.last_snapshot_id: Optional[str] = None

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _new_id(self) -> str:
        return f"snapshot_{int(time.time() * 1000)}"

    def _governor_allows_snapshot(self) -> bool:
        """
        Tier 1: No snapshots
        Tier 2: Basic snapshots allowed
        Tier 3: Full snapshots allowed
        Strict mode: No snapshots
        """
        if governor.strict_mode:
            return False

        return governor.tier >= 2

    # ------------------------------------------------------------
    # Snapshot Capture
    # ------------------------------------------------------------

    def capture(self, state: Dict[str, Any]) -> Optional[str]:
        """
        Capture a snapshot of the given system state.
        Returns snapshot ID or None if not allowed.
        """

        if not self._governor_allows_snapshot():
            return None

        sid = self._new_id()

        self.snapshots[sid] = {
            "timestamp": time.time(),
            "state": state,
        }

        self.snapshot_order.append(sid)
        self.last_snapshot_id = sid

        return sid

    # ------------------------------------------------------------
    # Snapshot Diff
    # ------------------------------------------------------------

    def diff(self, sid_a: str, sid_b: str) -> Optional[Dict[str, Any]]:
        """
        Compute a shallow diff between two snapshots.
        """

        if sid_a not in self.snapshots or sid_b not in self.snapshots:
            return None

        a = self.snapshots[sid_a]["state"]
        b = self.snapshots[sid_b]["state"]

        diff = {
            "added": {},
            "removed": {},
            "changed": {},
        }

        # Detect added keys
        for key in b:
            if key not in a:
                diff["added"][key] = b[key]

        # Detect removed keys
        for key in a:
            if key not in b:
                diff["removed"][key] = a[key]

        # Detect changed keys
        for key in a:
            if key in b and a[key] != b[key]:
                diff["changed"][key] = {
                    "from": a[key],
                    "to": b[key],
                }

        return diff

    # ------------------------------------------------------------
    # Snapshot Retrieval
    # ------------------------------------------------------------

    def get(self, sid: str) -> Optional[Dict[str, Any]]:
        return self.snapshots.get(sid)

    def latest(self) -> Optional[Dict[str, Any]]:
        if not self.last_snapshot_id:
            return None
        return self.snapshots[self.last_snapshot_id]

    def list_all(self):
        return [
            {"id": sid, **self.snapshots[sid]}
            for sid in self.snapshot_order
        ]


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
snapshot_engine = SnapshotEngine()
