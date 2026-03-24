# runtime/tier3_strategy.py
"""
Strategic governance modeling and optimization suggestions.

Produces read-only, long-horizon projections of governance trajectory,
per-environment evolution, and per-policy lifecycles.  Also generates
descriptive optimization suggestions that reference existing governed
operations but never create artifacts or mutate state.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_STRATEGY_LOG: List[Dict[str, Any]] = []


def get_strategy_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_STRATEGY_LOG[-limit:])


def clear_strategy_log() -> None:
    _STRATEGY_LOG.clear()


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


# ------------------------------------------------------------------
# Governance trajectory
# ------------------------------------------------------------------

def model_governance_trajectory(horizon: int = 10) -> Dict[str, Any]:
    """Model the overall governance system trajectory."""
    factors: List[str] = []
    projections: List[Dict[str, str]] = []

    n_envs = 0
    n_pols = 0
    n_retired = 0
    n_anomalies = 0
    n_lineage = 0

    try:
        from runtime.tier3_environments import list_environments
        n_envs = len(list_environments())
    except Exception:
        pass

    try:
        from runtime.tier3_policies import get_policies
        pols = get_policies()
        n_pols = len(pols)
        n_retired = sum(1 for p in pols if p.get("retired"))
        if n_retired > n_pols * 0.5 and n_pols > 0:
            projections.append({
                "projection": "high_policy_retirement_rate",
                "detail": f"{n_retired}/{n_pols} policies retired",
            })
            factors.append("over half of policies are retired")
    except Exception:
        pass

    try:
        from runtime.tier3_anomaly import get_anomaly_registry
        n_anomalies = len(get_anomaly_registry(200))
        if n_anomalies > 10:
            projections.append({
                "projection": "anomaly_accumulation",
                "detail": f"{n_anomalies} anomalies detected",
            })
            factors.append("anomaly count is high")
    except Exception:
        pass

    try:
        from runtime.tier3_lineage import get_lineage_log
        n_lineage = len(get_lineage_log(1000))
        if n_lineage > 20:
            factors.append(f"active lineage ({n_lineage} records)")
    except Exception:
        pass

    try:
        from runtime.tier3_forecast import get_forecast_log
        forecasts = get_forecast_log(50)
        declining = sum(
            1 for f in forecasts
            if "declining" in f.get("prediction", "") or "increase" in f.get("prediction", "")
        )
        if declining > len(forecasts) * 0.5 and forecasts:
            projections.append({
                "projection": "negative_forecast_trend",
                "detail": f"{declining}/{len(forecasts)} forecasts negative",
            })
            factors.append("majority of forecasts show negative trends")
    except Exception:
        pass

    if not projections:
        projections.append({
            "projection": "governance_stable",
            "detail": "no significant strategic concerns",
        })

    n_samples = n_envs + n_pols + n_anomalies + n_lineage
    confidence = "high" if n_samples >= 20 else "medium" if n_samples >= 5 else "low"

    if not factors:
        factors.append("no significant signals")

    result = {
        "horizon": horizon,
        "projections": projections,
        "confidence": confidence,
        "factors": factors,
        "stats": {
            "environments": n_envs,
            "policies": n_pols,
            "retired_policies": n_retired,
            "anomalies": n_anomalies,
            "lineage_records": n_lineage,
        },
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "governance_trajectory",
        "n_projections": len(projections),
        "confidence": confidence,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "strategy_model",
        f"governance trajectory: {len(projections)} projection(s), confidence={confidence}",
        {"projections": [p["projection"] for p in projections]},
    )

    return result


# ------------------------------------------------------------------
# Environment evolution
# ------------------------------------------------------------------

def model_environment_evolution(
    env_id: str,
    horizon: int = 10,
) -> Dict[str, Any]:
    """Model a single environment's future evolution."""
    factors: List[str] = []
    projections: List[Dict[str, str]] = []

    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    try:
        from runtime.tier3_forecast import forecast_environment_drift
        drift_fc = forecast_environment_drift(env_id, horizon)
        if drift_fc.get("prediction") == "drift_likely_to_increase":
            projections.append({
                "projection": "drift_increasing",
                "detail": "drift forecast predicts increase",
            })
            factors.extend(drift_fc.get("factors", []))
    except Exception:
        pass

    try:
        from runtime.tier3_env_health import compute_environment_health
        health = compute_environment_health(env_id)
        grade = health.get("grade", "unknown")
        n_findings = len(health.get("findings", []))
        if grade == "needs_attention":
            projections.append({
                "projection": "health_degrading",
                "detail": f"current grade: {grade}, {n_findings} findings",
            })
            factors.append(f"health grade: {grade}")
    except Exception:
        pass

    n_packs = len(env.get("applied_pack_ids", []))
    if n_packs == 0:
        projections.append({
            "projection": "no_packs_applied",
            "detail": "environment has no governance packs",
        })
        factors.append("no packs applied")

    if not projections:
        projections.append({
            "projection": "environment_stable",
            "detail": "no significant evolution signals",
        })

    if not factors:
        factors.append("no significant signals")

    n_samples = n_packs + len(env.get("allowed_policy_ids", []))
    confidence = "high" if n_samples >= 10 else "medium" if n_samples >= 3 else "low"

    result = {
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "horizon": horizon,
        "projections": projections,
        "confidence": confidence,
        "factors": factors,
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "environment_evolution",
        "env_id": env_id,
        "n_projections": len(projections),
        "confidence": confidence,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "strategy_model",
        f"env '{env.get('name', '?')}' evolution: {len(projections)} projection(s)",
        {"env_id": env_id, "projections": [p["projection"] for p in projections]},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Policy lifecycle
# ------------------------------------------------------------------

def model_policy_lifecycle(
    policy_id: str,
    horizon: int = 10,
) -> Dict[str, Any]:
    """Model a single policy's future lifecycle."""
    factors: List[str] = []
    projections: List[Dict[str, str]] = []

    try:
        from runtime.tier3_policies import get_policy
        pol = get_policy(policy_id)
        if pol is None:
            return {"error": True, "reason": f"policy '{policy_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read policy"}

    if pol.get("retired"):
        projections.append({
            "projection": "already_retired",
            "detail": "policy is retired — no further lifecycle expected",
        })
    else:
        try:
            from runtime.tier3_forecast import forecast_policy_activity
            pa = forecast_policy_activity(policy_id, horizon)
            if pa.get("prediction") == "activity_increasing":
                projections.append({
                    "projection": "activity_rising",
                    "detail": "trigger frequency increasing",
                })
                factors.extend(pa.get("factors", []))
            elif pa.get("prediction") == "activity_decreasing":
                projections.append({
                    "projection": "may_become_stale",
                    "detail": "trigger frequency declining — consider review",
                })
                factors.extend(pa.get("factors", []))
        except Exception:
            pass

        if not pol.get("trigger_conditions"):
            projections.append({
                "projection": "no_conditions",
                "detail": "policy has no trigger conditions",
            })
            factors.append("missing trigger conditions")

        if not pol.get("actions"):
            projections.append({
                "projection": "no_actions",
                "detail": "policy has no actions defined",
            })
            factors.append("missing actions")

    if not projections:
        projections.append({
            "projection": "policy_stable",
            "detail": "no significant lifecycle signals",
        })

    if not factors:
        factors.append("no significant signals")

    confidence = "high" if pol.get("last_evaluated_at") else "low"

    result = {
        "policy_id": policy_id,
        "policy_name": pol.get("name", "?"),
        "horizon": horizon,
        "projections": projections,
        "confidence": confidence,
        "factors": factors,
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "policy_lifecycle",
        "policy_id": policy_id,
        "n_projections": len(projections),
        "confidence": confidence,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "strategy_model",
        f"policy '{pol.get('name', '?')}' lifecycle: {len(projections)} projection(s)",
        {"policy_id": policy_id,
         "projections": [p["projection"] for p in projections]},
        [policy_id],
    )

    return result


# ------------------------------------------------------------------
# Optimization suggestions
# ------------------------------------------------------------------

def suggest_governance_optimizations() -> Dict[str, Any]:
    """Generate system-wide optimization suggestions (descriptive only)."""
    suggestions: List[Dict[str, str]] = []

    try:
        from runtime.tier3_policies import get_policies
        pols = get_policies()
        retired = [p for p in pols if p.get("retired")]
        enabled_no_cond = [
            p for p in pols
            if p.get("enabled") and not p.get("retired")
            and not p.get("trigger_conditions")
        ]
        if len(retired) > len(pols) * 0.4 and pols:
            suggestions.append({
                "category": "policy_cleanup",
                "suggestion": f"consider archiving {len(retired)} retired policies",
            })
        for p in enabled_no_cond:
            suggestions.append({
                "category": "policy_review",
                "suggestion": (
                    f"policy '{p.get('name', '?')}' is enabled without "
                    f"conditions — consider disabling or adding conditions"
                ),
            })
    except Exception:
        pass

    try:
        from runtime.tier3_environments import list_environments
        envs = list_environments()
        for env in envs:
            if not env.get("default_profile_id"):
                suggestions.append({
                    "category": "environment_defaults",
                    "suggestion": (
                        f"environment '{env.get('name', '?')}' has no "
                        f"default profile — consider setting one"
                    ),
                })
            if not env.get("applied_pack_ids"):
                suggestions.append({
                    "category": "environment_packs",
                    "suggestion": (
                        f"environment '{env.get('name', '?')}' has no "
                        f"governance packs — consider applying one"
                    ),
                })
    except Exception:
        pass

    try:
        from runtime.tier3_envpacks import list_envpacks
        packs = list_envpacks()
        for pack in packs:
            if (not pack.get("policy_ids") and not pack.get("profile_ids")
                    and not pack.get("feature_flag_overrides")):
                suggestions.append({
                    "category": "pack_cleanup",
                    "suggestion": f"pack '{pack.get('name', '?')}' is empty — consider removing",
                })
    except Exception:
        pass

    result = {
        "total": len(suggestions),
        "suggestions": suggestions,
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "governance_optimizations",
        "n_suggestions": len(suggestions),
        "timestamp": result["timestamp"],
    })
    for s in suggestions:
        _add_insight(
            "optimization_suggestion", s["suggestion"],
            {"category": s["category"]},
        )

    return result


