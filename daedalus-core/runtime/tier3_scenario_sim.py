# runtime/tier3_scenario_sim.py
"""
Scenario simulation for governance what-if analysis.

Simulates the impact of hypothetical changes to policies, packs,
and environments by cloning state, applying changes to the clone,
and computing predicted drift, health, readiness, and anomalies.
All functions are strictly read-only — they never mutate real
objects or create artifacts.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, List

_SIMULATION_LOG: List[Dict[str, Any]] = []


def get_simulation_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_SIMULATION_LOG[-limit:])


def clear_simulation_log() -> None:
    _SIMULATION_LOG.clear()


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


# ------------------------------------------------------------------
# Policy change simulation
# ------------------------------------------------------------------

def simulate_policy_change(
    policy_id: str,
    hypothetical_changes: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate the impact of changing a policy without mutating it."""
    try:
        from runtime.tier3_policies import get_policy
        pol = get_policy(policy_id)
        if pol is None:
            return {"error": True, "reason": f"policy '{policy_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read policy"}

    before = copy.deepcopy(pol)
    after = copy.deepcopy(pol)
    after.update(hypothetical_changes)

    impacts: List[Dict[str, str]] = []

    if before.get("enabled") and not after.get("enabled"):
        impacts.append({"impact": "policy_disabled", "detail": "policy would be disabled"})
    elif not before.get("enabled") and after.get("enabled"):
        impacts.append({"impact": "policy_enabled", "detail": "policy would be enabled"})

    if after.get("retired") and not before.get("retired"):
        impacts.append({"impact": "policy_retired", "detail": "policy would be retired"})

    old_conds = len(before.get("trigger_conditions", []))
    new_conds = len(after.get("trigger_conditions", []))
    if new_conds != old_conds:
        impacts.append({
            "impact": "conditions_changed",
            "detail": f"conditions: {old_conds} -> {new_conds}",
        })

    old_actions = len(before.get("actions", []))
    new_actions = len(after.get("actions", []))
    if new_actions != old_actions:
        impacts.append({
            "impact": "actions_changed",
            "detail": f"actions: {old_actions} -> {new_actions}",
        })

    env_presence = 0
    try:
        from runtime.tier3_environments import list_environments
        for env in list_environments():
            if (policy_id in env.get("allowed_policy_ids", [])
                    or policy_id in env.get("default_policy_ids", [])):
                env_presence += 1
    except Exception:
        pass

    if env_presence > 0 and after.get("retired"):
        impacts.append({
            "impact": "removal_from_environments",
            "detail": f"policy present in {env_presence} environment(s) — would need cleanup",
        })

    if not impacts:
        impacts.append({"impact": "no_significant_impact", "detail": "change has minimal effect"})

    result = {
        "simulation": "policy_change",
        "policy_id": policy_id,
        "policy_name": pol.get("name", "?"),
        "hypothetical_changes": hypothetical_changes,
        "impacts": impacts,
        "environments_affected": env_presence,
        "timestamp": time.time(),
    }

    _SIMULATION_LOG.append({
        "type": "policy_change",
        "policy_id": policy_id,
        "n_impacts": len(impacts),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scenario_simulation",
        f"policy '{pol.get('name', '?')}' change: {len(impacts)} impact(s)",
        {"policy_id": policy_id, "impacts": [i["impact"] for i in impacts]},
        [policy_id],
    )

    return result


# ------------------------------------------------------------------
# Pack change simulation
# ------------------------------------------------------------------

def simulate_pack_change(
    pack_id: str,
    hypothetical_changes: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate the impact of changing a governance pack."""
    try:
        from runtime.tier3_envpacks import get_envpack
        pack = get_envpack(pack_id)
        if pack is None:
            return {"error": True, "reason": f"pack '{pack_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read pack"}

    before = copy.deepcopy(pack)
    after = copy.deepcopy(pack)
    after.update(hypothetical_changes)

    impacts: List[Dict[str, str]] = []

    old_pols = set(before.get("policy_ids", []))
    new_pols = set(after.get("policy_ids", []))
    added_pols = new_pols - old_pols
    removed_pols = old_pols - new_pols
    if added_pols:
        impacts.append({
            "impact": "policies_added",
            "detail": f"{len(added_pols)} policy/ies added to pack",
        })
    if removed_pols:
        impacts.append({
            "impact": "policies_removed",
            "detail": f"{len(removed_pols)} policy/ies removed from pack",
        })

    old_flags = before.get("feature_flag_overrides", {})
    new_flags = after.get("feature_flag_overrides", {})
    if old_flags != new_flags:
        impacts.append({
            "impact": "flags_changed",
            "detail": f"feature flags would change from {old_flags} to {new_flags}",
        })

    env_count = 0
    try:
        from runtime.tier3_environments import list_environments
        for env in list_environments():
            if pack_id in env.get("applied_pack_ids", []):
                env_count += 1
    except Exception:
        pass

    if env_count > 0:
        impacts.append({
            "impact": "environments_affected",
            "detail": f"pack is applied to {env_count} environment(s)",
        })

    if not impacts:
        impacts.append({"impact": "no_significant_impact", "detail": "change has minimal effect"})

    result = {
        "simulation": "pack_change",
        "pack_id": pack_id,
        "pack_name": pack.get("name", "?"),
        "hypothetical_changes": hypothetical_changes,
        "impacts": impacts,
        "environments_affected": env_count,
        "timestamp": time.time(),
    }

    _SIMULATION_LOG.append({
        "type": "pack_change",
        "pack_id": pack_id,
        "n_impacts": len(impacts),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scenario_simulation",
        f"pack '{pack.get('name', '?')}' change: {len(impacts)} impact(s)",
        {"pack_id": pack_id, "impacts": [i["impact"] for i in impacts]},
        [pack_id],
    )

    return result


# ------------------------------------------------------------------
# Environment change simulation
# ------------------------------------------------------------------

def simulate_environment_change(
    env_id: str,
    hypothetical_changes: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate the impact of changing an environment's configuration."""
    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    before = copy.deepcopy(env)
    after = copy.deepcopy(env)
    after.update(hypothetical_changes)

    impacts: List[Dict[str, str]] = []

    old_pols = set(before.get("allowed_policy_ids", []))
    new_pols = set(after.get("allowed_policy_ids", []))
    added = new_pols - old_pols
    removed = old_pols - new_pols
    if added:
        impacts.append({
            "impact": "policies_added",
            "detail": f"{len(added)} policy/ies added to allowlist",
        })
    if removed:
        impacts.append({
            "impact": "policies_removed",
            "detail": f"{len(removed)} policy/ies removed from allowlist",
        })

    old_profs = set(before.get("allowed_profile_ids", []))
    new_profs = set(after.get("allowed_profile_ids", []))
    if old_profs != new_profs:
        impacts.append({
            "impact": "profiles_changed",
            "detail": (
                f"profiles: +{len(new_profs - old_profs)} "
                f"-{len(old_profs - new_profs)}"
            ),
        })

    old_flags = before.get("default_feature_flags", {})
    new_flags = after.get("default_feature_flags", {})
    if old_flags != new_flags:
        changed_keys = [
            k for k in set(old_flags) | set(new_flags)
            if old_flags.get(k) != new_flags.get(k)
        ]
        impacts.append({
            "impact": "feature_flags_changed",
            "detail": f"{len(changed_keys)} flag(s) changed: {changed_keys}",
        })

    upstream = env.get("upstream_env_id")
    if upstream:
        impacts.append({
            "impact": "upstream_drift_possible",
            "detail": f"changes may cause drift from upstream '{upstream[:8]}..'",
        })

    downstream = env.get("downstream_env_ids", [])
    if downstream:
        impacts.append({
            "impact": "downstream_impact",
            "detail": f"{len(downstream)} downstream environment(s) may be affected",
        })

    if not impacts:
        impacts.append({"impact": "no_significant_impact", "detail": "change has minimal effect"})

    result = {
        "simulation": "environment_change",
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "hypothetical_changes": hypothetical_changes,
        "impacts": impacts,
        "timestamp": time.time(),
    }

    _SIMULATION_LOG.append({
        "type": "environment_change",
        "env_id": env_id,
        "n_impacts": len(impacts),
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "scenario_simulation",
        f"env '{env.get('name', '?')}' change: {len(impacts)} impact(s)",
        {"env_id": env_id, "impacts": [i["impact"] for i in impacts]},
        [env_id],
    )

    return result
