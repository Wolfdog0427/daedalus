from __future__ import annotations
from fastapi import FastAPI
from typing import Dict, Any

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)

from runtime.dashboard_api import dashboard_api
from runtime.command_console import command_console


app = FastAPI(
    title="Intelligence Kernel API",
    description="Unified read/write control plane for the autonomous maintenance architecture.",
    version="1.0.0",
)


# ------------------------------------------------------------
# READ-SIDE ENDPOINTS (Dashboard API)
# ------------------------------------------------------------

@app.get("/status")
def api_status() -> Dict[str, Any]:
    hem_maybe_enter("web_status")
    result = dashboard_api.get_status()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/health")
def api_health() -> Dict[str, Any]:
    hem_maybe_enter("web_health")
    result = dashboard_api.get_health()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/tick")
def api_tick() -> Dict[str, Any]:
    hem_maybe_enter("web_tick")
    result = dashboard_api.tick()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/proposals")
def api_list_proposals() -> Dict[str, Any]:
    hem_maybe_enter("web_list_proposals")
    result = dashboard_api.list_proposals()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/execution/log")
def api_execution_log() -> Dict[str, Any]:
    hem_maybe_enter("web_execution_log")
    result = dashboard_api.get_execution_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/rollback/log")
def api_rollback_log() -> Dict[str, Any]:
    hem_maybe_enter("web_rollback_log")
    result = dashboard_api.get_rollback_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/snapshots")
def api_snapshots() -> Dict[str, Any]:
    hem_maybe_enter("web_snapshots")
    result = dashboard_api.list_snapshots()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/restoration/log")
def api_restoration_log() -> Dict[str, Any]:
    hem_maybe_enter("web_restoration_log")
    result = dashboard_api.get_restoration_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/validation/log")
def api_validation_log() -> Dict[str, Any]:
    hem_maybe_enter("web_validation_log")
    result = dashboard_api.get_validation_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/integrity/score")
def api_integrity_score() -> Dict[str, Any]:
    hem_maybe_enter("web_integrity_score")
    result = dashboard_api.get_integrity_score()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/integrity/history")
def api_integrity_history() -> Dict[str, Any]:
    hem_maybe_enter("web_integrity_history")
    result = dashboard_api.get_integrity_score_history()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/governor")
def api_governor_state() -> Dict[str, Any]:
    hem_maybe_enter("web_governor_state")
    result = dashboard_api.get_governor_state()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.get("/hem/status")
def api_hem_status() -> Dict[str, Any]:
    hem_maybe_enter("web_hem_status")
    result = dashboard_api.get_hem_status()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


# ------------------------------------------------------------
# WRITE-SIDE ENDPOINTS (Command Console)
# ------------------------------------------------------------

@app.post("/proposal/{proposal_id}/approve")
def api_approve_proposal(proposal_id: str) -> Dict[str, Any]:
    hem_maybe_enter("web_approve_proposal", {"proposal_id": proposal_id})
    result = command_console.approve_proposal(proposal_id)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/proposal/{proposal_id}/reject")
def api_reject_proposal(proposal_id: str) -> Dict[str, Any]:
    hem_maybe_enter("web_reject_proposal", {"proposal_id": proposal_id})
    result = command_console.reject_proposal(proposal_id)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/execute")
def api_execute_next() -> Dict[str, Any]:
    hem_maybe_enter("web_execute_next")
    result = command_console.execute_next()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/rollback/{proposal_id}")
def api_rollback(proposal_id: str) -> Dict[str, Any]:
    hem_maybe_enter("web_rollback", {"proposal_id": proposal_id})
    result = command_console.rollback(proposal_id)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/snapshot")
def api_capture_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    hem_maybe_enter("web_capture_snapshot")
    result = command_console.capture_snapshot(state)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/restore/{snapshot_id}")
def api_restore(snapshot_id: str, keys: list[str] | None = None) -> Dict[str, Any]:
    hem_maybe_enter("web_restore", {"snapshot_id": snapshot_id})
    result = command_console.restore(snapshot_id, keys)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/validate")
def api_validate() -> Dict[str, Any]:
    hem_maybe_enter("web_validate")
    result = command_console.validate()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/integrity/compute")
def api_compute_integrity() -> Dict[str, Any]:
    hem_maybe_enter("web_integrity_compute")
    result = command_console.compute_integrity_score()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/governor/tier/{tier}")
def api_set_governor_tier(tier: int) -> Dict[str, Any]:
    hem_maybe_enter("web_set_governor_tier", {"tier": tier})
    result = command_console.set_governor_tier(tier)
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/governor/strict/enable")
def api_enable_strict() -> Dict[str, Any]:
    hem_maybe_enter("web_enable_strict")
    result = command_console.enable_strict_mode()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/governor/strict/disable")
def api_disable_strict() -> Dict[str, Any]:
    hem_maybe_enter("web_disable_strict")
    result = command_console.disable_strict_mode()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


# ------------------------------------------------------------
# LOG MANAGEMENT
# ------------------------------------------------------------

@app.post("/logs/execution/clear")
def api_clear_execution_log() -> Dict[str, Any]:
    hem_maybe_enter("web_clear_execution_log")
    result = command_console.clear_execution_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/logs/rollback/clear")
def api_clear_rollback_log() -> Dict[str, Any]:
    hem_maybe_enter("web_clear_rollback_log")
    result = command_console.clear_rollback_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/logs/restoration/clear")
def api_clear_restoration_log() -> Dict[str, Any]:
    hem_maybe_enter("web_clear_restoration_log")
    result = command_console.clear_restoration_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/logs/validation/clear")
def api_clear_validation_log() -> Dict[str, Any]:
    hem_maybe_enter("web_clear_validation_log")
    result = command_console.clear_validation_log()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result


@app.post("/logs/integrity/clear")
def api_clear_integrity_history() -> Dict[str, Any]:
    hem_maybe_enter("web_clear_integrity_history")
    result = command_console.clear_integrity_score_history()
    hem_transition_to_postcheck()
    hem_run_post_engagement_checks()
    return result
