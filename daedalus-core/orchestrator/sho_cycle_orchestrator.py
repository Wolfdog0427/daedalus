# orchestrator/sho_cycle_orchestrator.py
"""
Knowledge-layer SHO cycle coordinator (lightweight, tier-driven).

Hierarchy position
------------------
This is the *primary* SHO entry-point used by ``runtime.sho_bootstrap``
and ``runtime.scheduler``.  It is a thin, functional wrapper that
observes / proposes / applies a single patch based on the governor's
autonomy tier.

Related SHO modules (do NOT confuse):
  - ``runtime.sho_cycle_orchestrator``  — class-based, DI-style
    orchestrator used by ``RuntimeLoop`` / ``runtime_main``.
  - ``knowledge.self_healing_orchestrator`` — full pipeline SHO
    with sandboxing, scoring, and persistence for nightly /
    web-triggered improvement cycles.
  - ``orchestrator.orchestrator`` — planning-only orchestrator
    (security checks + proposal-to-plan translation).
"""

from __future__ import annotations
from typing import Dict, Any

from knowledge.drift_detector import compute_drift
from knowledge.system_stability import compute_stability
from knowledge.diagnostics import compute_diagnostics
from knowledge.patch_applier import apply_patch
from knowledge.patch_generator import _normal_patch as generate_patch


def run_sho_cycle(governor) -> Dict[str, Any]:
    """Run one tier-driven SHO observe / propose / apply cycle."""

    drift = compute_drift()
    stability = compute_stability()
    diagnostics = compute_diagnostics()

    signals = {
        "drift": drift,
        "stability": stability,
        "diagnostics": diagnostics,
    }

    if governor.tier < 1:
        return {
            "cycle": {"mode": "disabled", "signals": signals},
            "patch": None,
        }

    # Tier 1: passive — SHO only observes
    if governor.tier == 1:
        return {
            "cycle": {"mode": "observe", "signals": signals},
            "patch": None,
        }

    # Tier 2: assisted — SHO proposes patches but does not apply
    if governor.tier == 2:
        patch = generate_patch(diagnostics)
        return {
            "cycle": {"mode": "propose", "signals": signals},
            "patch": {"proposal": patch, "applied": False},
        }

    # Tier 3: autonomous strict — SHO proposes AND applies patches
    #         All mutations still pass through the governance kernel.
    if governor.tier == 3:
        patch = generate_patch(diagnostics)

        try:
            from governance.kernel import evaluate_change
            verdict = evaluate_change({
                "type": "patch_apply",
                "source": "sho_tier3",
                "patch": patch,
            })
        except ImportError:
            verdict = {"allowed": False, "reason": "governance kernel unavailable — fail-closed"}
        except Exception:
            verdict = {"allowed": False, "reason": "governance evaluation failed — fail-closed"}

        if verdict.get("allowed", False):
            result = apply_patch(patch)
            applied = isinstance(result, dict) and result.get("status") == "success"
        else:
            result = None
            applied = False

        return {
            "cycle": {"mode": "autonomous", "signals": signals},
            "patch": {
                "proposal": patch,
                "applied": applied,
                "apply_result": result,
                "governance_verdict": verdict,
            },
        }

    # Fallback
    return {
        "cycle": {"mode": "unknown", "signals": signals},
        "patch": None,
    }
