# runtime/tier3_personas.py
"""
Operator-defined governance personas.

A persona declares a weighting profile that contextualises how KPIs,
SLAs, risk, maturity, readiness, drift, and anomalies should be
prioritised when evaluating governance posture.  Personas are never
auto-activated — they exist as read-only lenses for the envelope.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_PERSONA_REGISTRY: List[Dict[str, Any]] = []

DEFAULT_WEIGHTS: Dict[str, float] = {
    "kpis": 1.0,
    "sla": 1.0,
    "risk": 1.0,
    "maturity": 1.0,
    "readiness": 1.0,
    "drift": 1.0,
    "anomalies": 1.0,
}


def get_persona_registry(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_PERSONA_REGISTRY[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def create_persona(
    name: str,
    description: str,
    weighting_profile: Dict[str, float] | None = None,
    objective_bindings: List[str] | None = None,
) -> Dict[str, Any]:
    """Create a new governance persona (operator-triggered only)."""
    weights = dict(DEFAULT_WEIGHTS)
    if weighting_profile:
        for k, v in weighting_profile.items():
            if k in weights and isinstance(v, (int, float)):
                weights[k] = float(v)

    persona = {
        "persona_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "weighting_profile": weights,
        "objective_bindings": list(objective_bindings or []),
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _PERSONA_REGISTRY.append(persona)

    _add_insight(
        "persona_definition",
        f"persona '{name}' created",
        {"persona_id": persona["persona_id"], "name": name},
        [persona["persona_id"]],
    )

    return dict(persona)


def list_personas() -> List[Dict[str, Any]]:
    return [
        {
            "persona_id": p["persona_id"],
            "name": p["name"],
            "description": p["description"],
            "objective_bindings": p["objective_bindings"],
            "created_at": p["created_at"],
        }
        for p in _PERSONA_REGISTRY
    ]


def get_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    for p in _PERSONA_REGISTRY:
        if p["persona_id"] == persona_id:
            return dict(p)
    return None
