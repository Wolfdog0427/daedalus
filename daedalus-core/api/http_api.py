# api/http_api.py

from __future__ import annotations
from typing import Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

from api.ui_gateway import handle_request

# NEW: import the dashboard router
from api.dashboard_router import router as dashboard_router

app = FastAPI(title="Assistant Core API", version="1.4.0")

# Mount the dashboard router
app.include_router(dashboard_router)


class UIRequest(BaseModel):
    command: str
    args: Dict[str, Any] | None = None


# ------------------------------------------------------------
# Generic UI Endpoint
# ------------------------------------------------------------

@app.post("/ui")
def ui_endpoint(req: UIRequest) -> Dict[str, Any]:
    return handle_request({"command": req.command, "args": req.args or {}})


# ------------------------------------------------------------
# Existing Endpoints
# ------------------------------------------------------------

@app.get("/status")
def status_endpoint():
    return handle_request({"command": "status", "args": {}})


@app.get("/health")
def health_endpoint():
    return handle_request({"command": "health", "args": {}})


@app.get("/readiness")
def readiness_endpoint():
    return handle_request({"command": "readiness", "args": {}})


@app.get("/governor/trace")
def governor_trace_endpoint():
    return handle_request({"command": "governor_trace", "args": {}})


@app.get("/governor/thresholds")
def governor_thresholds_endpoint():
    return handle_request({"command": "governor_thresholds", "args": {}})


# ------------------------------------------------------------
# Governor Tuning API Endpoints
# ------------------------------------------------------------

@app.post("/governor/thresholds/set")
def governor_set_thresholds_endpoint(req: Dict[str, Any]):
    args = req.get("args", {})
    return handle_request({"command": "governor_set_thresholds", "args": args})


@app.post("/governor/thresholds/save")
def governor_save_thresholds_endpoint():
    return handle_request({"command": "governor_save_thresholds", "args": {}})


@app.post("/governor/thresholds/load")
def governor_load_thresholds_endpoint():
    return handle_request({"command": "governor_load_thresholds", "args": {}})


@app.post("/governor/thresholds/reset")
def governor_reset_thresholds_endpoint():
    return handle_request({"command": "governor_reset_thresholds", "args": {}})
