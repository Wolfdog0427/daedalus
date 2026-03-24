# runtime/tier3_objectives.py
"""
Operator-defined governance objectives.

An objective declares target metrics the governance system should
aim for.  Objectives are never auto-enforced — they exist as
read-only reference points for alignment scoring and meta-modeling.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_OBJECTIVE_REGISTRY: List[Dict[str, Any]] = []


def get_objective_registry(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_OBJECTIVE_REGISTRY[-limit:])


def create_objective(
    name: str,
    description: str,
    target_metrics: Dict[str, Any] | None = None,
    target_maturity_tier: str | None = None,
    target_risk_tier: str | None = None,
    target_sla_pass_rate: float | None = None,
) -> Dict[str, Any]:
    """Create a new governance objective (operator-triggered only)."""
    obj = {
        "objective_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "target_metrics": target_metrics or {},
        "target_maturity_tier": target_maturity_tier,
        "target_risk_tier": target_risk_tier,
        "target_sla_pass_rate": target_sla_pass_rate,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _OBJECTIVE_REGISTRY.append(obj)
    return dict(obj)


def list_objectives() -> List[Dict[str, Any]]:
    return [
        {
            "objective_id": o["objective_id"],
            "name": o["name"],
            "description": o["description"],
            "created_at": o["created_at"],
        }
        for o in _OBJECTIVE_REGISTRY
    ]


def get_objective(objective_id: str) -> Optional[Dict[str, Any]]:
    for o in _OBJECTIVE_REGISTRY:
        if o["objective_id"] == objective_id:
            return dict(o)
    return None
