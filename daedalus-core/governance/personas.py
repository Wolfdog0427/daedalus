# governance/personas.py
"""
Governance personas for Daedalus.

Each persona defines a decision style, risk posture, allowed/forbidden
governance operations, escalation rules, and operator-override behavior.
Personas are declarative and read-only — they never auto-activate.
"""

from __future__ import annotations

import copy
import threading
from typing import Any, Dict, List, Optional

_persona_lock = threading.Lock()

ARCHITECT_GOV = "ARCHITECT_GOV"
SENTINEL_GOV = "SENTINEL_GOV"
ORACLE_GOV = "ORACLE_GOV"
SCRIBE_GOV = "SCRIBE_GOV"
COMPANION_GOV = "COMPANION_GOV"

_PERSONAS: Dict[str, Dict[str, Any]] = {
    ARCHITECT_GOV: {
        "name": "Architect",
        "description": "Structural governance — emphasises system integrity, "
                       "change contracts, and architectural coherence.",
        "decision_style": "structural",
        "risk_posture": "moderate",
        "allowed_operations": [
            "propose_change", "review_patch", "evaluate_drift",
            "score_risk", "approve_reversible",
        ],
        "forbidden_operations": [
            "approve_irreversible_without_operator",
            "modify_safety_invariants",
            "bypass_approval_gate",
        ],
        "escalation_rules": {
            "on_high_risk": "require_operator_approval",
            "on_invariant_violation": "block_and_log",
        },
        "operator_override": "always_honoured",
    },
    SENTINEL_GOV: {
        "name": "Sentinel",
        "description": "Defensive governance — prioritises safety, blocks "
                       "risky changes, strict approval requirements.",
        "decision_style": "conservative",
        "risk_posture": "low",
        "allowed_operations": [
            "evaluate_drift", "score_risk", "enforce_invariants",
            "trigger_circuit_breaker", "review_patch",
        ],
        "forbidden_operations": [
            "approve_irreversible_without_operator",
            "modify_safety_invariants",
            "bypass_approval_gate",
            "approve_high_risk",
        ],
        "escalation_rules": {
            "on_any_risk": "require_operator_approval",
            "on_invariant_violation": "kill_switch",
        },
        "operator_override": "always_honoured",
    },
    ORACLE_GOV: {
        "name": "Oracle",
        "description": "Analytical governance — integrative pattern analysis, "
                       "drift forecasting, long-arc governance insights.",
        "decision_style": "integrative",
        "risk_posture": "moderate",
        "allowed_operations": [
            "evaluate_drift", "score_risk", "propose_change",
            "forecast_drift", "compute_governance_health",
        ],
        "forbidden_operations": [
            "approve_irreversible_without_operator",
            "modify_safety_invariants",
            "bypass_approval_gate",
            "patch_apply",
        ],
        "escalation_rules": {
            "on_high_risk": "require_operator_approval",
            "on_invariant_violation": "block_and_log",
        },
        "operator_override": "always_honoured",
    },
    SCRIBE_GOV: {
        "name": "Scribe",
        "description": "Documentation governance — emphasises audit trails, "
                       "change documentation, and operational transparency.",
        "decision_style": "documentary",
        "risk_posture": "neutral",
        "allowed_operations": [
            "evaluate_drift", "review_patch", "generate_audit",
            "document_change",
        ],
        "forbidden_operations": [
            "approve_irreversible_without_operator",
            "modify_safety_invariants",
            "bypass_approval_gate",
            "patch_apply",
            "approve_high_risk",
        ],
        "escalation_rules": {
            "on_any_change": "document_and_log",
            "on_invariant_violation": "block_and_log",
        },
        "operator_override": "always_honoured",
    },
    COMPANION_GOV: {
        "name": "Companion",
        "description": "Relational governance — operator-centric, supportive "
                       "framing of governance decisions, low-friction advisory.",
        "decision_style": "advisory",
        "risk_posture": "moderate",
        "allowed_operations": [
            "propose_change", "evaluate_drift", "score_risk",
            "review_patch", "advise_operator",
        ],
        "forbidden_operations": [
            "approve_irreversible_without_operator",
            "modify_safety_invariants",
            "bypass_approval_gate",
        ],
        "escalation_rules": {
            "on_high_risk": "advise_operator",
            "on_invariant_violation": "block_and_log",
        },
        "operator_override": "always_honoured",
    },
}

_active_persona: str = COMPANION_GOV


def list_personas() -> List[Dict[str, Any]]:
    return [{"persona_id": pid, **copy.deepcopy(meta)} for pid, meta in _PERSONAS.items()]


def get_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    p = _PERSONAS.get(persona_id)
    if p is None:
        return None
    return {"persona_id": persona_id, **copy.deepcopy(p)}


def get_active_persona() -> Dict[str, Any]:
    with _persona_lock:
        pid = _active_persona
    return get_persona(pid) or get_persona(COMPANION_GOV)  # type: ignore


def set_active_persona(persona_id: str, reason: str = "") -> Dict[str, Any]:
    global _active_persona
    if persona_id not in _PERSONAS:
        return {"success": False, "reason": f"unknown persona '{persona_id}'"}
    with _persona_lock:
        prev = _active_persona
        _active_persona = persona_id
    return {"success": True, "from": prev, "to": persona_id, "reason": reason}


def is_operation_allowed(operation: str) -> bool:
    """Check if an operation is allowed under the active persona."""
    with _persona_lock:
        pid = _active_persona
    p = _PERSONAS.get(pid, _PERSONAS[COMPANION_GOV])
    if operation in p.get("forbidden_operations", []):
        return False
    allowed = p.get("allowed_operations", [])
    return not allowed or operation in allowed
