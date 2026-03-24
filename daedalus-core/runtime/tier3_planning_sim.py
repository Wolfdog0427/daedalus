# runtime/tier3_planning_sim.py
"""
Read-only plan impact simulation.

Estimates drift reduction, readiness improvement, anomaly reduction,
and risk tradeoffs for a governance plan without mutating any state.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_PLAN_SIM_LOG: List[Dict[str, Any]] = []


def get_plan_sim_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_PLAN_SIM_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def simulate_plan_impact(plan_id: str) -> Dict[str, Any]:
    """Estimate the impact of executing a governance plan."""
    try:
        from runtime.tier3_planning import get_governance_plan
        plan = get_governance_plan(plan_id)
        if plan is None:
            return {"error": True, "reason": f"plan '{plan_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read plan"}

    phases = plan.get("phases", [])
    n_actions = sum(len(p.get("recommended_actions", [])) for p in phases)

    # --- Estimate drift reduction ---
    drift_reduction_pct = 0
    anomaly_actions = sum(
        1 for p in phases for a in p.get("recommended_actions", [])
        if a.get("action") == "investigate_anomaly"
    )
    if anomaly_actions > 0:
        drift_reduction_pct = min(anomaly_actions * 15, 60)

    # --- Estimate readiness improvement ---
    readiness_improvement_pct = 0
    optimization_phases = [
        p for p in phases
        if "optimization" in p.get("goal", "")
    ]
    if optimization_phases:
        opt_actions = sum(
            len(p.get("recommended_actions", []))
            for p in optimization_phases
        )
        readiness_improvement_pct = min(opt_actions * 10, 50)

    # --- Estimate anomaly reduction ---
    anomaly_reduction_pct = 0
    anomaly_phase = [
        p for p in phases
        if "anomal" in p.get("goal", "")
    ]
    if anomaly_phase:
        anomaly_reduction_pct = min(anomaly_actions * 20, 70)

    # --- Risk tradeoffs ---
    risks: List[str] = list(plan.get("risk_considerations", []))
    if n_actions > 10:
        risks.append("large plan — execution may take multiple sessions")
    if drift_reduction_pct == 0 and anomaly_reduction_pct == 0:
        risks.append("plan may not materially reduce drift or anomalies")

    confidence = plan.get("confidence", "low")

    result = {
        "plan_id": plan_id,
        "scope": plan.get("scope", "?"),
        "n_phases": len(phases),
        "n_actions": n_actions,
        "estimated_drift_reduction_pct": drift_reduction_pct,
        "estimated_readiness_improvement_pct": readiness_improvement_pct,
        "estimated_anomaly_reduction_pct": anomaly_reduction_pct,
        "risk_tradeoffs": risks,
        "confidence": confidence,
        "timestamp": time.time(),
    }

    _PLAN_SIM_LOG.append({
        "type": "plan_impact",
        "plan_id": plan_id,
        "drift_reduction": drift_reduction_pct,
        "readiness_improvement": readiness_improvement_pct,
        "anomaly_reduction": anomaly_reduction_pct,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "plan_simulation",
        (f"plan {plan_id[:8]}.. impact: "
         f"drift -{drift_reduction_pct}%, "
         f"readiness +{readiness_improvement_pct}%, "
         f"anomalies -{anomaly_reduction_pct}%"),
        {"plan_id": plan_id,
         "drift_reduction": drift_reduction_pct,
         "readiness_improvement": readiness_improvement_pct,
         "anomaly_reduction": anomaly_reduction_pct},
        [plan_id],
    )

    return result
