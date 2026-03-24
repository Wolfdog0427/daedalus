# runtime/tier3_env_guardrails.py
"""
Read-only environment guardrails.

Guardrails are pre-action checks that evaluate whether an
operator-triggered action should proceed under the active
environment.  They never mutate state, never auto-block
silently, and never auto-correct anything.  Each check returns
a structured guardrail_result.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_GUARDRAIL_LOG: List[Dict[str, Any]] = []


def get_guardrail_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_GUARDRAIL_LOG[-limit:])


def clear_guardrail_log() -> None:
    _GUARDRAIL_LOG.clear()


def _result(
    action: str,
    allowed: bool,
    blocking_reasons: List[str],
    warnings: List[str],
) -> Dict[str, Any]:
    entry = {
        "action": action,
        "allowed": allowed,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "timestamp": time.time(),
    }
    _GUARDRAIL_LOG.append(entry)
    return entry


# ------------------------------------------------------------------
# Guardrail checks
# ------------------------------------------------------------------

def check_profile_activation(profile_id: str) -> Dict[str, Any]:
    """Check whether activating a profile is safe under the active environment."""
    blocking: List[str] = []
    warnings: List[str] = []

    try:
        from runtime.tier3_environments import (
            get_active_environment, is_profile_allowed,
        )
        env = get_active_environment()
        if env is not None:
            if not is_profile_allowed(profile_id):
                blocking.append(
                    f"profile '{profile_id}' not in environment "
                    f"'{env['name']}' allowed list")

            dp = env.get("default_profile_id")
            if dp and dp != profile_id:
                warnings.append(
                    f"environment suggests default profile '{dp}', "
                    f"activating '{profile_id}' instead")
    except Exception:
        pass

    try:
        from runtime.tier3_profiles import get_profile
        if get_profile(profile_id) is None:
            blocking.append(f"profile '{profile_id}' does not exist")
    except Exception:
        pass

    return _result("profile_activation", len(blocking) == 0, blocking, warnings)


def check_plan_execution(plan_id: str) -> Dict[str, Any]:
    """Check whether executing a plan is safe under the active environment."""
    blocking: List[str] = []
    warnings: List[str] = []

    try:
        from runtime.tier3_profiles import get_feature_flag
        if not get_feature_flag("allow_plans"):
            blocking.append("feature flag allow_plans is False")
    except Exception:
        pass

    try:
        from runtime.tier3_plans import get_plan
        plan = get_plan(plan_id)
        if plan is None:
            blocking.append(f"plan '{plan_id}' does not exist")
        elif plan.get("status") not in ("draft", "ready"):
            warnings.append(
                f"plan status is '{plan.get('status')}', expected draft or ready")
    except Exception:
        pass

    return _result("plan_execution", len(blocking) == 0, blocking, warnings)


def check_template_instantiation(template_id: str) -> Dict[str, Any]:
    """Check whether instantiating a template is safe under the active environment."""
    blocking: List[str] = []
    warnings: List[str] = []

    try:
        from runtime.tier3_environments import (
            get_active_environment, is_template_allowed,
        )
        env = get_active_environment()
        if env is not None:
            if not is_template_allowed(template_id):
                blocking.append(
                    f"template '{template_id}' not in environment "
                    f"'{env['name']}' allowed list")
    except Exception:
        pass

    try:
        from runtime.tier3_runbook_templates import get_template
        if get_template(template_id) is None:
            blocking.append(f"template '{template_id}' does not exist")
    except Exception:
        pass

    return _result(
        "template_instantiation", len(blocking) == 0, blocking, warnings)


def check_promotion_runbook(
    source_env_id: str,
    target_env_id: str,
) -> Dict[str, Any]:
    """Check whether creating a promotion runbook is advisable."""
    blocking: List[str] = []
    warnings: List[str] = []

    try:
        from runtime.tier3_environments import get_environment, get_promotion_path
        if get_environment(source_env_id) is None:
            blocking.append(f"source environment '{source_env_id}' not found")
        if get_environment(target_env_id) is None:
            blocking.append(f"target environment '{target_env_id}' not found")

        if not blocking:
            path = get_promotion_path(source_env_id, target_env_id)
            if path.get("error"):
                blocking.append(path["reason"])
    except Exception:
        pass

    if not blocking:
        try:
            from runtime.tier3_env_health import compute_promotion_readiness
            readiness = compute_promotion_readiness(
                source_env_id, target_env_id)
            score = readiness.get("readiness_score", 0)
            if score < 30:
                blocking.append(
                    f"readiness score too low ({score}/100)")
            elif score < 60:
                warnings.append(
                    f"readiness score is marginal ({score}/100)")
            for b in readiness.get("blockers", []):
                if b not in blocking:
                    blocking.append(b)
            for w in readiness.get("warnings", []):
                if w not in warnings:
                    warnings.append(w)
        except Exception:
            warnings.append("readiness scoring unavailable")

    return _result(
        "promotion_runbook", len(blocking) == 0, blocking, warnings)


def check_migration_execution(proposal_id: str) -> Dict[str, Any]:
    """Check whether executing a migration proposal is safe."""
    blocking: List[str] = []
    warnings: List[str] = []

    try:
        from runtime.tier3_profiles import get_feature_flag
        if not get_feature_flag("allow_migrations"):
            blocking.append("feature flag allow_migrations is False")
    except Exception:
        pass

    try:
        from runtime.tier3_environments import get_active_environment
        env = get_active_environment()
        if env is not None:
            env_flags = env.get("default_feature_flags", {})
            if env_flags.get("allow_migrations") is False:
                if "feature flag allow_migrations is False" not in blocking:
                    blocking.append(
                        "environment default_feature_flags: allow_migrations=False")
    except Exception:
        pass

    return _result(
        "migration_execution", len(blocking) == 0, blocking, warnings)


# ------------------------------------------------------------------
# Unified check dispatcher
# ------------------------------------------------------------------

_CHECK_DISPATCH = {
    "profile_activation": lambda p: check_profile_activation(
        p.get("profile_id", "")),
    "plan_execution": lambda p: check_plan_execution(
        p.get("plan_id", "")),
    "template_instantiation": lambda p: check_template_instantiation(
        p.get("template_id", "")),
    "promotion_runbook": lambda p: check_promotion_runbook(
        p.get("source_env_id", ""), p.get("target_env_id", "")),
    "migration_execution": lambda p: check_migration_execution(
        p.get("proposal_id", "")),
}


def run_guardrail_check(
    action: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a named guardrail check with the given parameters."""
    fn = _CHECK_DISPATCH.get(action)
    if fn is None:
        return _result(action, False, [f"unknown guardrail action '{action}'"], [])
    return fn(parameters)


def list_guardrail_categories() -> List[str]:
    return sorted(_CHECK_DISPATCH.keys())
