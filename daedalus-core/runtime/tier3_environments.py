# runtime/tier3_environments.py
"""
Tier-3 environment-aware governance packs.

An environment bundles allowed profiles, policies, and runbook
templates into a named scope (e.g. dev, staging, prod).  Only one
environment may be active at a time.  Environments further restrict
what is usable but never weaken existing governance checks.

All switching is operator-triggered.  No auto-execution, no
auto-activation of profiles or policies.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_ENV_REGISTRY: List[Dict[str, Any]] = []

_ACTIVE_ENV_ID: Optional[str] = None

_ENV_ACTIVATION_LOG: List[Dict[str, Any]] = []


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_environment(
    name: str,
    description: str,
    default_profile_id: Optional[str] = None,
    allowed_profile_ids: Optional[List[str]] = None,
    allowed_policy_ids: Optional[List[str]] = None,
    allowed_runbook_template_ids: Optional[List[str]] = None,
    default_policy_ids: Optional[List[str]] = None,
    default_scheduling_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    default_feature_flags: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    env = {
        "env_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "default_profile_id": default_profile_id,
        "allowed_profile_ids": allowed_profile_ids or [],
        "allowed_policy_ids": allowed_policy_ids or [],
        "allowed_runbook_template_ids": allowed_runbook_template_ids or [],
        "default_policy_ids": default_policy_ids or [],
        "default_scheduling_overrides": default_scheduling_overrides or {},
        "default_feature_flags": default_feature_flags or {},
        "applied_pack_ids": [],
        "upstream_env_id": None,
        "downstream_env_ids": [],
        "status": "inactive",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _TIER3_ENV_REGISTRY.append(env)
    return env


def list_environments() -> List[Dict[str, Any]]:
    return list(_TIER3_ENV_REGISTRY)


def get_environment(env_id: str) -> Optional[Dict[str, Any]]:
    for e in _TIER3_ENV_REGISTRY:
        if e["env_id"] == env_id:
            return e
    return None


def get_active_environment() -> Optional[Dict[str, Any]]:
    global _ACTIVE_ENV_ID
    if _ACTIVE_ENV_ID is None:
        return None
    return get_environment(_ACTIVE_ENV_ID)


def activate_environment(env_id: str) -> Dict[str, Any]:
    global _ACTIVE_ENV_ID

    env = get_environment(env_id)
    if env is None:
        return {"activated": False, "reason": f"environment '{env_id}' not found"}

    previous_id = _ACTIVE_ENV_ID

    if _ACTIVE_ENV_ID is not None and _ACTIVE_ENV_ID != env_id:
        prev = get_environment(_ACTIVE_ENV_ID)
        if prev:
            prev["status"] = "inactive"
            prev["updated_at"] = time.time()

    _ACTIVE_ENV_ID = env_id
    env["status"] = "active"
    env["updated_at"] = time.time()

    _ENV_ACTIVATION_LOG.append({
        "env_id": env_id,
        "previous_env_id": previous_id,
        "action": "activate",
        "timestamp": time.time(),
    })

    return {"activated": True, "env_id": env_id,
            "previous_env_id": previous_id,
            "default_profile_id": env.get("default_profile_id")}


def deactivate_environment() -> Dict[str, Any]:
    global _ACTIVE_ENV_ID

    if _ACTIVE_ENV_ID is None:
        return {"deactivated": False, "reason": "no active environment"}

    prev_id = _ACTIVE_ENV_ID
    prev = get_environment(prev_id)
    if prev:
        prev["status"] = "inactive"
        prev["updated_at"] = time.time()

    _ACTIVE_ENV_ID = None

    _ENV_ACTIVATION_LOG.append({
        "env_id": prev_id,
        "previous_env_id": None,
        "action": "deactivate",
        "timestamp": time.time(),
    })

    return {"deactivated": True, "env_id": prev_id}


def get_env_activation_log(limit: int = 10) -> List[Dict[str, Any]]:
    return list(_ENV_ACTIVATION_LOG[-limit:])


def clear_tier3_environments() -> None:
    """Reset registry and active state (for testing only)."""
    global _ACTIVE_ENV_ID
    _TIER3_ENV_REGISTRY.clear()
    _ACTIVE_ENV_ID = None
    _ENV_ACTIVATION_LOG.clear()


# ------------------------------------------------------------------
# Environment-aware query helpers (read-only)
# ------------------------------------------------------------------

def is_profile_allowed(profile_id: str) -> bool:
    """Check whether a profile is allowed by the active environment."""
    env = get_active_environment()
    if env is None:
        return True
    return profile_id in env.get("allowed_profile_ids", [])


def is_policy_allowed(policy_id: str) -> bool:
    """Check whether a policy is allowed by the active environment."""
    env = get_active_environment()
    if env is None:
        return True
    return policy_id in env.get("allowed_policy_ids", [])


def is_template_allowed(template_id: str) -> bool:
    """Check whether a runbook template is allowed by the active environment."""
    env = get_active_environment()
    if env is None:
        return True
    return template_id in env.get("allowed_runbook_template_ids", [])


def is_policy_default(policy_id: str) -> bool:
    """Check whether a policy is in the active environment's default list."""
    env = get_active_environment()
    if env is None:
        return False
    return policy_id in env.get("default_policy_ids", [])


