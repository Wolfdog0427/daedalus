# runtime/restoration_engine.py

from __future__ import annotations
import threading
from typing import Dict, Any, Optional
import time

# FIXED
from governor.singleton import governor

from runtime.snapshot_engine import snapshot_engine


class RestorationEngine:
    """
    Restoration Engine 1.0

    Responsibilities:
      - Restore system state from snapshots
      - Support full and partial restoration
      - Validate restoration safety
      - Maintain restoration logs
      - Enforce governor tier and strict mode
      - Never modify system state unless explicitly authorized
    """

    _MAX_LOG = 500

    def __init__(self):
        self._lock = threading.Lock()
        self.restoration_log = []
        self.last_restoration: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------
    # Governor Safety Gate
    # ------------------------------------------------------------

    def _governor_allows_restoration(self) -> bool:
        """
        Tier 1: No restoration
        Tier 2: Partial restoration only
        Tier 3: Full restoration allowed
        Strict mode: No restoration
        """
        if governor.strict_mode:
            return False

        return governor.tier >= 2

    # ------------------------------------------------------------
    # Restoration Logic
    # ------------------------------------------------------------

    def _restore_full(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder full restoration logic.
        In future versions, this will:
          - restore telemetry state
          - restore governor thresholds
          - restore SHO state
          - restore maintenance state
          - restore proposal/execution state
        """

        return {
            "timestamp": time.time(),
            "status": "restored_full",
            "notes": "Full system state restored symbolically.",
            "snapshot_id": snapshot.get("id"),
        }

    def _restore_partial(self, snapshot: Dict[str, Any], keys: list[str]) -> Dict[str, Any]:
        """
        Placeholder partial restoration logic.
        Restores only specific subsystems.
        """

        state = snapshot.get("state", {})
        restored = {k: state.get(k) for k in keys}

        return {
            "timestamp": time.time(),
            "status": "restored_partial",
            "restored_keys": keys,
            "notes": "Partial system state restored symbolically.",
            "snapshot_id": snapshot.get("id"),
            "restored_state": restored,
        }

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def restore(self, snapshot_id: str, keys: Optional[list[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Restore system state from a snapshot.

        - If keys=None → full restoration (Tier 3 only)
        - If keys provided → partial restoration (Tier 2+)
        """

        if not self._governor_allows_restoration():
            return None

        snapshot = snapshot_engine.get(snapshot_id)
        if not snapshot:
            return None

        # Full restoration requires Tier 3
        if keys is None:
            if governor.tier < 3:
                return None
            result = self._restore_full({"id": snapshot_id, **snapshot})

        # Partial restoration allowed in Tier 2+
        else:
            result = self._restore_partial({"id": snapshot_id, **snapshot}, keys)

        with self._lock:
            self.restoration_log.append(result)
            if len(self.restoration_log) > self._MAX_LOG:
                self.restoration_log[:] = self.restoration_log[-self._MAX_LOG:]
            self.last_restoration = result

        return result

    def get_last_restoration(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self.last_restoration) if self.last_restoration else None

    def get_restoration_log(self):
        with self._lock:
            return list(self.restoration_log)

    def clear_log(self) -> None:
        with self._lock:
            self.restoration_log.clear()
            self.last_restoration = None


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
restoration_engine = RestorationEngine()
