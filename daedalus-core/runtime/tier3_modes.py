# runtime/tier3_modes.py
"""
Orchestration modes.

A mode declares soft constraints (max drift, min readiness, max risk)
that contextualise governance analytics.  Modes never auto-enforce
or auto-switch — they are read-only lenses for the envelope.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_MODE_REGISTRY: List[Dict[str, Any]] = []


def get_mode_registry(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_MODE_REGISTRY[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def create_mode(
    name: str,
    description: str,
    constraints: Dict[str, Any] | None = None,
    persona_id: str | None = None,
) -> Dict[str, Any]:
    """Create a new orchestration mode (operator-triggered only)."""
    mode = {
        "mode_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "constraints": dict(constraints or {}),
        "persona_id": persona_id,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _MODE_REGISTRY.append(mode)

    _add_insight(
        "mode_definition",
        f"mode '{name}' created",
        {"mode_id": mode["mode_id"], "name": name},
        [mode["mode_id"]],
    )

    return dict(mode)


def list_modes() -> List[Dict[str, Any]]:
    return [
        {
            "mode_id": m["mode_id"],
            "name": m["name"],
            "description": m["description"],
            "persona_id": m["persona_id"],
            "created_at": m["created_at"],
        }
        for m in _MODE_REGISTRY
    ]


def get_mode(mode_id: str) -> Optional[Dict[str, Any]]:
    for m in _MODE_REGISTRY:
        if m["mode_id"] == mode_id:
            return dict(m)
    return None
