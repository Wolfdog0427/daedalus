# api/dashboard_router.py

from __future__ import annotations
import hmac
import os
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from runtime.telemetry_history import telemetry_history
from runtime.system_console import status as system_status
from runtime.system_console import health as system_health
from runtime.system_console import run_scheduler

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_API_KEY_HEADER = APIKeyHeader(name="X-Daedalus-Key", auto_error=False)
_OPERATOR_KEY = os.environ.get("DAEDALUS_API_KEY", "")


def _require_api_key(key: str = Depends(_API_KEY_HEADER)) -> str:
    if not _OPERATOR_KEY:
        return ""
    if not key or not hmac.compare_digest(key, _OPERATOR_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


_MAX_N = 1000


def _clamp_n(n: int) -> int:
    return max(1, min(n, _MAX_N))


# ------------------------------------------------------------
# Basic System Info
# ------------------------------------------------------------

@router.get("/status")
def get_status(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    return system_status()


@router.get("/health")
def get_health(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    return system_health()


# ------------------------------------------------------------
# Telemetry
# ------------------------------------------------------------

@router.get("/telemetry/latest")
def get_latest_telemetry(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    entry = telemetry_history.latest()
    return entry.get("snapshot", entry) if entry else {}


@router.get("/telemetry/recent")
def get_recent_telemetry(n: int = 20, _key: str = Depends(_require_api_key)) -> List[Dict[str, Any]]:
    n = _clamp_n(n)
    entries = telemetry_history.recent(n)
    return [e.get("snapshot", e) for e in entries]


# ------------------------------------------------------------
# Trends
# ------------------------------------------------------------

@router.get("/trends/readiness")
def readiness_trend(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.readiness_trend(_clamp_n(n))


@router.get("/trends/drift")
def drift_trend(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.drift_trend(_clamp_n(n))


@router.get("/trends/stability")
def stability_trend(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.stability_trend(_clamp_n(n))


@router.get("/trends/system_health")
def system_health_trend(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.system_health_trend(_clamp_n(n))


# ------------------------------------------------------------
# Governor History
# ------------------------------------------------------------

@router.get("/governor/decisions")
def governor_decisions(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.governor_decisions(_clamp_n(n))


@router.get("/governor/reasons")
def governor_reasons(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.governor_reasons(_clamp_n(n))


@router.get("/governor/tier_history")
def tier_history(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.tier_history(_clamp_n(n))


@router.get("/governor/tier_transitions")
def tier_transitions(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.tier_transitions(_clamp_n(n))


# ------------------------------------------------------------
# SHO Behavior History
# ------------------------------------------------------------

@router.get("/behavior/modes")
def behavior_modes(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.behavior_modes(_clamp_n(n))


@router.get("/behavior/actions")
def behavior_actions(n: int = 50, _key: str = Depends(_require_api_key)):
    return telemetry_history.behavior_actions(_clamp_n(n))


# ------------------------------------------------------------
# Full Scheduler Tick (optional)
# ------------------------------------------------------------

@router.post("/tick")
def dashboard_tick(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    """
    Run a full scheduler tick and return the complete system state.
    Useful for debugging or manual control.
    """
    return run_scheduler()


# ------------------------------------------------------------
# Dashboard Convenience Endpoints (via ui_gateway)
# ------------------------------------------------------------

@router.get("/overview")
def dashboard_overview(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    """High-level overview: drift, stability, readiness, patch history."""
    from api.dashboard_endpoints import get_dashboard_overview
    return get_dashboard_overview()


@router.get("/compact")
def dashboard_compact_status(_key: str = Depends(_require_api_key)) -> Dict[str, Any]:
    """Compact status for dashboard header."""
    from api.dashboard_endpoints import get_dashboard_status
    return get_dashboard_status()
