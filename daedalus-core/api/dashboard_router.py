# api/dashboard_router.py

from __future__ import annotations
from typing import Dict, Any, List

from fastapi import APIRouter

from api.ui_gateway import ui_gateway
from runtime.telemetry_history import telemetry_history
from runtime.system_console import status as system_status
from runtime.system_console import health as system_health
from runtime.system_console import run_scheduler

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ------------------------------------------------------------
# Basic System Info
# ------------------------------------------------------------

@router.get("/status")
def get_status() -> Dict[str, Any]:
    return system_status()


@router.get("/health")
def get_health() -> Dict[str, Any]:
    return system_health()


# ------------------------------------------------------------
# Telemetry
# ------------------------------------------------------------

@router.get("/telemetry/latest")
def get_latest_telemetry() -> Dict[str, Any] | None:
    entry = telemetry_history.latest()
    return entry["snapshot"] if entry else None


@router.get("/telemetry/recent")
def get_recent_telemetry(n: int = 20) -> List[Dict[str, Any]]:
    entries = telemetry_history.recent(n)
    return [e["snapshot"] for e in entries]


# ------------------------------------------------------------
# Trends
# ------------------------------------------------------------

@router.get("/trends/readiness")
def readiness_trend(n: int = 50):
    return telemetry_history.readiness_trend(n)


@router.get("/trends/drift")
def drift_trend(n: int = 50):
    return telemetry_history.drift_trend(n)


@router.get("/trends/stability")
def stability_trend(n: int = 50):
    return telemetry_history.stability_trend(n)


@router.get("/trends/system_health")
def system_health_trend(n: int = 50):
    return telemetry_history.system_health_trend(n)


# ------------------------------------------------------------
# Governor History
# ------------------------------------------------------------

@router.get("/governor/decisions")
def governor_decisions(n: int = 50):
    return telemetry_history.governor_decisions(n)


@router.get("/governor/reasons")
def governor_reasons(n: int = 50):
    return telemetry_history.governor_reasons(n)


@router.get("/governor/tier_history")
def tier_history(n: int = 50):
    return telemetry_history.tier_history(n)


@router.get("/governor/tier_transitions")
def tier_transitions(n: int = 50):
    return telemetry_history.tier_transitions(n)


# ------------------------------------------------------------
# SHO Behavior History
# ------------------------------------------------------------

@router.get("/behavior/modes")
def behavior_modes(n: int = 50):
    return telemetry_history.behavior_modes(n)


@router.get("/behavior/actions")
def behavior_actions(n: int = 50):
    return telemetry_history.behavior_actions(n)


# ------------------------------------------------------------
# Full Scheduler Tick (optional)
# ------------------------------------------------------------

@router.post("/tick")
def dashboard_tick() -> Dict[str, Any]:
    """
    Run a full scheduler tick and return the complete system state.
    Useful for debugging or manual control.
    """
    return run_scheduler()
