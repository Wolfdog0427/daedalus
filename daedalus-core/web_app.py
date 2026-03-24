# web_app.py

"""
FastAPI Web API for the Cognitive System.

This module is optional — it only activates if FastAPI is installed.
Provides:
- /dashboard  → system dashboard summary
- /stability  → run stability enforcement
- /improve    → trigger a self-healing improvement cycle
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
        results = []
        for _ in range(cycles):
            results.append(run_improvement_cycle(goal=goal))
        return {"cycles_run": cycles, "results": results}
