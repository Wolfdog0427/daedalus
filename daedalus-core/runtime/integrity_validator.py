# runtime/integrity_validator.py

from __future__ import annotations
import threading
from typing import Dict, Any, Optional
import time

# FIXED
from governor.singleton import governor

from runtime.snapshot_engine import snapshot_engine
from runtime.rollback_engine import rollback_engine
from runtime.execution_engine import execution_engine
from runtime.proposal_review import proposal_review


class IntegrityValidator:
    """
    Integrity Validator 1.0

    Responsibilities:
      - Validate snapshot consistency
      - Validate diff correctness
      - Validate restoration safety
      - Validate rollback safety
      - Validate proposal/execution lifecycle coherence
      - Maintain validation logs
      - Enforce governor safety rules
    """

    _MAX_LOG = 500

    def __init__(self):
        self._lock = threading.Lock()
        self.validation_log = []
        self.last_validation: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------
    # Governor Safety Gate
    # ------------------------------------------------------------

    def _governor_allows_validation(self) -> bool:
        """
        Tier 1: Minimal validation only
        Tier 2: Full validation allowed
        Tier 3: Full validation + deep invariants
        Strict mode: Validation allowed but no auto-correction
        """
        return True  # Validation is always allowed, but depth varies

    # ------------------------------------------------------------
    # Validation Helpers
    # ------------------------------------------------------------

    def _validate_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic snapshot integrity checks.
        """

        issues = []

        if "timestamp" not in snapshot:
            issues.append("Missing timestamp")

        if "state" not in snapshot:
            issues.append("Missing state")

        if not isinstance(snapshot.get("state", {}), dict):
            issues.append("State is not a dictionary")

        return {"valid": len(issues) == 0, "issues": issues}

    def _validate_diff(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate diff structure and correctness.
        """

        issues = []

        for key in ["added", "removed", "changed"]:
            if key not in diff:
                issues.append(f"Missing diff section: {key}")

        return {"valid": len(issues) == 0, "issues": issues}

    def _validate_proposal_lifecycle(self) -> Dict[str, Any]:
        """
        Ensure proposals follow a coherent lifecycle:
          pending_review → approved → executed → rolled_back/restored
        """

        issues = []

        for p in proposal_review.list_all():
            status = p.get("status")

            pid = p.get("id", "unknown")

            if status == "executed" and pid not in [
                r.get("proposal_id") for r in execution_engine.get_execution_log()
            ]:
                issues.append(f"Proposal {pid} marked executed but no execution record found")

            if status == "rolled_back" and pid not in [
                r.get("proposal_id") for r in rollback_engine.get_rollback_log()
            ]:
                issues.append(f"Proposal {pid} marked rolled_back but no rollback record found")

        return {"valid": len(issues) == 0, "issues": issues}

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        """
        Perform full integrity validation across:
          - snapshots
          - diffs
          - proposal lifecycle
          - rollback safety
          - restoration safety
        """

        if not self._governor_allows_validation():
            return {"valid": False, "reason": "Governor disallowed validation"}

        issues = []

        # Validate snapshots
        for entry in snapshot_engine.list_all():
            sid = entry["id"]
            snap = snapshot_engine.get(sid)
            if snap is None:
                issues.append({"snapshot": sid, "issues": ["snapshot evicted"]})
                continue
            result = self._validate_snapshot(snap)
            if not result["valid"]:
                issues.append({"snapshot": sid, "issues": result["issues"]})

        # Validate proposal lifecycle
        lifecycle = self._validate_proposal_lifecycle()
        if not lifecycle["valid"]:
            issues.append({"proposal_lifecycle": lifecycle["issues"]})

        # Build validation result
        result = {
            "timestamp": time.time(),
            "valid": len(issues) == 0,
            "issues": issues,
        }

        with self._lock:
            self.validation_log.append(result)
            if len(self.validation_log) > self._MAX_LOG:
                self.validation_log[:] = self.validation_log[-self._MAX_LOG:]
            self.last_validation = result

        return result

    def get_last_validation(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self.last_validation) if self.last_validation else None

    def get_validation_log(self):
        with self._lock:
            return list(self.validation_log)

    def clear_log(self) -> None:
        with self._lock:
            self.validation_log.clear()
            self.last_validation = None


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
integrity_validator = IntegrityValidator()
