# runtime/tier3_planning.py
"""
Governance-wide planning and strategic runbook generation.

Synthesizes forecasts, anomalies, strategy models, optimizations, and
simulations into structured, multi-phase governance plans.  Plans are
purely descriptive and never mutate state.  Strategic runbooks convert
a plan's recommendations into a draft runbook via existing creation
APIs but never execute it.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_PLAN_REGISTRY: List[Dict[str, Any]] = []
_PLANNING_LOG: List[Dict[str, Any]] = []


def get_planning_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_PLANNING_LOG[-limit:])


def get_plan_registry(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_PLAN_REGISTRY[-limit:])


def get_governance_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    for p in _PLAN_REGISTRY:
        if p["plan_id"] == plan_id:
            return p
    return None


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


# ------------------------------------------------------------------
# Internal helpers — gather signals
# ------------------------------------------------------------------

def _gather_strategy(horizon: int) -> Dict[str, Any]:
    try:
        from runtime.tier3_strategy import model_governance_trajectory
        return model_governance_trajectory(horizon)
    except Exception:
        return {}


def _gather_optimizations() -> List[Dict[str, str]]:
    try:
        from runtime.tier3_strategy import suggest_governance_optimizations
        return suggest_governance_optimizations().get("suggestions", [])
    except Exception:
        return []


def _gather_env_strategy(env_id: str, horizon: int) -> Dict[str, Any]:
    try:
        from runtime.tier3_strategy import model_environment_evolution
        return model_environment_evolution(env_id, horizon)
    except Exception:
        return {}


def _gather_env_optimizations(env_id: str) -> List[Dict[str, str]]:
    try:
        from runtime.tier3_strategy import suggest_environment_optimizations
        r = suggest_environment_optimizations(env_id)
        return r.get("suggestions", []) if not r.get("error") else []
    except Exception:
        return []


def _gather_policy_strategy(policy_id: str, horizon: int) -> Dict[str, Any]:
    try:
        from runtime.tier3_strategy import model_policy_lifecycle
        return model_policy_lifecycle(policy_id, horizon)
    except Exception:
        return {}


def _gather_policy_optimizations(policy_id: str) -> List[Dict[str, str]]:
    try:
        from runtime.tier3_strategy import suggest_policy_optimizations
        r = suggest_policy_optimizations(policy_id)
        return r.get("suggestions", []) if not r.get("error") else []
    except Exception:
        return []


def _gather_anomalies() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_anomaly import get_anomaly_registry
        return get_anomaly_registry(20)
    except Exception:
        return []


def _gather_forecasts() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_forecast import get_forecast_log
        return get_forecast_log(20)
    except Exception:
        return []


# ------------------------------------------------------------------
# Build phases from signals
# ------------------------------------------------------------------

def _build_phases(
    projections: List[Dict[str, str]],
    suggestions: List[Dict[str, str]],
    anomalies: List[Dict[str, Any]],
    forecasts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert raw signals into ordered plan phases."""
    phases: List[Dict[str, Any]] = []

    critical_anomalies = [a for a in anomalies if a.get("severity") == "high"]
    if critical_anomalies:
        phases.append({
            "phase": 1,
            "goal": "resolve critical anomalies",
            "rationale": f"{len(critical_anomalies)} high-severity anomalies detected",
            "recommended_actions": [
                {"action": "investigate_anomaly", "detail": a.get("detail", "?")[:80]}
                for a in critical_anomalies[:5]
            ],
        })

    concern_projs = [p for p in projections
                     if p["projection"] not in ("governance_stable",
                                                 "environment_stable",
                                                 "policy_stable")]
    if concern_projs:
        phase_num = len(phases) + 1
        phases.append({
            "phase": phase_num,
            "goal": "address strategic projections",
            "rationale": f"{len(concern_projs)} projection(s) require attention",
            "recommended_actions": [
                {"action": "review_projection", "detail": p.get("detail", "")}
                for p in concern_projs[:5]
            ],
        })

    if suggestions:
        phase_num = len(phases) + 1
        phases.append({
            "phase": phase_num,
            "goal": "apply optimization suggestions",
            "rationale": f"{len(suggestions)} optimization(s) identified",
            "recommended_actions": [
                {"action": s.get("category", "optimize"),
                 "detail": s.get("suggestion", "")}
                for s in suggestions[:5]
            ],
        })

    negative_fc = [f for f in forecasts
                   if "increase" in f.get("prediction", "")
                   or "declining" in f.get("prediction", "")]
    if negative_fc:
        phase_num = len(phases) + 1
        phases.append({
            "phase": phase_num,
            "goal": "mitigate negative forecast trends",
            "rationale": f"{len(negative_fc)} negative forecast(s)",
            "recommended_actions": [
                {"action": "review_forecast",
                 "detail": f.get("prediction", "?")}
                for f in negative_fc[:5]
            ],
        })

    if not phases:
        phases.append({
            "phase": 1,
            "goal": "maintain current governance posture",
            "rationale": "no significant concerns detected",
            "recommended_actions": [
                {"action": "continue_monitoring",
                 "detail": "system is stable — continue routine evaluation"},
            ],
        })

    return phases


