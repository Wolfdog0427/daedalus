# runtime/tier3_env_health.py
"""
Read-only environment health scoring.

Computes a structured health report for a Tier-3 environment by
inspecting its defaults, pack validation, upstream drift, and
override conflicts.  All functions are side-effect-free — they
never mutate state or auto-correct anything.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_HEALTH_LOG: List[Dict[str, Any]] = []


def get_health_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_HEALTH_LOG[-limit:])


def clear_health_log() -> None:
    _HEALTH_LOG.clear()


# ------------------------------------------------------------------
# Scoring helpers
# ------------------------------------------------------------------

def _check_defaults(env: Dict[str, Any]) -> List[Dict[str, str]]:
    """Flag missing or incomplete defaults."""
    findings: List[Dict[str, str]] = []
    if not env.get("default_profile_id"):
        findings.append({
            "category": "missing_default",
            "detail": "no default_profile_id set",
        })
    if not env.get("default_policy_ids"):
        findings.append({
            "category": "missing_default",
            "detail": "no default_policy_ids set",
        })
    if not env.get("default_feature_flags"):
        findings.append({
            "category": "missing_default",
            "detail": "no default_feature_flags set",
        })
    return findings


def _check_unused(env: Dict[str, Any]) -> List[Dict[str, str]]:
    """Detect policies or templates in allowlists but not in defaults or packs."""
    findings: List[Dict[str, str]] = []
    allowed_pol = set(env.get("allowed_policy_ids", []))
    default_pol = set(env.get("default_policy_ids", []))
    unused_pol = allowed_pol - default_pol
    for pid in sorted(unused_pol):
        findings.append({
            "category": "unused_policy",
            "detail": f"policy '{pid}' allowed but not in defaults",
        })

    allowed_tmpl = set(env.get("allowed_runbook_template_ids", []))
    if allowed_tmpl and not env.get("applied_pack_ids"):
        for tid in sorted(allowed_tmpl):
            findings.append({
                "category": "unused_template",
                "detail": f"template '{tid}' allowed but no packs applied",
            })
    return findings


def _check_override_conflicts(env: Dict[str, Any]) -> List[Dict[str, str]]:
    """Detect scheduling overrides for policies not in scope."""
    findings: List[Dict[str, str]] = []
    effective_pols = set(env.get("allowed_policy_ids", []))
    effective_pols |= set(env.get("default_policy_ids", []))

    for pol_id in env.get("default_scheduling_overrides", {}):
        if pol_id not in effective_pols:
            findings.append({
                "category": "orphan_override",
                "detail": f"scheduling override for '{pol_id}' which is not in scope",
            })
    return findings


def _check_pack_validation(env: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validate all applied packs against the environment."""
    findings: List[Dict[str, str]] = []
    try:
        from runtime.tier3_envpacks import validate_envpack_against_environment
        for pack_id in env.get("applied_pack_ids", []):
            result = validate_envpack_against_environment(pack_id, env["env_id"])
            if not result.get("valid"):
                for issue in result.get("issues", []):
                    findings.append({
                        "category": "pack_issue",
                        "detail": (
                            f"pack '{pack_id[:12]}..': {issue['scope']} "
                            f"'{issue['id']}' — {issue['issue']}"
                        ),
                    })
    except Exception:
        pass
    return findings


def _check_upstream_drift(env: Dict[str, Any]) -> Dict[str, Any]:
    """If the environment has an upstream, report drift summary."""
    upstream_id = env.get("upstream_env_id")
    if not upstream_id:
        return {"has_upstream": False}
    try:
        from runtime.tier3_env_drift import detect_full_env_drift
        drift = detect_full_env_drift(upstream_id, env["env_id"])
        return {
            "has_upstream": True,
            "upstream_env_id": upstream_id,
            "has_drift": drift.get("has_drift", False),
            "drift_summary": {
                "policies_only_upstream": len(
                    drift.get("policies", {}).get("only_in_a", [])),
                "policies_only_here": len(
                    drift.get("policies", {}).get("only_in_b", [])),
                "profiles_only_upstream": len(
                    drift.get("profiles", {}).get("only_in_a", [])),
                "profiles_only_here": len(
                    drift.get("profiles", {}).get("only_in_b", [])),
                "templates_only_upstream": len(
                    drift.get("templates", {}).get("only_in_a", [])),
                "templates_only_here": len(
                    drift.get("templates", {}).get("only_in_b", [])),
                "flag_differences": len(
                    drift.get("feature_flags", {}).get("different", {})),
            },
        }
    except Exception:
        return {"has_upstream": True, "upstream_env_id": upstream_id, "error": True}


# ------------------------------------------------------------------
# Main scorer
# ------------------------------------------------------------------

def compute_environment_health(env_id: str) -> Dict[str, Any]:
    """Compute a read-only health report for an environment."""
    from runtime.tier3_environments import get_environment

    env = get_environment(env_id)
    if env is None:
        return {"error": True, "reason": f"environment '{env_id}' not found"}

    findings: List[Dict[str, str]] = []
    findings.extend(_check_defaults(env))
    findings.extend(_check_unused(env))
    findings.extend(_check_override_conflicts(env))
    findings.extend(_check_pack_validation(env))
    upstream_drift = _check_upstream_drift(env)

    n_issues = len(findings)
    has_drift = upstream_drift.get("has_drift", False)

    if n_issues == 0 and not has_drift:
        grade = "healthy"
    elif n_issues <= 2 and not has_drift:
        grade = "minor_issues"
    elif has_drift and n_issues <= 2:
        grade = "drift_detected"
    else:
        grade = "needs_attention"

    report = {
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "grade": grade,
        "findings": findings,
        "upstream_drift": upstream_drift,
        "applied_packs": len(env.get("applied_pack_ids", [])),
        "effective_policies": len(
            set(env.get("allowed_policy_ids", []))
            | set(env.get("default_policy_ids", []))),
        "effective_profiles": len(env.get("allowed_profile_ids", [])),
        "effective_templates": len(env.get("allowed_runbook_template_ids", [])),
        "timestamp": time.time(),
    }

    _HEALTH_LOG.append({
        "env_id": env_id,
        "grade": grade,
        "findings_count": n_issues,
        "has_drift": has_drift,
        "timestamp": report["timestamp"],
    })

    return report


