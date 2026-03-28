# governance/safety_invariants.py
"""
Global safety invariants for Daedalus governance.

These invariants are unconditional and cannot be overridden by any
persona, mode, or operator command.  They form the constitutional
floor of the governance system.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

_INVARIANTS: List[Dict[str, Any]] = [
    {
        "id": "NO_AUTONOMY_EXPANSION",
        "description": "No change may expand autonomy beyond existing global rules.",
        "category": "autonomy",
    },
    {
        "id": "NO_SAFETY_BYPASS",
        "description": "No change may bypass Tier-1 safety checks.",
        "category": "safety",
    },
    {
        "id": "NO_PERSONAL_DATA_PERSISTENCE",
        "description": "No personal data may be persisted across sessions.",
        "category": "privacy",
    },
    {
        "id": "NO_EMOTIONAL_INFERENCE",
        "description": "No module may infer or model operator emotional state.",
        "category": "privacy",
    },
    {
        "id": "NO_PSYCHOLOGICAL_MODELING",
        "description": "No module may build psychological models of the operator.",
        "category": "privacy",
    },
    {
        "id": "NO_SELF_MODIFICATION_WITHOUT_APPROVAL",
        "description": "No self-modification without explicit operator approval.",
        "category": "sovereignty",
    },
    {
        "id": "OPERATOR_OVERRIDE_SOVEREIGN",
        "description": "Operator commands override all governance suggestions "
                       "(but never override Tier-1 safety).",
        "category": "sovereignty",
    },
    {
        "id": "REVERSIBILITY_DEFAULT",
        "description": "All changes must be reversible unless the operator "
                       "explicitly approves irreversibility.",
        "category": "reversibility",
    },
]

_VIOLATION_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 100
_violation_lock = threading.Lock()


def list_invariants() -> List[Dict[str, Any]]:
    return list(_INVARIANTS)


def get_invariant(invariant_id: str) -> Dict[str, Any] | None:
    for inv in _INVARIANTS:
        if inv["id"] == invariant_id:
            return dict(inv)
    return None


def enforce_invariants(change_request: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Check all invariants against an optional change request.

    Returns {"passed": True/False, "violations": [...]}.
    """
    violations: List[Dict[str, Any]] = []

    if change_request is None:
        return {"passed": True, "violations": [], "checked": len(_INVARIANTS)}

    cr_type = change_request.get("type", "")
    cr_target = change_request.get("target", "")
    cr_flags = set(change_request.get("flags") or [])

    if "expand_autonomy" in cr_flags:
        violations.append({"invariant": "NO_AUTONOMY_EXPANSION",
                           "detail": "change requests autonomy expansion"})

    if "bypass_safety" in cr_flags:
        violations.append({"invariant": "NO_SAFETY_BYPASS",
                           "detail": "change requests safety bypass"})

    if "persist_personal_data" in cr_flags:
        violations.append({"invariant": "NO_PERSONAL_DATA_PERSISTENCE",
                           "detail": "change persists personal data"})

    if "emotional_inference" in cr_flags:
        violations.append({"invariant": "NO_EMOTIONAL_INFERENCE",
                           "detail": "change introduces emotional inference"})

    if "psychological_model" in cr_flags:
        violations.append({"invariant": "NO_PSYCHOLOGICAL_MODELING",
                           "detail": "change introduces psychological modeling"})

    if cr_type == "self_modification" and "operator_approved" not in cr_flags:
        _protected = {
            "governance", "invariant", "safety", "identity", "constitutional",
            "autonomy", "tier_system", "operator_trust", "kernel", "permission",
            "self_modification_rules", "drift_guard",
        }
        combined = f"{cr_target} {change_request.get('description', '')}".lower()
        if any(kw in combined for kw in _protected):
            violations.append({"invariant": "NO_SELF_MODIFICATION_WITHOUT_APPROVAL",
                               "detail": "self-modification of protected domain without operator approval"})

    if not change_request.get("reversible", True) and "operator_approved_irreversible" not in cr_flags:
        violations.append({"invariant": "REVERSIBILITY_DEFAULT",
                           "detail": "irreversible change without operator approval"})

    with _violation_lock:
        for v in violations:
            _VIOLATION_LOG.append({**v, "timestamp": time.time(),
                                   "change_type": cr_type, "target": cr_target})
        if len(_VIOLATION_LOG) > _MAX_LOG:
            _VIOLATION_LOG[:] = _VIOLATION_LOG[-_MAX_LOG:]

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "checked": len(_INVARIANTS),
    }


def get_violation_log(limit: int = 20) -> List[Dict[str, Any]]:
    with _violation_lock:
        return list(_VIOLATION_LOG[-limit:])
