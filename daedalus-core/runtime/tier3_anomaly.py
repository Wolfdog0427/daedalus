# runtime/tier3_anomaly.py
"""
Governance anomaly detection.

Identifies unexpected patterns in policies, environments, packs,
and lineage by scanning historical logs and current state.  All
functions are read-only and operator-triggered.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

_ANOMALY_REGISTRY: List[Dict[str, Any]] = []

_GOVERNANCE_INSIGHTS: List[Dict[str, Any]] = []


# ------------------------------------------------------------------
# Insight registry (append-only)
# ------------------------------------------------------------------

def _add_insight(
    insight_type: str,
    summary: str,
    details: Dict[str, Any],
    related_ids: List[str] | None = None,
) -> Dict[str, Any]:
    entry = {
        "insight_id": str(uuid.uuid4()),
        "insight_type": insight_type,
        "summary": summary,
        "details": details,
        "related_ids": related_ids or [],
        "timestamp": time.time(),
    }
    _GOVERNANCE_INSIGHTS.append(entry)
    return entry


def get_governance_insights(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_GOVERNANCE_INSIGHTS[-limit:])


def get_governance_insight(insight_id: str) -> Dict[str, Any] | None:
    for i in _GOVERNANCE_INSIGHTS:
        if i["insight_id"] == insight_id:
            return i
    return None


def clear_governance_insights() -> None:
    _GOVERNANCE_INSIGHTS.clear()


def get_anomaly_registry(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_ANOMALY_REGISTRY[-limit:])


def clear_anomaly_registry() -> None:
    _ANOMALY_REGISTRY.clear()


# ------------------------------------------------------------------
# Policy anomalies
# ------------------------------------------------------------------

def detect_policy_anomalies() -> List[Dict[str, Any]]:
    """Scan for unexpected patterns in policies."""
    anomalies: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_policies import get_policies, get_policy_eval_log
        policies = get_policies()
    except Exception:
        return anomalies

    for pol in policies:
        pid = pol.get("policy_id", "")

        if pol.get("enabled") and pol.get("retired"):
            a = {
                "anomaly_type": "policy_enabled_and_retired",
                "object_id": pid,
                "severity": "high",
                "detail": f"policy '{pol.get('name', '?')}' is both enabled and retired",
            }
            anomalies.append(a)

        if (pol.get("enabled") and not pol.get("retired")
                and not pol.get("trigger_conditions")):
            a = {
                "anomaly_type": "policy_no_conditions",
                "object_id": pid,
                "severity": "medium",
                "detail": f"policy '{pol.get('name', '?')}' is enabled but has no trigger conditions",
            }
            anomalies.append(a)

        if (pol.get("enabled") and not pol.get("retired")
                and not pol.get("actions")):
            a = {
                "anomaly_type": "policy_no_actions",
                "object_id": pid,
                "severity": "low",
                "detail": f"policy '{pol.get('name', '?')}' is enabled but has no actions",
            }
            anomalies.append(a)

    try:
        eval_log = get_policy_eval_log(20)
        if len(eval_log) >= 3:
            recent_triggered = sum(
                e.get("total_triggered", 0) for e in eval_log[-3:])
            if recent_triggered > 10:
                anomalies.append({
                    "anomaly_type": "policy_trigger_spike",
                    "object_id": "system",
                    "severity": "medium",
                    "detail": f"{recent_triggered} triggers in last 3 evaluations",
                })
    except Exception:
        pass

    for a in anomalies:
        a["timestamp"] = time.time()
        _ANOMALY_REGISTRY.append(a)
        _add_insight(
            "anomaly", a["detail"],
            {"anomaly_type": a["anomaly_type"], "severity": a["severity"]},
            [a["object_id"]],
        )

    return anomalies


# ------------------------------------------------------------------
# Environment anomalies
# ------------------------------------------------------------------

def detect_environment_anomalies() -> List[Dict[str, Any]]:
    """Scan for unexpected patterns in environments."""
    anomalies: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_environments import list_environments
        envs = list_environments()
    except Exception:
        return anomalies

    for env in envs:
        eid = env.get("env_id", "")
        name = env.get("name", "?")

        if (not env.get("allowed_profile_ids")
                and not env.get("allowed_policy_ids")):
            anomalies.append({
                "anomaly_type": "env_empty_allowlists",
                "object_id": eid,
                "severity": "medium",
                "detail": f"environment '{name}' has no allowed profiles or policies",
            })

        flags = env.get("default_feature_flags", {})
        all_false = flags and all(not v for v in flags.values())
        if all_false:
            anomalies.append({
                "anomaly_type": "env_all_flags_disabled",
                "object_id": eid,
                "severity": "high",
                "detail": f"environment '{name}' has all feature flags disabled",
            })

        packs = env.get("applied_pack_ids", [])
        defaults = env.get("default_policy_ids", [])
        if packs and not defaults:
            anomalies.append({
                "anomaly_type": "env_packs_no_defaults",
                "object_id": eid,
                "severity": "low",
                "detail": (
                    f"environment '{name}' has applied packs "
                    f"but no default_policy_ids"
                ),
            })

    try:
        from runtime.tier3_env_drift import get_drift_log
        drift_log = get_drift_log(20)
        drift_count = sum(1 for e in drift_log if e.get("has_drift"))
        if drift_count > len(drift_log) * 0.7 and len(drift_log) >= 3:
            anomalies.append({
                "anomaly_type": "persistent_drift",
                "object_id": "system",
                "severity": "high",
                "detail": f"{drift_count}/{len(drift_log)} recent drift checks positive",
            })
    except Exception:
        pass

    for a in anomalies:
        a["timestamp"] = time.time()
        _ANOMALY_REGISTRY.append(a)
        _add_insight(
            "anomaly", a["detail"],
            {"anomaly_type": a["anomaly_type"], "severity": a["severity"]},
            [a["object_id"]],
        )

    return anomalies


# ------------------------------------------------------------------
# Pack anomalies
# ------------------------------------------------------------------

def detect_pack_anomalies() -> List[Dict[str, Any]]:
    """Scan for unexpected patterns in governance packs."""
    anomalies: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_envpacks import list_envpacks
        packs = list_envpacks()
    except Exception:
        return anomalies

    for pack in packs:
        pid = pack.get("pack_id", "")
        name = pack.get("name", "?")

        if (not pack.get("policy_ids")
                and not pack.get("profile_ids")
                and not pack.get("feature_flag_overrides")):
            anomalies.append({
                "anomaly_type": "pack_empty",
                "object_id": pid,
                "severity": "low",
                "detail": f"pack '{name}' has no policies, profiles, or flags",
            })

        flags = pack.get("feature_flag_overrides", {})
        all_false = flags and all(not v for v in flags.values())
        if all_false and len(flags) >= 2:
            anomalies.append({
                "anomaly_type": "pack_all_flags_disabled",
                "object_id": pid,
                "severity": "medium",
                "detail": f"pack '{name}' disables all feature flags",
            })

    for a in anomalies:
        a["timestamp"] = time.time()
        _ANOMALY_REGISTRY.append(a)
        _add_insight(
            "anomaly", a["detail"],
            {"anomaly_type": a["anomaly_type"], "severity": a["severity"]},
            [a["object_id"]],
        )

    return anomalies


# ------------------------------------------------------------------
# Lineage anomalies
# ------------------------------------------------------------------

def detect_lineage_anomalies() -> List[Dict[str, Any]]:
    """Scan for unexpected patterns in lineage history."""
    anomalies: List[Dict[str, Any]] = []

    try:
        from runtime.tier3_lineage import get_lineage_log
        lineage = get_lineage_log(200)
    except Exception:
        return anomalies

    if not lineage:
        return anomalies

    object_counts: Dict[str, int] = {}
    for entry in lineage:
        oid = entry.get("object_id", "?")
        object_counts[oid] = object_counts.get(oid, 0) + 1

    for oid, count in object_counts.items():
        if count >= 5:
            anomalies.append({
                "anomaly_type": "lineage_excessive_promotions",
                "object_id": oid,
                "severity": "medium",
                "detail": (
                    f"object '{oid}' has been promoted {count} times "
                    f"— possible churn"
                ),
            })

    env_pairs: Dict[str, int] = {}
    for entry in lineage:
        pair = f"{entry.get('origin_env_id', '?')}->{entry.get('derived_env_id', '?')}"
        env_pairs[pair] = env_pairs.get(pair, 0) + 1

    for pair, count in env_pairs.items():
        if count >= 8:
            anomalies.append({
                "anomaly_type": "lineage_path_hotspot",
                "object_id": pair,
                "severity": "low",
                "detail": f"promotion path '{pair}' used {count} times",
            })

    for a in anomalies:
        a["timestamp"] = time.time()
        _ANOMALY_REGISTRY.append(a)
        _add_insight(
            "anomaly", a["detail"],
            {"anomaly_type": a["anomaly_type"], "severity": a["severity"]},
            [a["object_id"]],
        )

    return anomalies


# ------------------------------------------------------------------
# Combined detection
# ------------------------------------------------------------------

def detect_all_anomalies() -> Dict[str, Any]:
    """Run all anomaly detectors and return a combined report."""
    policy = detect_policy_anomalies()
    environment = detect_environment_anomalies()
    pack = detect_pack_anomalies()
    lineage = detect_lineage_anomalies()

    all_anomalies = policy + environment + pack + lineage

    return {
        "total": len(all_anomalies),
        "policy": len(policy),
        "environment": len(environment),
        "pack": len(pack),
        "lineage": len(lineage),
        "anomalies": all_anomalies,
        "timestamp": time.time(),
    }