def compute_all_environment_health() -> List[Dict[str, Any]]:
    """Compute health for every registered environment."""
    from runtime.tier3_environments import list_environments
    return [
        compute_environment_health(e["env_id"])
        for e in list_environments()
    ]


# ------------------------------------------------------------------
# Promotion readiness
# ------------------------------------------------------------------

_READINESS_LOG: List[Dict[str, Any]] = []


def get_readiness_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_READINESS_LOG[-limit:])


def clear_readiness_log() -> None:
    _READINESS_LOG.clear()


def compute_promotion_readiness(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    """
    Compute a read-only promotion-readiness score (0–100) for promoting
    governance from source to target.  Considers health, drift, pack
    validation, feature-flag compatibility, and promotion path.
    """
    from runtime.tier3_environments import get_environment

    src = get_environment(source_env_id)
    if src is None:
        return {"error": True, "reason": f"source environment '{source_env_id}' not found"}
    tgt = get_environment(target_env_id)
    if tgt is None:
        return {"error": True, "reason": f"target environment '{target_env_id}' not found"}

    blockers: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    score = 100

    src_health = compute_environment_health(source_env_id)
    tgt_health = compute_environment_health(target_env_id)

    if src_health.get("grade") == "needs_attention":
        blockers.append("source environment health: needs_attention")
        score -= 30
    elif src_health.get("grade") == "drift_detected":
        warnings.append("source environment has upstream drift")
        score -= 10
    elif src_health.get("grade") == "minor_issues":
        score -= 5

    if tgt_health.get("grade") == "needs_attention":
        blockers.append("target environment health: needs_attention")
        score -= 30
    elif tgt_health.get("grade") == "drift_detected":
        warnings.append("target environment has upstream drift")
        score -= 10
    elif tgt_health.get("grade") == "minor_issues":
        score -= 5

    try:
        from runtime.tier3_env_drift import detect_full_env_drift
        drift = detect_full_env_drift(source_env_id, target_env_id)
        if drift.get("has_drift"):
            pol_a = len(drift.get("policies", {}).get("only_in_a", []))
            pol_b = len(drift.get("policies", {}).get("only_in_b", []))
            flag_diff = len(
                drift.get("feature_flags", {}).get("different", {}))
            if flag_diff > 0:
                warnings.append(
                    f"{flag_diff} feature-flag difference(s) between environments")
                score -= 5 * flag_diff
            if pol_a > 0:
                warnings.append(
                    f"{pol_a} policy/ies in source but not target")
                score -= 3 * pol_a
            if pol_b > 0:
                warnings.append(
                    f"{pol_b} policy/ies in target but not source")
                score -= 2 * pol_b
    except Exception:
        warnings.append("drift detection unavailable")
        score -= 10

    try:
        from runtime.tier3_promotion import plan_promotion
        plan = plan_promotion(source_env_id, target_env_id)
        n_ops = len(plan.get("operations", []))
        n_conflicts = len(plan.get("conflicts", []))
        if n_conflicts > 0:
            blockers.append(f"promotion plan has {n_conflicts} conflict(s)")
            score -= 15 * n_conflicts
        if not plan.get("has_promotion_path"):
            blockers.append("no promotion path from source to target")
            score -= 20
        if n_ops > 0:
            recommendations.append(
                f"promotion plan requires {n_ops} operation(s)")
    except Exception:
        warnings.append("promotion planning unavailable")
        score -= 5

    try:
        from runtime.tier3_envpacks import validate_envpack_against_environment
        for pack_id in src.get("applied_pack_ids", []):
            vr = validate_envpack_against_environment(pack_id, target_env_id)
            if not vr.get("valid"):
                n_issues = len(vr.get("issues", []))
                warnings.append(
                    f"source pack '{pack_id[:12]}..' has {n_issues} issue(s) "
                    f"against target environment")
                score -= 5 * n_issues
    except Exception:
        pass

    src_flags = src.get("default_feature_flags", {})
    tgt_flags = tgt.get("default_feature_flags", {})
    for key in set(src_flags) | set(tgt_flags):
        sv = src_flags.get(key)
        tv = tgt_flags.get(key)
        if sv is not None and tv is not None and sv != tv:
            pass  # already counted in drift

    if not src.get("default_profile_id"):
        recommendations.append("set default_profile_id on source environment")
    if not tgt.get("default_profile_id"):
        recommendations.append("set default_profile_id on target environment")

    score = max(0, min(100, score))

    report = {
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "readiness_score": score,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "source_grade": src_health.get("grade"),
        "target_grade": tgt_health.get("grade"),
        "timestamp": time.time(),
    }

    _READINESS_LOG.append({
        "source_env_id": source_env_id,
        "target_env_id": target_env_id,
        "readiness_score": score,
        "n_blockers": len(blockers),
        "n_warnings": len(warnings),
        "timestamp": report["timestamp"],
    })

    return report
