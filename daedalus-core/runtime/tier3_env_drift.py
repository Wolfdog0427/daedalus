# runtime/tier3_env_drift.py
"""
Read-only drift detection between Tier-3 environments.

Compares effective policies, profiles, templates, and feature flags
across two environments and reports differences.  All functions are
side-effect-free — they never mutate state, auto-promote, or
auto-correct anything.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_DRIFT_LOG: List[Dict[str, Any]] = []


def get_drift_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_DRIFT_LOG[-limit:])


def clear_drift_log() -> None:
    _DRIFT_LOG.clear()


# ------------------------------------------------------------------
# Individual drift detectors
# ------------------------------------------------------------------

def detect_policy_drift(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    from runtime.tier3_environments import get_effective_policies
    a = get_effective_policies(env_a_id)
    if a.get("error"):
        return a
    b = get_effective_policies(env_b_id)
    if b.get("error"):
        return b

    set_a = set(a["effective_policy_ids"])
    set_b = set(b["effective_policy_ids"])

    return {
        "scope": "policies",
        "env_a": env_a_id,
        "env_b": env_b_id,
        "only_in_a": sorted(set_a - set_b),
        "only_in_b": sorted(set_b - set_a),
        "shared": sorted(set_a & set_b),
        "a_default_ids": a["default_policy_ids"],
        "b_default_ids": b["default_policy_ids"],
    }


def detect_profile_drift(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    from runtime.tier3_environments import get_effective_profiles
    a = get_effective_profiles(env_a_id)
    if a.get("error"):
        return a
    b = get_effective_profiles(env_b_id)
    if b.get("error"):
        return b

    set_a = set(a["allowed_profile_ids"])
    set_b = set(b["allowed_profile_ids"])

    return {
        "scope": "profiles",
        "env_a": env_a_id,
        "env_b": env_b_id,
        "only_in_a": sorted(set_a - set_b),
        "only_in_b": sorted(set_b - set_a),
        "shared": sorted(set_a & set_b),
        "default_profile_a": a.get("default_profile_id"),
        "default_profile_b": b.get("default_profile_id"),
    }


def detect_template_drift(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    from runtime.tier3_environments import get_effective_templates
    a = get_effective_templates(env_a_id)
    if a.get("error"):
        return a
    b = get_effective_templates(env_b_id)
    if b.get("error"):
        return b

    set_a = set(a["allowed_runbook_template_ids"])
    set_b = set(b["allowed_runbook_template_ids"])

    return {
        "scope": "templates",
        "env_a": env_a_id,
        "env_b": env_b_id,
        "only_in_a": sorted(set_a - set_b),
        "only_in_b": sorted(set_b - set_a),
        "shared": sorted(set_a & set_b),
    }


def detect_feature_flag_drift(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    from runtime.tier3_environments import get_effective_feature_flags
    a = get_effective_feature_flags(env_a_id)
    if a.get("error"):
        return a
    b = get_effective_feature_flags(env_b_id)
    if b.get("error"):
        return b

    flags_a = a.get("default_feature_flags", {})
    flags_b = b.get("default_feature_flags", {})

    all_keys = sorted(set(flags_a) | set(flags_b))
    only_a = {k: flags_a[k] for k in all_keys if k in flags_a and k not in flags_b}
    only_b = {k: flags_b[k] for k in all_keys if k in flags_b and k not in flags_a}
    different = {}
    shared = {}
    for k in all_keys:
        if k in flags_a and k in flags_b:
            if flags_a[k] != flags_b[k]:
                different[k] = {"a": flags_a[k], "b": flags_b[k]}
            else:
                shared[k] = flags_a[k]

    return {
        "scope": "feature_flags",
        "env_a": env_a_id,
        "env_b": env_b_id,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "different": different,
        "shared": shared,
        "packs_a": a.get("applied_pack_ids", []),
        "packs_b": b.get("applied_pack_ids", []),
    }


# ------------------------------------------------------------------
# Full drift report
# ------------------------------------------------------------------

def detect_full_env_drift(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    """Run all drift detectors and combine into a single report."""
    report = {
        "env_a": env_a_id,
        "env_b": env_b_id,
        "timestamp": time.time(),
        "policies": detect_policy_drift(env_a_id, env_b_id),
        "profiles": detect_profile_drift(env_a_id, env_b_id),
        "templates": detect_template_drift(env_a_id, env_b_id),
        "feature_flags": detect_feature_flag_drift(env_a_id, env_b_id),
    }

    has_drift = False
    for scope in ("policies", "profiles", "templates"):
        section = report[scope]
        if section.get("error"):
            has_drift = True
            continue
        if section.get("only_in_a") or section.get("only_in_b"):
            has_drift = True
    ff = report["feature_flags"]
    if not ff.get("error"):
        if ff.get("only_in_a") or ff.get("only_in_b") or ff.get("different"):
            has_drift = True

    report["has_drift"] = has_drift

    _DRIFT_LOG.append({
        "env_a": env_a_id,
        "env_b": env_b_id,
        "has_drift": has_drift,
        "timestamp": report["timestamp"],
    })

    return report