def _compute_risks(
    anomalies: List[Dict[str, Any]],
    projections: List[Dict[str, str]],
) -> List[str]:
    risks: List[str] = []
    if anomalies:
        risks.append(f"{len(anomalies)} outstanding anomalies may delay plan execution")
    concern = [p for p in projections
               if p["projection"] not in ("governance_stable",
                                           "environment_stable",
                                           "policy_stable")]
    if concern:
        risks.append(f"{len(concern)} strategic concern(s) may evolve before plan completes")
    if not risks:
        risks.append("no significant risks identified")
    return risks


def _compute_dependencies(phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deps: List[Dict[str, Any]] = []
    for i in range(1, len(phases)):
        deps.append({
            "phase": phases[i]["phase"],
            "depends_on": phases[i - 1]["phase"],
        })
    return deps


# ------------------------------------------------------------------
# Plan generators
# ------------------------------------------------------------------

def generate_governance_plan(horizon: int = 10) -> Dict[str, Any]:
    """Generate a system-wide governance plan."""
    strategy = _gather_strategy(horizon)
    suggestions = _gather_optimizations()
    anomalies = _gather_anomalies()
    forecasts = _gather_forecasts()

    projections = strategy.get("projections", [])
    phases = _build_phases(projections, suggestions, anomalies, forecasts)
    risks = _compute_risks(anomalies, projections)
    deps = _compute_dependencies(phases)

    plan = {
        "plan_id": str(uuid.uuid4()),
        "scope": "system",
        "horizon": horizon,
        "phases": phases,
        "dependencies": deps,
        "risk_considerations": risks,
        "confidence": strategy.get("confidence", "low"),
        "timestamp": time.time(),
    }

    _PLAN_REGISTRY.append(plan)
    _PLANNING_LOG.append({
        "type": "governance_plan",
        "plan_id": plan["plan_id"],
        "n_phases": len(phases),
        "timestamp": plan["timestamp"],
    })
    _add_insight(
        "governance_plan",
        f"governance plan: {len(phases)} phase(s), confidence={plan['confidence']}",
        {"plan_id": plan["plan_id"], "phases": len(phases)},
    )

    return plan


def generate_environment_plan(
    env_id: str,
    horizon: int = 10,
) -> Dict[str, Any]:
    """Generate a plan scoped to a single environment."""
    strategy = _gather_env_strategy(env_id, horizon)
    if strategy.get("error"):
        return strategy

    suggestions = _gather_env_optimizations(env_id)
    anomalies = _gather_anomalies()
    forecasts = _gather_forecasts()

    projections = strategy.get("projections", [])
    phases = _build_phases(projections, suggestions, anomalies, forecasts)
    risks = _compute_risks(anomalies, projections)
    deps = _compute_dependencies(phases)

    plan = {
        "plan_id": str(uuid.uuid4()),
        "scope": "environment",
        "scope_id": env_id,
        "scope_name": strategy.get("env_name", "?"),
        "horizon": horizon,
        "phases": phases,
        "dependencies": deps,
        "risk_considerations": risks,
        "confidence": strategy.get("confidence", "low"),
        "timestamp": time.time(),
    }

    _PLAN_REGISTRY.append(plan)
    _PLANNING_LOG.append({
        "type": "environment_plan",
        "plan_id": plan["plan_id"],
        "env_id": env_id,
        "n_phases": len(phases),
        "timestamp": plan["timestamp"],
    })
    _add_insight(
        "governance_plan",
        f"env plan '{strategy.get('env_name', '?')}': {len(phases)} phase(s)",
        {"plan_id": plan["plan_id"], "env_id": env_id, "phases": len(phases)},
        [env_id],
    )

    return plan


def generate_policy_plan(
    policy_id: str,
    horizon: int = 10,
) -> Dict[str, Any]:
    """Generate a plan scoped to a single policy."""
    strategy = _gather_policy_strategy(policy_id, horizon)
    if strategy.get("error"):
        return strategy

    suggestions = _gather_policy_optimizations(policy_id)
    anomalies = _gather_anomalies()
    forecasts = _gather_forecasts()

    projections = strategy.get("projections", [])
    phases = _build_phases(projections, suggestions, anomalies, forecasts)
    risks = _compute_risks(anomalies, projections)
    deps = _compute_dependencies(phases)

    plan = {
        "plan_id": str(uuid.uuid4()),
        "scope": "policy",
        "scope_id": policy_id,
        "scope_name": strategy.get("policy_name", "?"),
        "horizon": horizon,
        "phases": phases,
        "dependencies": deps,
        "risk_considerations": risks,
        "confidence": strategy.get("confidence", "low"),
        "timestamp": time.time(),
    }

    _PLAN_REGISTRY.append(plan)
    _PLANNING_LOG.append({
        "type": "policy_plan",
        "plan_id": plan["plan_id"],
        "policy_id": policy_id,
        "n_phases": len(phases),
        "timestamp": plan["timestamp"],
    })
    _add_insight(
        "governance_plan",
        f"policy plan '{strategy.get('policy_name', '?')}': {len(phases)} phase(s)",
        {"plan_id": plan["plan_id"], "policy_id": policy_id,
         "phases": len(phases)},
        [policy_id],
    )

    return plan


# ------------------------------------------------------------------
# Strategic runbook generation
# ------------------------------------------------------------------

_ACTION_TO_STEP_TYPE = {
    "investigate_anomaly": "generate_adaptive_insights",
    "review_projection": "generate_adaptive_insights",
    "review_forecast": "generate_adaptive_insights",
    "continue_monitoring": "evaluate_policies_once",
    "defaults": "evaluate_policies_once",
    "packs": "evaluate_policies_once",
    "cleanup": "evaluate_policies_once",
    "health": "evaluate_policies_scheduled_once",
    "policy_cleanup": "evaluate_policies_once",
    "policy_review": "evaluate_policies_once",
    "environment_defaults": "evaluate_policies_once",
    "environment_packs": "evaluate_policies_once",
    "pack_cleanup": "evaluate_policies_once",
    "completeness": "evaluate_policies_once",
    "scheduling": "evaluate_policies_scheduled_once",
    "lifecycle": "evaluate_policies_once",
}


def generate_strategic_runbook(plan_id: str) -> Dict[str, Any]:
    """Convert a governance plan into a draft runbook.

    Uses the existing runbook creation API. The runbook starts in
    ``draft`` status and is NEVER executed automatically.
    """
    plan = get_governance_plan(plan_id)
    if plan is None:
        return {"error": True, "reason": f"plan '{plan_id}' not found"}

    steps: List[Dict[str, Any]] = []
    for phase in plan.get("phases", []):
        for rec in phase.get("recommended_actions", []):
            action = rec.get("action", "")
            step_type = _ACTION_TO_STEP_TYPE.get(action, "evaluate_policies_once")
            steps.append({"type": step_type})

    if not steps:
        steps.append({"type": "evaluate_policies_once"})

    try:
        from runtime.tier3_runbooks import create_runbook
        scope = plan.get("scope", "system")
        scope_name = plan.get("scope_name", "")
        label = f"strategic-{scope}"
        if scope_name:
            label += f"-{scope_name}"

        runbook = create_runbook(
            name=label,
            description=f"Strategic runbook generated from plan {plan_id[:8]}..",
            steps=steps,
        )
    except Exception as exc:
        return {"error": True, "reason": f"runbook creation failed: {exc}"}

    if runbook.get("error"):
        return runbook

    runbook["strategic_origin"] = {
        "plan_id": plan_id,
        "scope": plan.get("scope"),
        "generated_at": time.time(),
    }

    _PLANNING_LOG.append({
        "type": "strategic_runbook",
        "plan_id": plan_id,
        "runbook_id": runbook.get("runbook_id", "?"),
        "n_steps": len(steps),
        "timestamp": time.time(),
    })
    _add_insight(
        "strategic_runbook",
        f"strategic runbook from plan {plan_id[:8]}.. ({len(steps)} steps)",
        {"plan_id": plan_id, "runbook_id": runbook.get("runbook_id", "?")},
        [plan_id],
    )

    return runbook
