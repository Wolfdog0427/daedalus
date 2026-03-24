# runtime/ui_state_bridge.py

from __future__ import annotations

from typing import Dict, Any

from runtime.delta_ui_bridge import get_delta_dashboard


def build_ui_state(health_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine SystemHealth with delta dashboard for UI consumption.
    """
    return {
        "system_health": health_snapshot,
        "delta_dashboard": get_delta_dashboard(),
    }
