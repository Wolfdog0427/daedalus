from typing import Any, Dict, List


class MetaInvariantChecker:
    """Verifies that core meta-invariants are intact across the system.

    Meta-invariants are structural guarantees that span multiple modules:
    - All 8 safety invariants are defined and enforceable
    - Operator sovereignty is intact
    - No unauthorized autonomy expansion
    - Canonical template invariants resolve to real modules
    - Governance kernel is reachable and not permanently degraded
    """

    def check(self) -> List[str]:
        """Return list of violated meta-invariants (as messages)."""
        violations: List[str] = []

        # 1. Safety invariants
        try:
            from governance.safety_invariants import list_invariants
            invariants = list_invariants()
            required = {
                "NO_AUTONOMY_EXPANSION", "NO_SAFETY_BYPASS",
                "NO_PERSONAL_DATA_PERSISTENCE", "NO_EMOTIONAL_INFERENCE",
                "NO_PSYCHOLOGICAL_MODELING",
                "NO_SELF_MODIFICATION_WITHOUT_APPROVAL",
                "OPERATOR_OVERRIDE_SOVEREIGN", "REVERSIBILITY_DEFAULT",
            }
            present = {inv["id"] for inv in invariants}
            for missing in required - present:
                violations.append(f"safety invariant {missing} is not defined")
        except Exception as e:
            violations.append(f"safety_invariants module unavailable: {e}")

        # 2. Operator sovereignty
        try:
            from governance.personas import get_active_persona
            persona = get_active_persona()
            if persona.get("operator_override") != "always_honoured":
                violations.append(
                    f"active persona '{persona.get('persona_id')}' does not "
                    f"honour operator override"
                )
        except Exception as e:
            violations.append(f"persona module unavailable: {e}")

        # 3. Canonical template invariants
        try:
            from knowledge.entropy.canonical_template import check_invariants
            ci = check_invariants()
            for m in ci.get("missing", []):
                violations.append(f"canonical invariant '{m}' module not found")
        except ImportError:
            pass
        except Exception as e:
            violations.append(f"canonical template check failed: {e}")

        # 4. Kernel reachability
        try:
            from governance.kernel import compute_governance_health
            health = compute_governance_health()
            score = health.get("governance_score", 0)
            if score < 20:
                violations.append(
                    f"governance health critically low ({score}/100)")
        except Exception as e:
            violations.append(f"governance kernel unreachable: {e}")

        return violations

    def full_report(self) -> Dict[str, Any]:
        """Run all checks and return a structured report."""
        violations = self.check()
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "violation_count": len(violations),
        }
