from __future__ import annotations
import os
import hmac
from fastapi import FastAPI, Request, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from typing import Dict, Any

_API_KEY_HEADER = APIKeyHeader(name="X-Daedalus-Key", auto_error=False)
_OPERATOR_KEY = os.environ.get("DAEDALUS_API_KEY", "")


def _require_api_key(key: str = Depends(_API_KEY_HEADER)) -> str:
    """Gate write endpoints behind an API key when DAEDALUS_API_KEY is set."""
    if not _OPERATOR_KEY:
        return ""
    if not key or not hmac.compare_digest(key, _OPERATOR_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key

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


def _hem_cleanup() -> None:
    """Ensure HEM always returns to NORMAL_MODE after an endpoint."""
    try:
        hem_transition_to_postcheck()
    except Exception:
        pass
    try:
        hem_run_post_engagement_checks()
    except Exception:
        pass


app = FastAPI(
    title="Intelligence Kernel API",
    description="Unified read/write control plane for the autonomous maintenance architecture.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    from runtime.logging_manager import log_event
    log_event("web_router_error", str(exc), {"path": str(request.url.path)})
    _hem_cleanup()
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "internal_error",
            "message": "An internal error occurred. Check server logs for details.",
        },
    )


# ------------------------------------------------------------
# READ-SIDE ENDPOINTS (Dashboard API)
# ------------------------------------------------------------

@app.get("/status")
def api_status() -> Dict[str, Any]:
    return dashboard_api.get_status()


@app.get("/health")
def api_health() -> Dict[str, Any]:
    return dashboard_api.get_health()


