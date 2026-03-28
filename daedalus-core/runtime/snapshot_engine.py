# runtime/snapshot_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import copy
import threading
import time

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

    _MAX_SNAPSHOTS = 200

    def __init__(self):
        self._lock = threading.Lock()
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self.snapshot_order: list[str] = []
        self.last_snapshot_id: Optional[str] = None
        self._counter = 0

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _new_id(self) -> str:
        self._counter += 1
        return f"snapshot_{int(time.time() * 1000)}_{self._counter}"

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

        with self._lock:
            sid = self._new_id()

            self.snapshots[sid] = {
                "timestamp": time.time(),
                "state": copy.deepcopy(state),
            }

            self.snapshot_order.append(sid)
            self.last_snapshot_id = sid

            if len(self.snapshot_order) > self._MAX_SNAPSHOTS:
                evict_id = self.snapshot_order.pop(0)
                self.snapshots.pop(evict_id, None)

            return sid

    # ------------------------------------------------------------
    # Snapshot Diff
    # ------------------------------------------------------------

    def diff(self, sid_a: str, sid_b: str) -> Optional[Dict[str, Any]]:
        """
        Compute a shallow diff between two snapshots.
        """
        with self._lock:
            if sid_a not in self.snapshots or sid_b not in self.snapshots:
                return None

            a = copy.deepcopy(self.snapshots[sid_a]["state"])
            b = copy.deepcopy(self.snapshots[sid_b]["state"])

        diff = {
            "added": {},
            "removed": {},
            "changed": {},
        }

        for key in b:
            if key not in a:
                diff["added"][key] = b[key]

        for key in a:
            if key not in b:
                diff["removed"][key] = a[key]

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
        with self._lock:
            snap = self.snapshots.get(sid)
            return copy.deepcopy(snap) if snap is not None else None

    def latest(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.last_snapshot_id:
                return None
            snap = self.snapshots.get(self.last_snapshot_id)
            return copy.deepcopy(snap) if snap is not None else None

    def restore(self, sid: str) -> Optional[Dict[str, Any]]:
        """Restore a previously captured snapshot. Returns a deep copy or None."""
        with self._lock:
            snap = self.snapshots.get(sid)
            if snap is None:
                return None
            return copy.deepcopy(snap["state"])

    def list_all(self):
        with self._lock:
            return [
                {"id": sid, **copy.deepcopy(self.snapshots[sid])}
                for sid in self.snapshot_order
            ]


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
snapshot_engine = SnapshotEngine()