def get_env_scheduling_override(policy_id: str) -> Optional[Dict[str, Any]]:
    """Return scheduling overrides from the active environment, or None."""
    env = get_active_environment()
    if env is None:
        return None
    return env.get("default_scheduling_overrides", {}).get(policy_id)


def get_env_feature_flag(flag: str) -> Optional[bool]:
    """Return a feature flag override from the active environment, or None."""
    env = get_active_environment()
    if env is None:
        return None
    return env.get("default_feature_flags", {}).get(flag)


def get_env_defaults() -> Dict[str, Any]:
    """Return merged defaults from the active environment (read-only)."""
    env = get_active_environment()
    if env is None:
        return {}
    return {
        "default_profile_id": env.get("default_profile_id"),
        "default_policy_ids": env.get("default_policy_ids", []),
        "default_scheduling_overrides": env.get("default_scheduling_overrides", {}),
        "default_feature_flags": env.get("default_feature_flags", {}),
        "applied_pack_ids": env.get("applied_pack_ids", []),
    }


# ------------------------------------------------------------------
# Effective-state helpers (read-only, side-effect-free)
# ------------------------------------------------------------------

def get_effective_policies(env_id: str) -> Dict[str, Any]:
    """Return the union of allowed + default policy IDs for an environment."""
    env = get_environment(env_id)
    if env is None:
        return {"error": True, "reason": f"environment '{env_id}' not found"}
    allowed = set(env.get("allowed_policy_ids", []))
    defaults = set(env.get("default_policy_ids", []))
    combined = sorted(allowed | defaults)
    return {
        "env_id": env_id,
        "allowed_policy_ids": sorted(allowed),
        "default_policy_ids": sorted(defaults),
        "effective_policy_ids": combined,
    }


def get_effective_profiles(env_id: str) -> Dict[str, Any]:
    """Return allowed profile IDs and the default profile for an environment."""
    env = get_environment(env_id)
    if env is None:
        return {"error": True, "reason": f"environment '{env_id}' not found"}
    allowed = sorted(env.get("allowed_profile_ids", []))
    return {
        "env_id": env_id,
        "allowed_profile_ids": allowed,
        "default_profile_id": env.get("default_profile_id"),
    }


def get_effective_templates(env_id: str) -> Dict[str, Any]:
    """Return allowed runbook template IDs for an environment."""
    env = get_environment(env_id)
    if env is None:
        return {"error": True, "reason": f"environment '{env_id}' not found"}
    allowed = sorted(env.get("allowed_runbook_template_ids", []))
    return {
        "env_id": env_id,
        "allowed_runbook_template_ids": allowed,
    }


def get_effective_feature_flags(env_id: str) -> Dict[str, Any]:
    """Return the merged feature flags from the environment and its packs."""
    env = get_environment(env_id)
    if env is None:
        return {"error": True, "reason": f"environment '{env_id}' not found"}
    return {
        "env_id": env_id,
        "default_feature_flags": dict(env.get("default_feature_flags", {})),
        "applied_pack_ids": list(env.get("applied_pack_ids", [])),
    }


# ------------------------------------------------------------------
# Environment relations
# ------------------------------------------------------------------

def set_environment_relations(
    env_id: str,
    upstream_env_id: Optional[str] = None,
    downstream_env_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    env = get_environment(env_id)
    if env is None:
        return {"updated": False, "reason": f"environment '{env_id}' not found"}

    if upstream_env_id is not None:
        if get_environment(upstream_env_id) is None:
            return {"updated": False,
                    "reason": f"upstream environment '{upstream_env_id}' not found"}
        if upstream_env_id == env_id:
            return {"updated": False, "reason": "environment cannot be its own upstream"}

    if downstream_env_ids is not None:
        for did in downstream_env_ids:
            if get_environment(did) is None:
                return {"updated": False,
                        "reason": f"downstream environment '{did}' not found"}
            if did == env_id:
                return {"updated": False,
                        "reason": "environment cannot be its own downstream"}

    env["upstream_env_id"] = upstream_env_id
    env["downstream_env_ids"] = downstream_env_ids or []
    env["updated_at"] = time.time()

    return {"updated": True, "env_id": env_id,
            "upstream_env_id": upstream_env_id,
            "downstream_env_ids": env["downstream_env_ids"]}


def get_promotion_path(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    """
    Compute the ordered sequence of environment IDs from source to target
    following downstream links.  Returns an error if no path exists.
    """
    source = get_environment(source_env_id)
    if source is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    target = get_environment(target_env_id)
    if target is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}
    if source_env_id == target_env_id:
        return {"error": True, "reason": "source and target are the same environment"}

    visited: set = set()
    path: List[str] = [source_env_id]
    current = source_env_id

    while current != target_env_id:
        if current in visited:
            return {"error": True, "reason": "cycle detected in environment relations"}
        visited.add(current)

        env = get_environment(current)
        if env is None:
            break
        downstream = env.get("downstream_env_ids") or []
        if target_env_id in downstream:
            path.append(target_env_id)
            break

        found_next = False
        for did in downstream:
            if did not in visited:
                path.append(did)
                current = did
                found_next = True
                break

        if not found_next:
            return {"error": True,
                    "reason": f"no promotion path from '{source_env_id}' to '{target_env_id}'"}

    if path[-1] != target_env_id:
        return {"error": True,
                "reason": f"no promotion path from '{source_env_id}' to '{target_env_id}'"}

    return {"path": path}