@app.post("/tick")
def api_tick(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    return dashboard_api.tick()


@app.get("/proposals")
def api_list_proposals() -> Dict[str, Any]:
    return dashboard_api.list_proposals()


@app.get("/execution/log")
def api_execution_log() -> Dict[str, Any]:
    return dashboard_api.get_execution_log()


@app.get("/rollback/log")
def api_rollback_log() -> Dict[str, Any]:
    return dashboard_api.get_rollback_log()


@app.get("/snapshots")
def api_snapshots() -> Dict[str, Any]:
    return dashboard_api.list_snapshots()


@app.get("/restoration/log")
def api_restoration_log() -> Dict[str, Any]:
    return dashboard_api.get_restoration_log()


@app.get("/validation/log")
def api_validation_log() -> Dict[str, Any]:
    return dashboard_api.get_validation_log()


@app.get("/integrity/score")
def api_integrity_score() -> Dict[str, Any]:
    return dashboard_api.get_integrity_score()


@app.get("/integrity/history")
def api_integrity_history() -> Dict[str, Any]:
    return dashboard_api.get_integrity_score_history()


@app.get("/governor")
def api_governor_state() -> Dict[str, Any]:
    return dashboard_api.get_governor_state()


@app.get("/hem/status")
def api_hem_status() -> Dict[str, Any]:
    return dashboard_api.get_hem_status()


# ------------------------------------------------------------
# WRITE-SIDE ENDPOINTS (Command Console)
# ------------------------------------------------------------

@app.post("/proposal/{proposal_id}/approve")
def api_approve_proposal(proposal_id: str, _key: str = Depends(_require_api_key)):
    hem_maybe_enter("web_approve_proposal", {"proposal_id": proposal_id})
    try:
        result = command_console.approve_proposal(proposal_id)
    finally:
        _hem_cleanup()
    if not result.get("approved"):
        return JSONResponse(content=result, status_code=404)
    return result


@app.post("/proposal/{proposal_id}/reject")
def api_reject_proposal(proposal_id: str, _key: str = Depends(_require_api_key)):
    hem_maybe_enter("web_reject_proposal", {"proposal_id": proposal_id})
    try:
        result = command_console.reject_proposal(proposal_id)
    finally:
        _hem_cleanup()
    if not result.get("rejected"):
        return JSONResponse(content=result, status_code=404)
    return result


@app.post("/execute")
def api_execute_next(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_execute_next")
    try:
        result = command_console.execute_next()
    finally:
        _hem_cleanup()
    return result


@app.post("/rollback/{proposal_id}")
def api_rollback(proposal_id: str, _key: str = Depends(_require_api_key)):
    hem_maybe_enter("web_rollback", {"proposal_id": proposal_id})
    try:
        result = command_console.rollback(proposal_id)
    finally:
        _hem_cleanup()
    rollback_data = result.get("rollback")
    if isinstance(rollback_data, dict) and not rollback_data.get("success", True):
        return JSONResponse(content=result, status_code=404)
    return result


@app.post("/snapshot")
def api_capture_snapshot(state: Dict[str, Any], _key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_capture_snapshot")
    try:
        result = command_console.capture_snapshot(state)
    finally:
        _hem_cleanup()
    return result


@app.post("/restore/{snapshot_id}")
def api_restore(snapshot_id: str, keys: list[str] | None = Body(None, embed=True), _key: str = Depends(_require_api_key)):
    hem_maybe_enter("web_restore", {"snapshot_id": snapshot_id})
    try:
        result = command_console.restore(snapshot_id, keys)
    finally:
        _hem_cleanup()
    restoration = result.get("restoration")
    if restoration is None:
        return JSONResponse(content={"ok": False, "error": "Snapshot not found"}, status_code=404)
    return result


@app.post("/validate")
def api_validate(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_validate")
    try:
        result = command_console.validate()
    finally:
        _hem_cleanup()
    return result


@app.post("/integrity/compute")
def api_compute_integrity(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_integrity_compute")
    try:
        result = command_console.compute_integrity_score()
    finally:
        _hem_cleanup()
    return result


@app.post("/governor/tier/{tier}")
def api_set_governor_tier(tier: int, _key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_set_governor_tier", {"tier": tier})
    try:
        result = command_console.set_governor_tier(tier)
    finally:
        _hem_cleanup()
    return result


@app.post("/governor/strict/enable")
def api_enable_strict(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_enable_strict")
    try:
        result = command_console.enable_strict_mode()
    finally:
        _hem_cleanup()
    return result


@app.post("/governor/strict/disable")
def api_disable_strict(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_disable_strict")
    try:
        result = command_console.disable_strict_mode()
    finally:
        _hem_cleanup()
    return result


# ------------------------------------------------------------
# LOG MANAGEMENT
# ------------------------------------------------------------

@app.post("/logs/execution/clear")
def api_clear_execution_log(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_clear_execution_log")
    try:
        result = command_console.clear_execution_log()
    finally:
        _hem_cleanup()
    return result


@app.post("/logs/rollback/clear")
def api_clear_rollback_log(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_clear_rollback_log")
    try:
        result = command_console.clear_rollback_log()
    finally:
        _hem_cleanup()
    return result


@app.post("/logs/restoration/clear")
def api_clear_restoration_log(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_clear_restoration_log")
    try:
        result = command_console.clear_restoration_log()
    finally:
        _hem_cleanup()
    return result


@app.post("/logs/validation/clear")
def api_clear_validation_log(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_clear_validation_log")
    try:
        result = command_console.clear_validation_log()
    finally:
        _hem_cleanup()
    return result


@app.post("/logs/integrity/clear")
def api_clear_integrity_history(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    hem_maybe_enter("web_clear_integrity_history")
    try:
        result = command_console.clear_integrity_score_history()
    finally:
        _hem_cleanup()
    return result


# ------------------------------------------------------------
# NOTIFICATION ENDPOINTS (Mobile + Web)
# ------------------------------------------------------------

@app.get("/notifications")
def api_list_notifications() -> Dict[str, Any]:
    from runtime.notification_center import list_all
    return {"notifications": list_all()}


@app.get("/notifications/unread")
def api_list_unread_notifications() -> Dict[str, Any]:
    from runtime.notification_center import list_unread
    return {"notifications": list_unread()}


@app.post("/notifications/{notification_id}/read")
def api_mark_notification_read(notification_id: str, _key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    from runtime.notification_center import mark_read
    updated = mark_read(notification_id)
    return {"ok": updated, "notification_id": notification_id}
