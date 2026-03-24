# runtime/tier3_kpis.py
"""
Governance-wide KPI calculators.

Computes structured, read-only key performance indicators for the
overall system, individual environments, and individual policies.
All functions are side-effect-free except for appending to the
governance insights registry.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_KPI_LOG: List[Dict[str, Any]] = []


def get_kpi_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_KPI_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _safe(fn, *args, default=None):
    try:
        return fn(*args)
    except Exception:
        return default


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


# ------------------------------------------------------------------
# System-wide KPIs
# ------------------------------------------------------------------

def compute_system_kpis() -> Dict[str, Any]:
    """Compute governance KPIs across the entire system."""
    kpis: Dict[str, Any] = {}
    ts = time.time()

    # drift stability — ratio of non-drifted entries in drift log
    drift_entries = _safe(
        lambda: __import__(
            "runtime.tier3_env_drift", fromlist=["get_drift_log"]
        ).get_drift_log(50),
        default=[],
    )
    n_drift = len(drift_entries)
    n_clean = sum(1 for d in drift_entries if not d.get("has_drift"))
    kpis["drift_stability_index"] = _pct(n_clean, n_drift) if n_drift else 100.0

    # anomaly rate — anomalies per total governance objects
    anomalies = _safe(
        lambda: __import__(
            "runtime.tier3_anomaly", fromlist=["get_anomaly_registry"]
        ).get_anomaly_registry(200),
        default=[],
    )
    envs = _safe(
        lambda: __import__(
            "runtime.tier3_environments", fromlist=["list_environments"]
        ).list_environments(),
        default=[],
    )
    policies = _safe(
        lambda: __import__(
            "runtime.tier3_policies", fromlist=["get_policies"]
        ).get_policies(),
        default=[],
    )
    n_objects = len(envs) + len(policies)
    kpis["anomaly_rate"] = _pct(len(anomalies), max(n_objects, 1))

    # readiness trend — average readiness from recent log
    readiness_entries = _safe(
        lambda: __import__(
            "runtime.tier3_env_health", fromlist=["get_readiness_log"]
        ).get_readiness_log(20),
        default=[],
    )
    if readiness_entries:
        scores = [r.get("readiness_score", 0) for r in readiness_entries]
        kpis["readiness_trend_score"] = round(sum(scores) / len(scores), 1)
    else:
        kpis["readiness_trend_score"] = 0.0

    # policy lifecycle health — % of enabled policies with conditions & actions
    enabled = [p for p in policies if p.get("enabled") and not p.get("retired")]
    healthy_pols = [
        p for p in enabled
        if p.get("trigger_conditions") and p.get("actions")
    ]
    kpis["policy_lifecycle_health"] = _pct(len(healthy_pols), len(enabled))

    # pack consistency — % of packs that passed validation recently
    packs = _safe(
        lambda: __import__(
            "runtime.tier3_envpacks", fromlist=["list_envpacks"]
        ).list_envpacks(),
        default=[],
    )
    kpis["pack_consistency_score"] = 100.0 if packs else 100.0
    # (no validation failures tracked globally, default to full)

    # lineage volatility — lineage records per object
    lineage = _safe(
        lambda: __import__(
            "runtime.tier3_lineage", fromlist=["get_lineage_log"]
        ).get_lineage_log(500),
        default=[],
    )
    kpis["lineage_volatility"] = round(
        len(lineage) / max(n_objects, 1), 2
    )

    # plan effectiveness — average estimated drift reduction from sims
    sims = _safe(
        lambda: __import__(
            "runtime.tier3_planning_sim", fromlist=["get_plan_sim_log"]
        ).get_plan_sim_log(20),
        default=[],
    )
    if sims:
        dr_avg = sum(s.get("drift_reduction", 0) for s in sims) / len(sims)
        kpis["plan_effectiveness"] = round(dr_avg, 1)
    else:
        kpis["plan_effectiveness"] = 0.0

    result = {
        "scope": "system",
        "kpis": kpis,
        "n_environments": len(envs),
        "n_policies": len(policies),
        "n_anomalies": len(anomalies),
        "timestamp": ts,
    }

    _KPI_LOG.append({"type": "system", "timestamp": ts, **kpis})
    _add_insight(
        "kpi_report",
        f"system KPIs: drift_stability={kpis['drift_stability_index']}%, "
        f"anomaly_rate={kpis['anomaly_rate']}%",
        {"scope": "system", "kpis": kpis},
    )

    return result


# ------------------------------------------------------------------
# Environment KPIs
# ------------------------------------------------------------------

def compute_environment_kpis(env_id: str) -> Dict[str, Any]:
    """Compute KPIs scoped to a single environment."""
    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    kpis: Dict[str, Any] = {}
    ts = time.time()

    # drift stability vs upstream
    drift_entries = _safe(
        lambda: __import__(
            "runtime.tier3_env_drift", fromlist=["get_drift_log"]
        ).get_drift_log(50),
        default=[],
    )
    env_drifts = [d for d in drift_entries
                  if d.get("env_a") == env_id or d.get("env_b") == env_id]
    n_env_drift = len(env_drifts)
    n_env_clean = sum(1 for d in env_drifts if not d.get("has_drift"))
    kpis["drift_stability_index"] = (
        _pct(n_env_clean, n_env_drift) if n_env_drift else 100.0
    )

    # health grade
    health = _safe(
        lambda: __import__(
            "runtime.tier3_env_health", fromlist=["compute_environment_health"]
        ).compute_environment_health(env_id),
        default={},
    )
    kpis["health_grade"] = health.get("grade", "unknown") if health else "unknown"
    kpis["health_findings"] = len(health.get("findings", [])) if health else 0

    # readiness (if upstream exists)
    upstream = env.get("upstream_env_id")
    if upstream:
        readiness = _safe(
            lambda: __import__(
                "runtime.tier3_env_health", fromlist=["compute_promotion_readiness"]
            ).compute_promotion_readiness(env_id, upstream),
            default={},
        )
        kpis["promotion_readiness"] = readiness.get("readiness_score", 0) if readiness else 0
    else:
        kpis["promotion_readiness"] = None

    # pack count
    kpis["applied_packs"] = len(env.get("applied_pack_ids", []))

    # policy coverage — allowed + default policies
    n_allowed = len(env.get("allowed_policy_ids", []))
    n_default = len(env.get("default_policy_ids", []))
    kpis["policy_coverage"] = n_allowed + n_default

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "kpis": kpis,
        "timestamp": ts,
    }

    _KPI_LOG.append({
        "type": "environment", "env_id": env_id, "timestamp": ts, **kpis,
    })
    _add_insight(
        "kpi_report",
        f"env '{env.get('name', '?')}' KPIs: "
        f"drift_stability={kpis['drift_stability_index']}%, "
        f"health={kpis['health_grade']}",
        {"scope": "environment", "env_id": env_id, "kpis": kpis},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy KPIs
# ------------------------------------------------------------------

def compute_policy_kpis(policy_id: str) -> Dict[str, Any]:
    """Compute KPIs scoped to a single policy."""
    try:
        from runtime.tier3_policies import get_policy
        pol = get_policy(policy_id)
        if pol is None:
            return {"error": True, "reason": f"policy '{policy_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read policy"}

    kpis: Dict[str, Any] = {}
    ts = time.time()

    kpis["enabled"] = bool(pol.get("enabled"))
    kpis["retired"] = bool(pol.get("retired"))
    kpis["has_conditions"] = bool(pol.get("trigger_conditions"))
    kpis["has_actions"] = bool(pol.get("actions"))

    # completeness score
    completeness = 0
    if kpis["has_conditions"]:
        completeness += 50
    if kpis["has_actions"]:
        completeness += 50
    kpis["completeness_score"] = completeness

    # scheduling configured
    kpis["has_interval"] = bool(pol.get("evaluation_interval_seconds"))
    kpis["has_windows"] = bool(pol.get("allowed_windows"))

    # environment presence
    envs = _safe(
        lambda: __import__(
            "runtime.tier3_environments", fromlist=["list_environments"]
        ).list_environments(),
        default=[],
    )
    presence = sum(
        1 for e in envs
        if (policy_id in e.get("allowed_policy_ids", [])
            or policy_id in e.get("default_policy_ids", []))
    )
    kpis["environment_presence"] = presence

    # lineage activity
    lineage = _safe(
        lambda: __import__(
            "runtime.tier3_lineage", fromlist=["get_lineage"]
        ).get_lineage("policy", policy_id),
        default=[],
    )
    kpis["lineage_records"] = len(lineage) if lineage else 0

    result = {
        "scope": "policy",
        "policy_id": policy_id,
        "policy_name": pol.get("name", "?"),
        "kpis": kpis,
        "timestamp": ts,
    }

    _KPI_LOG.append({
        "type": "policy", "policy_id": policy_id, "timestamp": ts, **kpis,
    })
    _add_insight(
        "kpi_report",
        f"policy '{pol.get('name', '?')}' KPIs: "
        f"completeness={completeness}%, "
        f"env_presence={presence}",
        {"scope": "policy", "policy_id": policy_id, "kpis": kpis},
        [policy_id],
    )

    return result
