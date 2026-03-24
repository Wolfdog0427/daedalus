# governance/change_contracts.py
"""
Change contracts for Daedalus governance.

Defines which changes are allowed, forbidden, reversible, or
irreversible, along with operator-approval requirements and risk
scoring rules.  All contracts are evaluated read-only and never
mutate system state.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_ALLOWED_CHANGE_TYPES = {
    "posture_transition", "tier_change", "expression_profile_change",
    "continuity_update", "coherence_correction", "stability_update",
    "resonance_update", "governance_persona_change", "governance_mode_change",
    "patch_apply", "patch_rollback", "proposal_create",
}

_FORBIDDEN_CHANGE_TYPES = {
    "safety_invariant_modification", "tier1_safety_bypass",
    "autonomy_expansion", "personal_data_persistence",
}

_ALWAYS_REVERSIBLE = {
    "posture_transition", "tier_change", "expression_profile_change",
    "governance_persona_change", "governance_mode_change",
    "continuity_update", "coherence_correction", "stability_update",
    "resonance_update",
}

_REQUIRES_OPERATOR_APPROVAL = {
    "patch_apply", "self_modification",
}

_CONTRACT_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 100


def evaluate_change(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a change request against governance contracts.

    Returns a structured verdict: allowed/forbidden/needs_approval,
    risk score, reversibility status.
    """
    cr_type = change_request.get("type", "unknown")

    if cr_type in _FORBIDDEN_CHANGE_TYPES:
        result = {
            "allowed": False,
            "reason": f"change type '{cr_type}' is forbidden by contract",
            "risk_score": 100,
            "reversible": False,
            "needs_approval": False,
        }
        _log_contract(cr_type, result)
        return result

    if cr_type not in _ALLOWED_CHANGE_TYPES:
        result = {
            "allowed": False,
            "reason": f"change type '{cr_type}' is not in allowed set",
            "risk_score": 80,
            "reversible": False,
            "needs_approval": True,
        }
        _log_contract(cr_type, result)
        return result

    reversible = cr_type in _ALWAYS_REVERSIBLE
    needs_approval = cr_type in _REQUIRES_OPERATOR_APPROVAL
    risk = score_risk(change_request)

    try:
        from governance.modes import get_safety_multiplier
        risk = min(100, int(risk * get_safety_multiplier()))
    except Exception:
        pass

    if risk >= 70:
        needs_approval = True

    result = {
        "allowed": True,
        "reason": f"change type '{cr_type}' is permitted",
        "risk_score": risk,
        "reversible": reversible,
        "needs_approval": needs_approval,
    }
    _log_contract(cr_type, result)
    return result


def enforce_contract(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce the contract: evaluate + check safety invariants.

    Returns a combined verdict.
    """
    contract_result = evaluate_change(change_request)

    try:
        from governance.safety_invariants import enforce_invariants
        inv_result = enforce_invariants(change_request)
        if not inv_result["passed"]:
            contract_result["allowed"] = False
            contract_result["reason"] = (
                f"safety invariant violated: "
                f"{inv_result['violations'][0]['detail']}"
            )
            contract_result["invariant_violations"] = inv_result["violations"]
    except Exception:
        pass

    return contract_result


def score_risk(change_request: Dict[str, Any]) -> int:
    """Compute a risk score (0-100) for a change request."""
    base = 10
    cr_type = change_request.get("type", "")

    if cr_type in ("patch_apply", "self_modification"):
        base = 50
    elif cr_type in ("tier_change", "posture_transition"):
        base = 20
    elif cr_type in ("governance_persona_change", "governance_mode_change"):
        base = 30

    if not change_request.get("reversible", True):
        base += 30
    if "operator_approved" not in change_request.get("flags", []):
        base += 10

    return min(100, base)


def get_contract_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_CONTRACT_LOG[-limit:])


def _log_contract(change_type: str, result: Dict[str, Any]) -> None:
    _CONTRACT_LOG.append({
        "change_type": change_type,
        "allowed": result.get("allowed"),
        "risk_score": result.get("risk_score"),
        "needs_approval": result.get("needs_approval"),
        "timestamp": time.time(),
    })
    if len(_CONTRACT_LOG) > _MAX_LOG:
        _CONTRACT_LOG[:] = _CONTRACT_LOG[-_MAX_LOG:]
