# runtime/integrity_score_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time

from runtime.integrity_validator import integrity_validator
from runtime.snapshot_engine import snapshot_engine
from runtime.execution_engine import execution_engine
from runtime.rollback_engine import rollback_engine
from runtime.restoration_engine import restoration_engine
from runtime.proposal_review import proposal_review
from runtime.telemetry_history import telemetry_history


class IntegrityScoreEngine:
    """
    Integrity Score Engine 1.0

    Responsibilities:
      - Compute a unified 0–100 integrity score
      - Weight contributions from:
          - snapshot consistency
          - proposal lifecycle coherence
          - execution/rollback consistency
          - restoration safety
          - telemetry stability
          - validator results
      - Maintain score history
      - Provide a single scalar metric for system health
    """

    def __init__(self):
        self.score_history = []
        self.last_score: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------
    # Component Scoring Helpers
    # ------------------------------------------------------------

    def _score_snapshots(self) -> float:
        """
        Score snapshot consistency.
        """
        snapshots = snapshot_engine.list_all()
        if not snapshots:
            return 100.0  # no snapshots = no issues

        # Count invalid snapshots
        invalid = 0
        for entry in snapshots:
            sid = entry["id"]
            snap = snapshot_engine.get(sid)
            result = integrity_validator._validate_snapshot(snap)
            if not result["valid"]:
                invalid += 1

        ratio = invalid / len(snapshots)
        return max(0.0, 100.0 * (1 - ratio))

    def _score_proposal_lifecycle(self) -> float:
        """
        Score proposal lifecycle coherence.
        """
        lifecycle = integrity_validator._validate_proposal_lifecycle()
        return 100.0 if lifecycle["valid"] else 60.0

    def _score_execution_consistency(self) -> float:
        """
        Score execution/rollback consistency.
        """
        exec_log = execution_engine.get_execution_log()
        rollback_log = rollback_engine.get_rollback_log()

        # If rollback entries reference non-executed proposals → penalty
        rollback_ids = {r["proposal_id"] for r in rollback_log}
        exec_ids = {e["proposal_id"] for e in exec_log}

        invalid = rollback_ids - exec_ids
        if invalid:
            return 70.0

        return 100.0

    def _score_restoration_safety(self) -> float:
        """
        Score restoration safety.
        """
        restorations = restoration_engine.get_restoration_log()
        if not restorations:
            return 100.0

        # If any restoration references missing snapshots → penalty
        invalid = 0
        for r in restorations:
            sid = r.get("snapshot_id")
            if sid and not snapshot_engine.get(sid):
                invalid += 1

        ratio = invalid / len(restorations)
        return max(0.0, 100.0 * (1 - ratio))

    def _score_telemetry_stability(self) -> float:
        """
        Score telemetry stability based on drift/stability history.
        """
        history = telemetry_history.get_all()
        if not history:
            return 100.0

        drift_penalty = 0
        stability_penalty = 0

        for entry in history[-20:]:  # last 20 cycles
            drift = entry.get("drift", {}).get("level")
            stability = entry.get("stability", {}).get("level")

            if drift == "high":
                drift_penalty += 5
            elif drift == "medium":
                drift_penalty += 2

            if stability == "low":
                stability_penalty += 5
            elif stability == "medium":
                stability_penalty += 2

        score = 100.0 - (drift_penalty + stability_penalty)
        return max(0.0, min(100.0, score))

    def _score_validator(self) -> float:
        """
        Score based on integrity validator results.
        """
        last = integrity_validator.get_last_validation()
        if not last:
            return 100.0

        return 100.0 if last["valid"] else 50.0

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def compute(self) -> Dict[str, Any]:
        """
        Compute the unified integrity score.
        """

        components = {
            "snapshots": self._score_snapshots(),
            "proposal_lifecycle": self._score_proposal_lifecycle(),
            "execution_consistency": self._score_execution_consistency(),
            "restoration_safety": self._score_restoration_safety(),
            "telemetry_stability": self._score_telemetry_stability(),
            "validator": self._score_validator(),
        }

        # Weighted score
        score = (
            components["snapshots"] * 0.20 +
            components["proposal_lifecycle"] * 0.20 +
            components["execution_consistency"] * 0.15 +
            components["restoration_safety"] * 0.15 +
            components["telemetry_stability"] * 0.20 +
            components["validator"] * 0.10
        )

        result = {
            "timestamp": time.time(),
            "score": round(score, 2),
            "components": components,
        }

        self.score_history.append(result)
        self.last_score = result

        return result

    def get_last_score(self) -> Optional[Dict[str, Any]]:
        return self.last_score

    def get_score_history(self):
        return list(self.score_history)


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
integrity_score_engine = IntegrityScoreEngine()