def suggest_environment_optimizations(env_id: str) -> Dict[str, Any]:
    """Generate optimization suggestions for a single environment."""
    suggestions: List[Dict[str, str]] = []

    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    if not env.get("default_profile_id"):
        suggestions.append({
            "category": "defaults",
            "suggestion": "set a default_profile_id for this environment",
        })
    if not env.get("default_policy_ids"):
        suggestions.append({
            "category": "defaults",
            "suggestion": "add default_policy_ids for baseline governance",
        })
    if not env.get("applied_pack_ids"):
        suggestions.append({
            "category": "packs",
            "suggestion": "apply a governance pack to centralise configuration",
        })

    allowed_pol = set(env.get("allowed_policy_ids", []))
    default_pol = set(env.get("default_policy_ids", []))
    unused = allowed_pol - default_pol
    if len(unused) > 3:
        suggestions.append({
            "category": "cleanup",
            "suggestion": (
                f"{len(unused)} allowed policies are not in defaults — "
                f"consider removing or promoting them"
            ),
        })

    try:
        from runtime.tier3_env_health import compute_environment_health
        health = compute_environment_health(env_id)
        if health.get("grade") == "needs_attention":
            suggestions.append({
                "category": "health",
                "suggestion": "address health findings before promotion",
            })
    except Exception:
        pass

    result = {
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "total": len(suggestions),
        "suggestions": suggestions,
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "environment_optimizations",
        "env_id": env_id,
        "n_suggestions": len(suggestions),
        "timestamp": result["timestamp"],
    })
    for s in suggestions:
        _add_insight(
            "optimization_suggestion", s["suggestion"],
            {"category": s["category"], "env_id": env_id},
            [env_id],
        )

    return result


