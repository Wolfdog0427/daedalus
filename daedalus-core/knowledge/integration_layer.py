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

from typing import Dict, Any, List, Optional

from knowledge.autonomy_governor import guard_action
from knowledge.storage_manager import maintenance_cycle
from knowledge.consistency_checker import run_consistency_check
from knowledge.concept_evolver import evolution_cycle, scoped_evolution_cycle
from knowledge.verification_pipeline import verify_new_information
from knowledge.reasoning_engine import reason_about_claim
from knowledge.curiosity_engine import (
    run_curiosity_cycle,
    approve_and_plan,
    run_quality_gate,
)
from knowledge.batch_ingestion import ingest_batch
from knowledge.adaptive_pacer import compute_pace, record_batch_result, should_acquire_now


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

def _safe_exec(action: str, fn, **extra) -> Dict[str, Any]:
    """Run *fn* inside a governed error boundary."""
    try:
        result = fn()
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "error": f"{type(exc).__name__}: {exc}",
            **extra,
        }
    return {"action": action, "allowed": True, "result": result, **extra}


def do_storage_maintenance() -> Dict[str, Any]:
    action = "maintenance.storage"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, maintenance_cycle)


def do_consistency_scan() -> Dict[str, Any]:
    action = "maintenance.consistency_scan"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, run_consistency_check)


def do_concept_evolution() -> Dict[str, Any]:
    action = "concept.evolve"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, evolution_cycle)


def do_claim_verification(claim: str) -> Dict[str, Any]:
    action = "knowledge.verify"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: verify_new_information(claim, source="integration_layer"),
        claim=claim,
    )


def do_reasoning(claim: str) -> Dict[str, Any]:
    """
    Governed reasoning. reason_about_claim can trigger verification
    (which mutates the KB) for uncertain/unknown claims, so this
    must go through guard_action.
    """
    action = "knowledge.reason"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: reason_about_claim(claim),
        claim=claim,
    )


# ------------------------------------------------------------
# CURIOSITY & KNOWLEDGE ACQUISITION (Part 1 integration)
# ------------------------------------------------------------

def do_curiosity_cycle() -> Dict[str, Any]:
    """
    Run the curiosity engine to detect gaps and propose goals.
    Read-only gap detection is always allowed. Goal proposals are
    governed by the tier system.
    """
    action = "knowledge.curiosity_cycle"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(action, run_curiosity_cycle)


def do_approve_knowledge_goal(goal_id: str) -> Dict[str, Any]:
    """
    Approve a proposed knowledge goal and generate its acquisition plan.
    Requires governance approval (operator or tier-appropriate auto-approve).
    """
    action = "knowledge.approve_goal"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: approve_and_plan(goal_id),
        goal_id=goal_id,
    )


def do_knowledge_acquisition(
    items: List[Dict[str, Any]],
    source: str = "acquisition",
    goal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a governed batch knowledge acquisition.
    Uses the adaptive pacer to determine batch size and verification intensity.
    Runs the quality gate after ingestion.
    """
    action = "knowledge.acquire"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    if not should_acquire_now():
        return {
            "action": action,
            "allowed": True,
            "paused": True,
            "reason": "cooldown_not_elapsed",
        }

    try:
        pace = compute_pace()

        if pace["action"] == "pause":
            return {
                "action": action,
                "allowed": True,
                "paused": True,
                "reason": pace["reason"],
                "pace": pace,
            }

        batch_size = pace["batch_size"]
        intensity = pace["verification_intensity"]
        batch_items = items[:batch_size]

        result = ingest_batch(
            items=batch_items,
            source=source,
            verification_intensity=intensity,
            goal_id=goal_id,
        )

        if result.get("quality_before") and result.get("quality_after"):
            record_batch_result(result["quality_before"], result["quality_after"])

        return {
            "action": action,
            "allowed": True,
            "pace": pace,
            "result": result,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "error": f"{type(exc).__name__}: {exc}",
        }


def do_quality_gate(goal_id: str) -> Dict[str, Any]:
    """
    Run the quality gate for an active knowledge goal.
    Persists quality metrics and may pause the goal if degradation
    is detected. Governed because it mutates goal persistence.
    """
    action = "knowledge.quality_gate"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.knowledge_goal import load_goal, save_goal

        goal = load_goal(goal_id)
        if goal is None:
            return {"action": action, "error": "goal_not_found"}

        gate = run_quality_gate(goal)

        goal.quality_after = {
            "graph_coherence": gate.get("coherence_after", 0),
            "consistency": gate.get("consistency_after", 0),
            "knowledge_quality": gate.get("quality", 0),
        }
        goal.coherence_delta = gate.get("coherence_delta", 0)
        goal.consistency_delta = gate.get("consistency_delta", 0)

        if not gate.get("passed"):
            goal.status = "paused"
        save_goal(goal)

        return {
            "action": action,
            "allowed": True,
            "goal_id": goal_id,
            "result": gate,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "goal_id": goal_id,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ------------------------------------------------------------
# META-COGNITION CYCLE
# ------------------------------------------------------------

def do_meta_cycle(claim: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a full meta-reasoning cycle. Read-heavy with potential
    maintenance side effects, so governed.
    """
    action = "meta.cycle"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.meta_reasoner import run_meta_cycle
        result = run_meta_cycle(claim=claim)
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except Exception as exc:
        return {
            "action": action,
            "allowed": True,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ------------------------------------------------------------
# PROVIDER DISCOVERY (governed wrapper)
# ------------------------------------------------------------

def do_provider_discovery() -> Dict[str, Any]:
    """
    Run LLM/AGI provider discovery. Read-only scanning is low-risk
    but activation requires governance.
    """
    action = "providers.discover"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.provider_discovery import run_discovery_cycle, provider_registry
        result = run_discovery_cycle(provider_registry)
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except ImportError:
        return {"action": action, "error": "provider_discovery_not_available"}


# ------------------------------------------------------------
# FLOW TUNING (governed wrapper)
# ------------------------------------------------------------

def do_flow_tuning() -> Dict[str, Any]:
    """
    Run flow tuning cycle. Adjusts pipeline parameters.
    """
    action = "pipeline.tune"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    try:
        from knowledge.flow_tuner import flow_tuner
        result = flow_tuner.tune()
        return {
            "action": action,
            "allowed": True,
            "result": result,
        }
    except ImportError:
        return {"action": action, "error": "flow_tuner_not_available"}


# ------------------------------------------------------------
# SCOPED EVOLUTION (Part 2 acceleration)
# ------------------------------------------------------------

def do_scoped_evolution(cluster_entities: List[str]) -> Dict[str, Any]:
    """
    Run concept evolution scoped to a specific cluster rather than
    the entire graph. Faster and safer for post-acquisition refinement.
    """
    action = "concept.evolve_scoped"
    guard = guard_action(action)

    if not guard["allowed"]:
        return _blocked(action, guard)

    return _safe_exec(
        action,
        lambda: scoped_evolution_cycle(cluster_entities),
    )
