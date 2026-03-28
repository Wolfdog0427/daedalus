# api/http_api.py

from __future__ import annotations
import hmac
import os
from typing import Dict, Any

from fastapi import Depends, FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.ui_gateway import handle_request

_API_KEY_HEADER = APIKeyHeader(name="X-Daedalus-Key", auto_error=False)
_OPERATOR_KEY = os.environ.get("DAEDALUS_API_KEY", "")


def _require_api_key(key: str = Depends(_API_KEY_HEADER)) -> str:
    if not _OPERATOR_KEY:
        return ""
    if not key or not hmac.compare_digest(key, _OPERATOR_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key

from api.dashboard_router import router as dashboard_router

app = FastAPI(title="Assistant Core API", version="1.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the dashboard router
app.include_router(dashboard_router)


class UIRequest(BaseModel):
    command: str
    args: Dict[str, Any] | None = None


# ------------------------------------------------------------
# Generic UI Endpoint
# ------------------------------------------------------------

@app.post("/ui")
def ui_endpoint(req: UIRequest, _key: str = Depends(_require_api_key)) -> Dict[str, Any]:
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
def governor_set_thresholds_endpoint(
    req: Dict[str, Any] = Body(...),
    _key: str = Depends(_require_api_key),
):
    args = req.get("args", {})
    return handle_request({"command": "governor_set_thresholds", "args": args})


@app.post("/governor/thresholds/save")
def governor_save_thresholds_endpoint(_key: str = Depends(_require_api_key)):
    return handle_request({"command": "governor_save_thresholds", "args": {}})


@app.post("/governor/thresholds/load")
def governor_load_thresholds_endpoint(_key: str = Depends(_require_api_key)):
    return handle_request({"command": "governor_load_thresholds", "args": {}})


@app.post("/governor/thresholds/reset")
def governor_reset_thresholds_endpoint(_key: str = Depends(_require_api_key)):
    return handle_request({"command": "governor_reset_thresholds", "args": {}})
