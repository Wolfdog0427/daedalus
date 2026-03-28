# governance/change_contracts.py
"""
Change contracts for Daedalus governance.

Defines which changes are allowed, forbidden, reversible, or
irreversible, along with operator-approval requirements and risk
scoring rules.  All contracts are evaluated read-only and never
mutate system state.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

_ALLOWED_CHANGE_TYPES = {
    "posture_transition", "tier_change", "expression_profile_change",
    "continuity_update", "coherence_correction",
    "resonance_update", "governance_persona_change", "governance_mode_change",
    "patch_apply", "patch_rollback", "proposal_create",
    "self_modification",
}

_FORBIDDEN_CHANGE_TYPES = {
    "safety_invariant_modification", "tier1_safety_bypass",
    "autonomy_expansion", "personal_data_persistence",
}

_ALWAYS_REVERSIBLE = {
    "posture_transition", "tier_change", "expression_profile_change",
    "governance_persona_change", "governance_mode_change",
    "continuity_update", "coherence_correction",
    "resonance_update",
}

_REQUIRES_OPERATOR_APPROVAL = {
    "patch_apply", "self_modification",
}

# Self-modification targets that touch protected domains. These always
# require explicit operator approval with a detailed impact explanation,
# regardless of risk score. The system can grow its knowledge and improve
# its reasoning autonomously, but it cannot alter its own governance,
# identity, or safety boundaries without the operator's direction.
_PROTECTED_SELF_MOD_TARGETS = {
    "governance", "invariant", "safety", "identity", "constitutional",
    "autonomy", "tier_system", "operator_trust", "kernel", "permission",
    "self_modification_rules", "drift_guard",
}

_CONTRACT_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 100
_contract_lock = threading.Lock()


def evaluate_change(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a change request against governance contracts.

    Returns a structured verdict: allowed/forbidden/needs_approval,
    risk score, reversibility status.

    Self-modification is tiered:
    - Knowledge growth (learning, reasoning improvement): autonomous
    - Changes touching protected domains (governance, identity, safety,
      invariants): requires explicit operator approval with a detailed
      short-term and long-term impact explanation
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

    # Tiered self-modification: check if the target touches a protected domain
    if cr_type == "self_modification":
        target = str(change_request.get("target") or "").lower()
        description = str(change_request.get("description") or "").lower()
        combined = f"{target} {description}"
        touches_protected = any(
            kw in combined for kw in _PROTECTED_SELF_MOD_TARGETS
        )
        if touches_protected:
            flags = change_request.get("flags") or []
            impact = change_request.get("impact_explanation")
            if "operator_approved" not in flags or not impact:
                result = {
                    "allowed": False,
                    "reason": (
                        f"self-modification touches protected domain "
                        f"({target}). Requires explicit operator approval "
                        f"with short-term and long-term impact explanation."
                    ),
                    "risk_score": 90,
                    "reversible": True,
                    "needs_approval": True,
                    "requires_impact_explanation": impact is None,
                    "missing_operator_approval": "operator_approved" not in flags,
                    "protected_domain": True,
                }
                _log_contract(cr_type, result)
                return result
            risk = max(risk, 60)
        else:
            # Knowledge growth, reasoning improvement, etc.: autonomous
            # Lower risk, no operator approval needed for routine growth
            needs_approval = False
            risk = max(risk, 30)

    try:
        from governance.modes import get_safety_multiplier
        risk = min(100, int(risk * get_safety_multiplier()))
    except Exception:
        risk = min(100, int(risk * 2.0))

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
    """Enforce the contract by evaluating the change request.

    Safety invariants are checked separately by the governance kernel
    (kernel.evaluate_change step 2) so they are not re-checked here
    to avoid redundant work.
    """
    return evaluate_change(change_request)


def score_risk(change_request: Dict[str, Any]) -> int:
    """Compute a risk score (0-100) for a change request."""
    base = 10
    cr_type = change_request.get("type", "")

    if cr_type == "patch_apply":
        base = 50
    elif cr_type == "self_modification":
        target = str(change_request.get("target") or "").lower()
        description = str(change_request.get("description") or "").lower()
        combined = f"{target} {description}"
        if any(kw in combined for kw in _PROTECTED_SELF_MOD_TARGETS):
            base = 70
        else:
            base = 30
    elif cr_type in ("tier_change", "posture_transition"):
        base = 20
    elif cr_type in ("governance_persona_change", "governance_mode_change"):
        base = 30

    if not change_request.get("reversible", True):
        base += 30
    if "operator_approved" not in (change_request.get("flags") or []):
        base += 10

    return min(100, base)


def get_contract_log(limit: int = 20) -> List[Dict[str, Any]]:
    n = max(0, int(limit))
    with _contract_lock:
        return [dict(e) for e in _CONTRACT_LOG[-n:]] if n > 0 else []


def _log_contract(change_type: str, result: Dict[str, Any]) -> None:
    with _contract_lock:
        _CONTRACT_LOG.append({
            "change_type": change_type,
            "allowed": result.get("allowed"),
            "risk_score": result.get("risk_score"),
            "needs_approval": result.get("needs_approval"),
            "timestamp": time.time(),
        })
        if len(_CONTRACT_LOG) > _MAX_LOG:
            _CONTRACT_LOG[:] = _CONTRACT_LOG[-_MAX_LOG:]
