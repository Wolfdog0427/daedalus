# runtime/tier3_audit.py
"""
Governance-wide audit reports.

Generates read-only audit reports that aggregate lineage, drift,
health, readiness, and pack validation across the governance system.
All functions are side-effect-free — they never mutate state or
auto-correct anything.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_AUDIT_LOG: List[Dict[str, Any]] = []


def get_audit_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_AUDIT_LOG[-limit:])


def clear_audit_log() -> None:
    _AUDIT_LOG.clear()


# ------------------------------------------------------------------
# System-wide audit
# ------------------------------------------------------------------

def generate_governance_audit() -> Dict[str, Any]:
    """Generate a comprehensive audit of the entire governance system."""
    report: Dict[str, Any] = {"timestamp": time.time()}

    try:
        from runtime.tier3_environments import list_environments
        envs = list_environments()
        report["total_environments"] = len(envs)
    except Exception:
        envs = []
        report["total_environments"] = 0

    try:
        from runtime.tier3_profiles import list_profiles
        report["total_profiles"] = len(list_profiles())
    except Exception:
        report["total_profiles"] = 0

    try:
        from runtime.tier3_policies import get_policies
        policies = get_policies()
        report["total_policies"] = len(policies)
        report["enabled_policies"] = sum(
            1 for p in policies if p.get("enabled") and not p.get("retired"))
        report["retired_policies"] = sum(
            1 for p in policies if p.get("retired"))
    except Exception:
        report["total_policies"] = 0
        report["enabled_policies"] = 0
        report["retired_policies"] = 0

    try:
        from runtime.tier3_runbook_templates import list_templates
        report["total_templates"] = len(list_templates())
    except Exception:
        report["total_templates"] = 0

    try:
        from runtime.tier3_runbooks import list_runbooks
        runbooks = list_runbooks()
        report["total_runbooks"] = len(runbooks)
        report["runbook_statuses"] = {}
        for rb in runbooks:
            s = rb.get("status", "unknown")
            report["runbook_statuses"][s] = report["runbook_statuses"].get(s, 0) + 1
    except Exception:
        report["total_runbooks"] = 0
        report["runbook_statuses"] = {}

    try:
        from runtime.tier3_envpacks import list_envpacks
        report["total_packs"] = len(list_envpacks())
    except Exception:
        report["total_packs"] = 0

    try:
        from runtime.tier3_lineage import get_lineage_log
        report["total_lineage_records"] = len(get_lineage_log(10000))
    except Exception:
        report["total_lineage_records"] = 0

    try:
        from runtime.tier3_snapshots import list_snapshots
        report["total_snapshots"] = len(list_snapshots())
    except Exception:
        report["total_snapshots"] = 0

    env_health: List[Dict[str, Any]] = []
    try:
        from runtime.tier3_env_health import compute_environment_health
        for env in envs:
            h = compute_environment_health(env["env_id"])
            env_health.append({
                "env_id": env["env_id"],
                "env_name": env.get("name", "?"),
                "grade": h.get("grade", "unknown"),
                "findings": len(h.get("findings", [])),
            })
    except Exception:
        pass
    report["environment_health"] = env_health

    _AUDIT_LOG.append({
        "type": "system",
        "total_environments": report["total_environments"],
        "total_policies": report["total_policies"],
        "timestamp": report["timestamp"],
    })

    return report


# ------------------------------------------------------------------
# Per-entity audits
# ------------------------------------------------------------------

def generate_environment_audit(env_id: str) -> Dict[str, Any]:
    """Generate an audit report for a single environment."""
    report: Dict[str, Any] = {"env_id": env_id, "timestamp": time.time()}

    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
        report["env_name"] = env.get("name", "?")
        report["status"] = env.get("status", "?")
        report["allowed_profiles"] = len(env.get("allowed_profile_ids", []))
        report["allowed_policies"] = len(env.get("allowed_policy_ids", []))
        report["allowed_templates"] = len(
            env.get("allowed_runbook_template_ids", []))
        report["default_policies"] = len(env.get("default_policy_ids", []))
        report["applied_packs"] = len(env.get("applied_pack_ids", []))
        report["upstream_env_id"] = env.get("upstream_env_id")
        report["downstream_env_ids"] = env.get("downstream_env_ids", [])
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    try:
        from runtime.tier3_env_health import compute_environment_health
        h = compute_environment_health(env_id)
        report["health"] = {
            "grade": h.get("grade"),
            "findings": h.get("findings", []),
        }
    except Exception:
        report["health"] = {}

    try:
        from runtime.tier3_lineage import get_lineage_for_env
        report["lineage_records"] = len(get_lineage_for_env(env_id))
    except Exception:
        report["lineage_records"] = 0

    try:
        from runtime.tier3_envpacks import validate_envpack_against_environment
        pack_results = []
        for pack_id in env.get("applied_pack_ids", []):
            vr = validate_envpack_against_environment(pack_id, env_id)
            pack_results.append({
                "pack_id": pack_id,
                "valid": vr.get("valid"),
                "issues": len(vr.get("issues", [])),
            })
        report["pack_validation"] = pack_results
    except Exception:
        report["pack_validation"] = []

    _AUDIT_LOG.append({
        "type": "environment",
        "env_id": env_id,
        "grade": report.get("health", {}).get("grade"),
        "timestamp": report["timestamp"],
    })

    return report


def generate_policy_audit(policy_id: str) -> Dict[str, Any]:
    """Generate an audit report for a single policy."""
    report: Dict[str, Any] = {"policy_id": policy_id, "timestamp": time.time()}

    try:
        from runtime.tier3_policies import get_policy
        pol = get_policy(policy_id)
        if pol is None:
            return {"error": True, "reason": f"policy '{policy_id}' not found"}
        report["name"] = pol.get("name", "?")
        report["enabled"] = pol.get("enabled", False)
        report["retired"] = pol.get("retired", False)
        report["conditions"] = len(pol.get("trigger_conditions", []))
        report["actions"] = len(pol.get("actions", []))
        report["evaluation_interval"] = pol.get("evaluation_interval_seconds")
        report["last_evaluated_at"] = pol.get("last_evaluated_at")
    except Exception:
        return {"error": True, "reason": "failed to read policy"}

    try:
        from runtime.tier3_environments import list_environments
        in_envs = []
        for env in list_environments():
            if policy_id in env.get("allowed_policy_ids", []):
                in_envs.append(env["env_id"])
            elif policy_id in env.get("default_policy_ids", []):
                in_envs.append(env["env_id"])
        report["present_in_environments"] = in_envs
    except Exception:
        report["present_in_environments"] = []

    try:
        from runtime.tier3_lineage import get_lineage
        report["lineage_records"] = len(
            get_lineage(object_type="policy", object_id=policy_id))
    except Exception:
        report["lineage_records"] = 0

    _AUDIT_LOG.append({
        "type": "policy",
        "policy_id": policy_id,
        "enabled": report.get("enabled"),
        "timestamp": report["timestamp"],
    })

    return report


def generate_profile_audit(profile_id: str) -> Dict[str, Any]:
    """Generate an audit report for a single profile."""
    report: Dict[str, Any] = {
        "profile_id": profile_id, "timestamp": time.time()}

    try:
        from runtime.tier3_profiles import get_profile
        prof = get_profile(profile_id)
        if prof is None:
            return {"error": True, "reason": f"profile '{profile_id}' not found"}
        report["name"] = prof.get("name", "?")
        report["status"] = prof.get("status", "?")
        report["attached_policies"] = len(
            prof.get("attached_policy_ids", []))
        report["scheduling_overrides"] = len(
            prof.get("scheduling_overrides", {}))
        report["feature_flags"] = prof.get("tier3_feature_flags", {})
    except Exception:
        return {"error": True, "reason": "failed to read profile"}

    try:
        from runtime.tier3_environments import list_environments
        in_envs = []
        for env in list_environments():
            if profile_id in env.get("allowed_profile_ids", []):
                in_envs.append(env["env_id"])
        report["present_in_environments"] = in_envs
    except Exception:
        report["present_in_environments"] = []

    try:
        from runtime.tier3_lineage import get_lineage
        report["lineage_records"] = len(
            get_lineage(object_type="profile", object_id=profile_id))
    except Exception:
        report["lineage_records"] = 0

    _AUDIT_LOG.append({
        "type": "profile",
        "profile_id": profile_id,
        "status": report.get("status"),
        "timestamp": report["timestamp"],
    })

    return report


def generate_template_audit(template_id: str) -> Dict[str, Any]:
    """Generate an audit report for a single template."""
    report: Dict[str, Any] = {
        "template_id": template_id, "timestamp": time.time()}

    try:
        from runtime.tier3_runbook_templates import get_template
        tmpl = get_template(template_id)
        if tmpl is None:
            return {"error": True, "reason": f"template '{template_id}' not found"}
        report["name"] = tmpl.get("name", "?")
        report["parameters"] = len(
            tmpl.get("parameter_schema", {}).get("properties", {}))
        report["steps"] = len(tmpl.get("step_blueprints", []))
    except Exception:
        return {"error": True, "reason": "failed to read template"}

    try:
        from runtime.tier3_environments import list_environments
        in_envs = []
        for env in list_environments():
            if template_id in env.get("allowed_runbook_template_ids", []):
                in_envs.append(env["env_id"])
        report["present_in_environments"] = in_envs
    except Exception:
        report["present_in_environments"] = []

    try:
        from runtime.tier3_lineage import get_lineage
        report["lineage_records"] = len(
            get_lineage(object_type="template", object_id=template_id))
    except Exception:
        report["lineage_records"] = 0

    _AUDIT_LOG.append({
        "type": "template",
        "template_id": template_id,
        "timestamp": report["timestamp"],
    })

    return report
