# knowledge/integration_layer.py

"""
Integration Layer

This module wraps all side-effectful operations and routes them
through the autonomy governor before allowing them to execute.

It ensures:
- strict mode is enforced by default
- guided/full modes unlock additional capabilities
- every action is checked, logged, and governed
- no subsystem can mutate state without passing through here

This is the enforcement layer for safe autonomy.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from knowledge.autonomy_governor import guard_action
from knowledge.storage_manager import maintenance_cycle
from knowledge.consistency_checker import run_consistency_check
from knowledge.concept_evolver import evolution_cycle
from knowledge.verification_pipeline import verify_new_information
from knowledge.reasoning_engine import reason_about_claim


# ------------------------------------------------------------
# INTERNAL HELPER
# ------------------------------------------------------------

def _blocked(action_type: str, guard: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardized blocked-action response.
    """
    return {
        "action": action_type,
        "allowed": False,
        "requires_approval": guard.get("requires_approval", True),
        "reason": guard.get("reason", "blocked"),
        "mode": guard.get("mode"),
    }


# ------------------------------------------------------------
# WRAPPED ACTIONS
# ------------------------------------------------------------

def do_storage_maintenance() -> Dict[str, Any]:
    action = "maintenance.storage"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    result = maintenance_cycle()
    return {
        "action": action,
        "allowed": True,
        "result": result,
    }


def do_consistency_scan() -> Dict[str, Any]:
    action = "maintenance.consistency_scan"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    result = run_consistency_check()
    return {
        "action": action,
        "allowed": True,
        "result": result,
    }


def do_concept_evolution() -> Dict[str, Any]:
    action = "concept.evolve"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    result = evolution_cycle()
    return {
        "action": action,
        "allowed": True,
        "result": result,
    }


def do_claim_verification(claim: str) -> Dict[str, Any]:
    action = "knowledge.verify"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    result = verify_new_information(claim, source="integration_layer")
    return {
        "action": action,
        "allowed": True,
        "claim": claim,
        "result": result,
    }


def do_reasoning(claim: str) -> Dict[str, Any]:
    """
    Reasoning is always allowed — it has no side effects.
    """
    result = reason_about_claim(claim)
    return {
        "action": "reasoning",
        "allowed": True,
        "claim": claim,
        "result": result,
    }
