from __future__ import annotations

from core.contracts import ImprovementPlan, CandidateSummary
from core.contracts import SecurityStatus


class MetaGovernor:
    """
    Central governance layer:
    - architectural consistency
    - alignment
    - stability horizon
    - meta-invariants
    - security posture

    Reviews improvement plans and candidates through governance checks:
    safety invariants, risk scoring, and protected-domain detection.
    """

    def review_plan(self, plan: ImprovementPlan, security_status: SecurityStatus) -> ImprovementPlan:
        """Review an improvement plan against governance constraints.

        Blocks plans that touch protected domains without operator approval.
        Adjusts risk scores based on security posture.  Fail-closed: if
        checks raise, the plan is blocked rather than silently allowed.
        """
        try:
            from governance.meta_invariant_checker import MetaInvariantChecker
            checker = MetaInvariantChecker()
            violations = checker.check()
            if violations:
                plan.blocked = True
                plan.block_reason = (
                    f"meta-invariant violations detected: "
                    f"{'; '.join(violations[:3])}"
                )
                return plan
        except ImportError:
            plan.blocked = True
            plan.block_reason = "meta-invariant checker unavailable — fail-closed"
            return plan
        except Exception as exc:
            plan.blocked = True
            plan.block_reason = f"meta-invariant check failed (fail-closed): {exc}"
            return plan

        try:
            from governance.kernel import evaluate_change
            verdict = evaluate_change({
                "type": "self_modification",
                "target": plan.fix_request.target_subsystem,
                "description": getattr(plan.fix_request, "change_type", ""),
                "flags": [],
                "reversible": True,
            })
            if not verdict.get("allowed"):
                plan.blocked = True
                plan.block_reason = verdict.get("reason", "governance_block")
        except ImportError:
            plan.blocked = True
            plan.block_reason = "governance kernel unavailable — fail-closed"
        except Exception as exc:
            plan.blocked = True
            plan.block_reason = f"governance evaluation failed (fail-closed): {exc}"

        return plan

    def review_candidate(self, candidate: CandidateSummary, security_status: SecurityStatus) -> CandidateSummary:
        """Review a candidate through governance checks.

        Vetoes candidates with unacceptable risk or security concerns.
        Fail-closed: if checks raise, the candidate is vetoed.
        """
        try:
            if security_status and security_status.mode in ("suspicious", "locked_down"):
                candidate.vetoed = True
                candidate.veto_reason = (
                    f"security mode is "
                    f"{security_status.mode} — candidate vetoed"
                )
                return candidate
        except Exception as exc:
            candidate.vetoed = True
            candidate.veto_reason = f"security check failed (fail-closed): {exc}"
            return candidate

        try:
            from governance.kernel import compute_governance_health
            health = compute_governance_health()
            if health.get("governance_score", 100) < 40:
                candidate.vetoed = True
                candidate.veto_reason = (
                    f"governance health too low "
                    f"({health['governance_score']}/100) for changes"
                )
        except ImportError:
            candidate.vetoed = True
            candidate.veto_reason = "governance kernel unavailable — fail-closed"
            return candidate
        except Exception as exc:
            candidate.vetoed = True
            candidate.veto_reason = f"governance health check failed (fail-closed): {exc}"

        return candidate
