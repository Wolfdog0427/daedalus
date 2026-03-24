# runtime/tier3_envpacks.py
"""
Tier-3 environment governance packs.

A governance pack is a reusable, read-only bundle of policy IDs,
scheduling overrides, and feature-flag overrides that can be applied
to an environment's defaults.  Applying a pack merges its contents
into the environment but never auto-enables policies, auto-activates
profiles, or auto-executes anything.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_ENVPACK_REGISTRY: List[Dict[str, Any]] = []

_PACK_APPLICATION_LOG: List[Dict[str, Any]] = []


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_envpack(
    name: str,
    description: str,
    profile_ids: Optional[List[str]] = None,
    policy_ids: Optional[List[str]] = None,
    scheduling_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    feature_flag_overrides: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    pack = {
        "pack_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "profile_ids": profile_ids or [],
        "policy_ids": policy_ids or [],
        "scheduling_overrides": scheduling_overrides or {},
        "feature_flag_overrides": feature_flag_overrides or {},
        "created_at": time.time(),
    }
    _ENVPACK_REGISTRY.append(pack)
    return pack


def list_envpacks() -> List[Dict[str, Any]]:
    return list(_ENVPACK_REGISTRY)


def get_envpack(pack_id: str) -> Optional[Dict[str, Any]]:
    for p in _ENVPACK_REGISTRY:
        if p["pack_id"] == pack_id:
            return p
    return None


def get_pack_application_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_PACK_APPLICATION_LOG[-limit:])


def clear_tier3_envpacks() -> None:
    """Reset registry and log (for testing only)."""
    _ENVPACK_REGISTRY.clear()
    _PACK_APPLICATION_LOG.clear()


# ------------------------------------------------------------------
# Application
# ------------------------------------------------------------------

def apply_pack_to_environment(env_id: str, pack_id: str) -> Dict[str, Any]:
    """
    Merge a governance pack's contents into an environment's defaults.

    Merges policy_ids, scheduling_overrides, and feature_flag_overrides
    into the environment.  Profile IDs from the pack are added to the
    environment's allowed_profile_ids.  Nothing is auto-enabled or
    auto-executed.
    """
    from runtime.tier3_environments import get_environment

    env = get_environment(env_id)
    if env is None:
        return {"applied": False, "reason": f"environment '{env_id}' not found"}

    pack = get_envpack(pack_id)
    if pack is None:
        return {"applied": False, "reason": f"pack '{pack_id}' not found"}

    existing_pol = set(env.get("default_policy_ids", []))
    for pid in pack.get("policy_ids", []):
        existing_pol.add(pid)
    env["default_policy_ids"] = sorted(existing_pol)

    existing_prof = set(env.get("allowed_profile_ids", []))
    for pid in pack.get("profile_ids", []):
        existing_prof.add(pid)
    env["allowed_profile_ids"] = sorted(existing_prof)

    existing_sched = env.get("default_scheduling_overrides", {})
    for pol_id, overrides in pack.get("scheduling_overrides", {}).items():
        if pol_id not in existing_sched:
            existing_sched[pol_id] = {}
        existing_sched[pol_id].update(overrides)
    env["default_scheduling_overrides"] = existing_sched

    existing_flags = env.get("default_feature_flags", {})
    existing_flags.update(pack.get("feature_flag_overrides", {}))
    env["default_feature_flags"] = existing_flags

    applied = env.get("applied_pack_ids", [])
    if pack_id not in applied:
        applied.append(pack_id)
    env["applied_pack_ids"] = applied

    env["updated_at"] = time.time()

    entry = {
        "env_id": env_id,
        "pack_id": pack_id,
        "pack_name": pack["name"],
        "timestamp": time.time(),
    }
    _PACK_APPLICATION_LOG.append(entry)

    return {"applied": True, "env_id": env_id, "pack_id": pack_id}


# ------------------------------------------------------------------
# Validation (read-only)
# ------------------------------------------------------------------

_VALID_FEATURE_FLAG_KEYS = {
    "allow_plans", "allow_migrations", "allow_policy_generated_proposals",
}

_VALID_SCHEDULING_KEYS = {
    "evaluation_interval_seconds", "allowed_windows", "rate_limit",
}


def validate_envpack_against_environment(
    pack_id: str,
    env_id: str,
) -> Dict[str, Any]:
    """
    Validate a governance pack against an environment's allowlists.

    Checks that referenced policies, profiles, and templates exist and
    are allowed, that scheduling overrides use valid keys, and that
    feature-flag overrides use known flag names.  Purely read-only.
    """
    from runtime.tier3_environments import get_environment

    pack = get_envpack(pack_id)
    if pack is None:
        return {"valid": False, "reason": f"pack '{pack_id}' not found", "issues": []}

    env = get_environment(env_id)
    if env is None:
        return {"valid": False, "reason": f"environment '{env_id}' not found", "issues": []}

    issues: List[Dict[str, str]] = []

    allowed_policies = set(env.get("allowed_policy_ids", []))
    default_policies = set(env.get("default_policy_ids", []))
    for pid in pack.get("policy_ids", []):
        if pid not in allowed_policies and pid not in default_policies:
            issues.append({
                "scope": "policy",
                "id": pid,
                "issue": "not in environment allowed or default policies",
            })

    allowed_profiles = set(env.get("allowed_profile_ids", []))
    for pid in pack.get("profile_ids", []):
        if pid not in allowed_profiles:
            issues.append({
                "scope": "profile",
                "id": pid,
                "issue": "not in environment allowed profiles",
            })

    allowed_templates = set(env.get("allowed_runbook_template_ids", []))
    for tid in pack.get("template_ids", []):
        if tid not in allowed_templates:
            issues.append({
                "scope": "template",
                "id": tid,
                "issue": "not in environment allowed templates",
            })

    for pol_id, overrides in pack.get("scheduling_overrides", {}).items():
        for key in overrides:
            if key not in _VALID_SCHEDULING_KEYS:
                issues.append({
                    "scope": "scheduling",
                    "id": pol_id,
                    "issue": f"unknown scheduling key '{key}'",
                })

    for key in pack.get("feature_flag_overrides", {}):
        if key not in _VALID_FEATURE_FLAG_KEYS:
            issues.append({
                "scope": "feature_flag",
                "id": key,
                "issue": f"unknown feature flag '{key}'",
            })

    return {
        "valid": len(issues) == 0,
        "pack_id": pack_id,
        "env_id": env_id,
        "issues": issues,
    }
