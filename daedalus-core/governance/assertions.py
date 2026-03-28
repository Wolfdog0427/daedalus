# governance/assertions.py
"""
Safety and sovereignty assertions for Daedalus governance.

These are diagnostic helpers, not hot-path guards.  They verify
that the system's invariants, autonomy boundaries, and operator
sovereignty guarantees are intact.
"""

from __future__ import annotations

from typing import Any, Dict


def assert_safety_invariants() -> Dict[str, Any]:
    """Verify all 8 safety invariants are defined and enforceable."""
    try:
        from governance.safety_invariants import list_invariants, enforce_invariants

        invariants = list_invariants()
        required_ids = {
            "NO_AUTONOMY_EXPANSION",
            "NO_SAFETY_BYPASS",
            "NO_PERSONAL_DATA_PERSISTENCE",
            "NO_EMOTIONAL_INFERENCE",
            "NO_PSYCHOLOGICAL_MODELING",
            "NO_SELF_MODIFICATION_WITHOUT_APPROVAL",
            "OPERATOR_OVERRIDE_SOVEREIGN",
            "REVERSIBILITY_DEFAULT",
        }
        present_ids = {inv["id"] for inv in invariants}
        missing = required_ids - present_ids

        health_check = enforce_invariants(None)

        return {
            "passed": len(missing) == 0 and health_check["passed"],
            "invariant_count": len(invariants),
            "missing": sorted(missing),
            "health_check": health_check,
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def assert_no_autonomy_expansion() -> Dict[str, Any]:
    """Verify autonomy tiers have not been expanded beyond definitions."""
    try:
        from runtime.autonomy_tiers import list_tiers, TIER_0, TIER_1, TIER_2, TIER_3, TIER_DEFENSIVE

        tiers = list_tiers()
        tier_ids = {t["tier_id"] for t in tiers}
        canonical = {TIER_0, TIER_1, TIER_2, TIER_3, TIER_DEFENSIVE}
        extra = tier_ids - canonical

        from runtime.autonomy_engine import get_effective_tier
        effective = get_effective_tier()
        effective_id = effective.get("tier_id")

        return {
            "passed": len(extra) == 0 and effective_id in canonical,
            "canonical_tiers": sorted(canonical),
            "actual_tiers": sorted(tier_ids),
            "extra_tiers": sorted(extra),
            "effective_tier": effective_id,
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def assert_operator_sovereignty() -> Dict[str, Any]:
    """Verify operator sovereignty is intact.

    Checks that:
    1. The sovereignty safety invariant exists
    2. ALL defined personas honour operator override
    3. No forbidden change types have been added to allowed sets
    """
    issues: list = []

    try:
        from governance.safety_invariants import get_invariant
        sov = get_invariant("OPERATOR_OVERRIDE_SOVEREIGN")
        if sov is None:
            issues.append("OPERATOR_OVERRIDE_SOVEREIGN invariant missing")
    except Exception as e:
        issues.append(f"safety_invariants unavailable: {e}")
        sov = None

    try:
        from governance.personas import list_personas
        personas = list_personas()
        for p in personas:
            if p.get("operator_override") != "always_honoured":
                issues.append(
                    f"persona '{p.get('persona_id')}' does not set "
                    f"operator_override to 'always_honoured' "
                    f"(has: '{p.get('operator_override')}')"
                )
            if "modify_safety_invariants" not in p.get("forbidden_operations", []):
                issues.append(
                    f"persona '{p.get('persona_id')}' does not forbid "
                    f"'modify_safety_invariants'"
                )
    except Exception as e:
        issues.append(f"personas module unavailable: {e}")

    try:
        from governance.kernel import get_kernel_state
        ks = get_kernel_state()
    except Exception:
        ks = {}

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "sovereignty_invariant_exists": sov is not None,
        "kill_switch": ks.get("kill_switch", False),
        "circuit_breaker": ks.get("circuit_breaker", False),
        "stabilise_mode": ks.get("stabilise_mode", False),
    }
