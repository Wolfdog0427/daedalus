# web_app.py

"""
DEPRECATED — This standalone FastAPI app is superseded by:
  - api/http_api.py        (primary FastAPI "Assistant Core API")
  - runtime/web_router.py  (Intelligence Kernel API, mounted at /api)
  - server/kernel_http_api.py (Starlette gateway)

Do NOT import this module in new code.  It is retained only for
backward-compatibility with any external tools that may reference it.

Original description:
FastAPI Web API for the Cognitive System.
"""

from __future__ import annotations

# ---------------------------------------------------------
# Optional FastAPI import (Termux-safe)
# ---------------------------------------------------------
try:
    from fastapi import FastAPI
except ImportError:
    FastAPI = None

import json

from knowledge.system_dashboard import dashboard_summary
from knowledge.stability_engine import enforce_stability
from knowledge.self_healing_orchestrator import run_improvement_cycle


# ---------------------------------------------------------
# If FastAPI is missing, create a placeholder object
# ---------------------------------------------------------
if FastAPI is None:
    # Dummy object so app.py can import "web_app:app" safely
    class _PlaceholderAPI:
        def __init__(self):
            self.error = (
                "FastAPI is not installed. "
                "Install with: pip install fastapi"
            )

    app = _PlaceholderAPI()

else:
    # ---------------------------------------------------------
    # Real FastAPI app
    # ---------------------------------------------------------
    app = FastAPI(
        title="Cognitive System API",
        description="Web API interface for the cognitive system.",
        version="1.0.0",
    )

    # ---------------------------------------------------------
    # ROUTES
    # ---------------------------------------------------------

    @app.get("/dashboard")
    def get_dashboard():
        """Return the system dashboard summary."""
        return {"dashboard": dashboard_summary()}

    @app.get("/stability")
    def get_stability():
        """Run stability enforcement and return results."""
        return enforce_stability()

    @app.post("/improve")
    def post_improve(goal: str = "general improvement", cycles: int = 1):
        """
        Trigger one or more self-healing improvement cycles.
        """
        cycles = max(1, min(cycles, 100))
        results = []
        for _ in range(cycles):
            results.append(run_improvement_cycle(goal=goal))
        return {"cycles_run": cycles, "results": results}
