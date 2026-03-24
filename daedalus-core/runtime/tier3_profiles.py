# runtime/tier3_profiles.py
"""
Tier-3 governance profiles.

A profile bundles a set of policies, scheduling overrides, and
feature flags into a named mode.  Only one profile may be active
at a time.  Profiles constrain or further gate behavior but never
weaken existing safety checks.  All switching is operator-triggered.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_PROFILE_REGISTRY: List[Dict[str, Any]] = []

_ACTIVE_PROFILE_ID: Optional[str] = None

_PROFILE_ACTIVATION_LOG: List[Dict[str, Any]] = []

_DEFAULT_FEATURE_FLAGS: Dict[str, bool] = {
    "allow_plans": True,
    "allow_migrations": True,
    "allow_policy_generated_proposals": True,
}


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_profile(
    name: str,
    description: str,
    attached_policy_ids: Optional[List[str]] = None,
    scheduling_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    tier3_feature_flags: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    profile = {
        "profile_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "attached_policy_ids": attached_policy_ids or [],
        "scheduling_overrides": scheduling_overrides or {},
        "tier3_feature_flags": {**_DEFAULT_FEATURE_FLAGS, **(tier3_feature_flags or {})},
        "status": "inactive",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _TIER3_PROFILE_REGISTRY.append(profile)
    return profile


def list_profiles() -> List[Dict[str, Any]]:
    return list(_TIER3_PROFILE_REGISTRY)


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    for p in _TIER3_PROFILE_REGISTRY:
        if p["profile_id"] == profile_id:
            return p
    return None


def get_active_profile() -> Optional[Dict[str, Any]]:
    global _ACTIVE_PROFILE_ID
    if _ACTIVE_PROFILE_ID is None:
        return None
    return get_profile(_ACTIVE_PROFILE_ID)


def activate_profile(profile_id: str) -> Dict[str, Any]:
    global _ACTIVE_PROFILE_ID

    try:
        from runtime.tier3_env_guardrails import check_profile_activation
        gr = check_profile_activation(profile_id)
        if not gr.get("allowed"):
            reasons = gr.get("blocking_reasons", [])
            return {"activated": False,
                    "reason": "; ".join(reasons) if reasons
                    else "blocked by guardrail"}
    except Exception:
        pass

    try:
        from runtime.tier3_environments import is_profile_allowed
        if not is_profile_allowed(profile_id):
            return {"activated": False,
                    "reason": f"profile '{profile_id}' not allowed by active environment"}
    except Exception:
        pass

    profile = get_profile(profile_id)
    if profile is None:
        return {"activated": False, "reason": f"profile '{profile_id}' not found"}

    previous_id = _ACTIVE_PROFILE_ID

    if _ACTIVE_PROFILE_ID is not None and _ACTIVE_PROFILE_ID != profile_id:
        prev = get_profile(_ACTIVE_PROFILE_ID)
        if prev:
            prev["status"] = "inactive"
            prev["updated_at"] = time.time()

    _ACTIVE_PROFILE_ID = profile_id
    profile["status"] = "active"
    profile["updated_at"] = time.time()

    _PROFILE_ACTIVATION_LOG.append({
        "profile_id": profile_id,
        "previous_profile_id": previous_id,
        "action": "activate",
        "timestamp": time.time(),
    })

    return {"activated": True, "profile_id": profile_id,
            "previous_profile_id": previous_id}


def deactivate_profile() -> Dict[str, Any]:
    global _ACTIVE_PROFILE_ID

    if _ACTIVE_PROFILE_ID is None:
        return {"deactivated": False, "reason": "no active profile"}

    prev_id = _ACTIVE_PROFILE_ID
    prev = get_profile(prev_id)
    if prev:
        prev["status"] = "inactive"
        prev["updated_at"] = time.time()

    _ACTIVE_PROFILE_ID = None

    _PROFILE_ACTIVATION_LOG.append({
        "profile_id": prev_id,
        "previous_profile_id": None,
        "action": "deactivate",
        "timestamp": time.time(),
    })

    return {"deactivated": True, "profile_id": prev_id}


def get_activation_log(limit: int = 10) -> List[Dict[str, Any]]:
    return list(_PROFILE_ACTIVATION_LOG[-limit:])


def clear_tier3_profiles() -> None:
    """Reset registry and active state (for testing only)."""
    global _ACTIVE_PROFILE_ID
    _TIER3_PROFILE_REGISTRY.clear()
    _ACTIVE_PROFILE_ID = None
    _PROFILE_ACTIVATION_LOG.clear()


# ------------------------------------------------------------------
# Profile-aware query helpers (read-only)
# ------------------------------------------------------------------

def is_policy_in_scope(policy_id: str) -> bool:
    """Check if a policy is in the active profile's scope (or all if no profile)."""
    profile = get_active_profile()
    if profile is None:
        return True
    return policy_id in profile.get("attached_policy_ids", [])


def get_scheduling_override(policy_id: str) -> Optional[Dict[str, Any]]:
    """Return scheduling overrides from the active profile, or None."""
    profile = get_active_profile()
    if profile is None:
        return None
    return profile.get("scheduling_overrides", {}).get(policy_id)


def get_feature_flag(flag: str) -> bool:
    """Return the effective value of a feature flag.

    Precedence (highest wins): profile > environment > system default.
    """
    try:
        from runtime.tier3_environments import get_env_feature_flag
        env_val = get_env_feature_flag(flag)
    except Exception:
        env_val = None

    profile = get_active_profile()
    if profile is not None:
        profile_flags = profile.get("tier3_feature_flags", {})
        if flag in profile_flags:
            return profile_flags[flag]

    if env_val is not None:
        return env_val

    return _DEFAULT_FEATURE_FLAGS.get(flag, True)
