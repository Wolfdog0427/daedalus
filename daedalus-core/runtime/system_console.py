# runtime/system_console.py

from __future__ import annotations
import threading
from typing import Dict, Any

_scheduler_lock = threading.Lock()

# Core subsystems
from runtime.readiness_score import compute_readiness_score
from runtime.governor_sho_bridge import integrate_governor_with_cycle
from runtime.sho_tier_behavior import sho_behavior
from runtime.telemetry import telemetry
from runtime.telemetry_history import telemetry_history
from runtime.maintenance_scheduler import maintenance_scheduler
from runtime.proposal_engine import proposal_engine
from runtime.proposal_review import proposal_review
from runtime.execution_engine import execution_engine
from runtime.rollback_engine import rollback_engine
from runtime.snapshot_engine import snapshot_engine
from runtime.restoration_engine import restoration_engine
from runtime.integrity_validator import integrity_validator
from runtime.integrity_score_engine import integrity_score_engine

# Governor (singleton)
from governor.singleton import governor

# SHO Engine
try:
    from runtime.sho_engine import sho_engine
except ImportError:
    class _FallbackSHO:
        def run_cycle(self):
            return {
                "drift": {"level": "medium"},
                "stability": {"level": "medium"},
                "pre_metrics": {},
                "post_metrics": {},
                "sho_behavior_profile": {"mode": "fallback"},
            }
    sho_engine = _FallbackSHO()


# ------------------------------------------------------------
# STATUS (refined)
# ------------------------------------------------------------

def status() -> Dict[str, Any]:
    """
    Returns the latest known drift/stability if available.
    Falls back to 'unknown' if no cycles have run yet.
    """
    latest = telemetry_history.latest()

    if latest:
        metrics = latest.get("snapshot", latest).get("metrics", {})
        drift = metrics.get("drift", {"level": "unknown"})
        stability = metrics.get("stability", {"level": "unknown"})
    else:
        drift = {"level": "unknown"}
        stability = {"level": "unknown"}

    return {
        "drift": drift,
        "stability": stability,
        "governor": governor.get_state(),
    }


# ------------------------------------------------------------
# HEALTH (refined)
# ------------------------------------------------------------

def health() -> Dict[str, Any]:
    """
    Returns readiness + latest drift/stability if available.
    """
    readiness = compute_readiness_score()
    latest = telemetry_history.latest()

    if latest:
        metrics = latest.get("snapshot", latest).get("metrics", {})
        drift = metrics.get("drift", {"level": "unknown"})
        stability = metrics.get("stability", {"level": "unknown"})
    else:
        drift = {"level": "unknown"}
        stability = {"level": "unknown"}

    return {
        "drift": drift,
        "stability": stability,
        "readiness": readiness,
        "warnings": {},
        "patch_history": {},
    }


# ------------------------------------------------------------
# RUN SINGLE CYCLE
# ------------------------------------------------------------

def run_cycle() -> Dict[str, Any]:
    """
    SHO → Metrics → Readiness → Governor → Tier Behavior → Telemetry → History
    """
    with _scheduler_lock:
        return _run_cycle_unlocked()


def _run_cycle_unlocked() -> Dict[str, Any]:
    # 1. SHO cycle
    cycle_result = sho_engine.run_cycle()

    # 2. Readiness
    readiness = compute_readiness_score()
    cycle_result["readiness"] = readiness

    # 3. Governor integration (tier decisions)
    cycle_result = integrate_governor_with_cycle(cycle_result)

    # 4. Tier behavior overlay
    cycle_result = sho_behavior.apply_tier_behavior(cycle_result)

    # 5. Telemetry snapshot
    snapshot = telemetry.snapshot(cycle_result)

    # 6. History
    telemetry_history.add(snapshot)

    return snapshot


# ------------------------------------------------------------
# RUN SCHEDULER
# ------------------------------------------------------------

def run_scheduler() -> Dict[str, Any]:
    """
    Cycle → Maintenance → Proposals → Review → Execution → Snapshots → Diff → Rollback → Restoration → Validation → Integrity Score
    """
    with _scheduler_lock:
        return _run_scheduler_unlocked()


def _run_scheduler_unlocked() -> Dict[str, Any]:
    # 1. Adaptive cycle
    snapshot = _run_cycle_unlocked()

    # 2. Maintenance
    maintenance = maintenance_scheduler.tick()

    # 3. Proposal generation
    proposal = proposal_engine.tick()

    # 4. Proposal ingestion
    proposal_review.ingest_new_proposal()

    # 5. Pre-execution snapshot
    pre_exec_snapshot_id = snapshot_engine.capture({
        "telemetry": snapshot,
        "governor": governor.get_state(),
        "maintenance": maintenance,
        "proposals": proposal_review.list_all(),
    })

    # 6. Execute approved proposals
    execution = execution_engine.tick()

    # 7. Post-execution snapshot
    post_exec_snapshot_id = snapshot_engine.capture({
        "telemetry": snapshot,
        "governor": governor.get_state(),
        "maintenance": maintenance,
        "proposals": proposal_review.list_all(),
        "execution": execution,
    })

    # 8. Compute diff
    diff = None
    if pre_exec_snapshot_id and post_exec_snapshot_id:
        diff = snapshot_engine.diff(pre_exec_snapshot_id, post_exec_snapshot_id)

    # 9. Rollback state
    last_rollback = rollback_engine.get_last_rollback()

    # 10. Restoration state
    last_restoration = restoration_engine.get_last_restoration()

    # 11. Integrity validation
    validation = integrity_validator.validate()

    # 12. Integrity score
    integrity_score = integrity_score_engine.compute()

    return {
        "status": "ok",
        "state": governor.get_state(),
        "telemetry": snapshot,
        "maintenance": maintenance,
        "proposal": proposal,
        "proposal_registry": proposal_review.list_all(),
        "execution": execution,
        "execution_log": execution_engine.get_execution_log(),
        "pre_execution_snapshot": pre_exec_snapshot_id,
        "post_execution_snapshot": post_exec_snapshot_id,
        "execution_diff": diff,
        "last_rollback": last_rollback,
        "rollback_log": rollback_engine.get_rollback_log(),
        "last_restoration": last_restoration,
        "restoration_log": restoration_engine.get_restoration_log(),
        "snapshots": snapshot_engine.list_all(),
        "integrity_validation": validation,
        "integrity_log": integrity_validator.get_validation_log(),
        "integrity_score": integrity_score,
        "integrity_score_history": integrity_score_engine.get_score_history(),
    }