def suggest_policy_optimizations(policy_id: str) -> Dict[str, Any]:
    """Generate optimization suggestions for a single policy."""
    suggestions: List[Dict[str, str]] = []

    try:
        from runtime.tier3_policies import get_policy
        pol = get_policy(policy_id)
        if pol is None:
            return {"error": True, "reason": f"policy '{policy_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read policy"}

    if pol.get("retired"):
        suggestions.append({
            "category": "lifecycle",
            "suggestion": "policy is retired — consider archiving or removing references",
        })
    if pol.get("enabled") and not pol.get("trigger_conditions"):
        suggestions.append({
            "category": "completeness",
            "suggestion": "add trigger conditions or disable the policy",
        })
    if pol.get("enabled") and not pol.get("actions"):
        suggestions.append({
            "category": "completeness",
            "suggestion": "add actions or disable the policy",
        })
    if not pol.get("evaluation_interval_seconds"):
        suggestions.append({
            "category": "scheduling",
            "suggestion": "consider setting an evaluation interval",
        })

    result = {
        "policy_id": policy_id,
        "policy_name": pol.get("name", "?"),
        "total": len(suggestions),
        "suggestions": suggestions,
        "timestamp": time.time(),
    }

    _STRATEGY_LOG.append({
        "type": "policy_optimizations",
        "policy_id": policy_id,
        "n_suggestions": len(suggestions),
        "timestamp": result["timestamp"],
    })
    for s in suggestions:
        _add_insight(
            "optimization_suggestion", s["suggestion"],
            {"category": s["category"], "policy_id": policy_id},
            [policy_id],
        )

    return result
