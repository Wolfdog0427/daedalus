# api/mobile_schema.py

from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

from api.ui_contract import get_contract


# ============================================================
#  AppConfig Schema (Kernel ↔ Mobile Shared UI Contract)
# ============================================================

class AppConfig(BaseModel):
    """
    Declarative UI configuration shared between the kernel and
    the mobile app. The kernel validates and patches this model,
    and the mobile app renders UI based on its values.
    """

    showDebugBanner: bool = Field(
        default=False,
        description="Whether to display the debug banner in the mobile UI."
    )

    layoutVariant: str = Field(
        default="default",
        pattern="^(default|compact|comfortable)$",
        description="UI layout variant: 'default' or 'compact'."
    )


# ============================================================
#  Mobile Command Schema (Existing)
# ============================================================

def get_mobile_command_schema() -> Dict[str, Any]:
    """
    Return the compact mobile-friendly command schema.
    This wraps the UI contract into a smaller structure
    that the mobile app can use to render commands.
    """

    contract = get_contract()

    return {
        "version": contract["version"],
        "commands": {
            "status": {
                "description": "Get compact system status",
                "request": {"command": "status", "args": {}},
                "response": contract["commands"]["status"],
            },
            "health": {
                "description": "Get full system health summary",
                "request": {"command": "health", "args": {}},
                "response": contract["commands"]["health"],
            },
            "run_cycle": {
                "description": "Run a full SHO runtime cycle",
                "request": {"command": "run_cycle", "args": {}},
                "response": contract["commands"]["run_cycle"],
            },
            "run_scheduler": {
                "description": "Run the scheduler once",
                "request": {"command": "run_scheduler", "args": {}},
                "response": contract["commands"]["run_scheduler"],
            },
        },
    }
