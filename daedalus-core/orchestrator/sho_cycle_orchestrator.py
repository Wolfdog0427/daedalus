# orchestrator/sho_cycle_orchestrator.py

from __future__ import annotations
from typing import Dict, Any

from knowledge.drift_detector import compute_drift
from knowledge.system_stability import compute_stability
from knowledge.dignostics import compute_diagnostics
from knowledge.patch_applier import apply_patch
from knowledge.patch_generator import _normal_patch as generate_patch


def run_sho_cycle(governor) -> Dict[str, Any]:
    """
    SHO cycle with governor-aware behavior.
    """

    drift = compute_drift()
    stability = compute_stability()
    diagnostics = compute_diagnostics()

    signals = {
        "drift": drift,
        "stability": stability,
        "diagnostics": diagnostics,
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
    if governor.tier == 3:
        patch = generate_patch(diagnostics)
        applied = apply_patch(patch)

        return {
            "cycle": {"mode": "autonomous", "signals": signals},
            "patch": {"proposal": patch, "applied": applied},
        }

    # Fallback
    return {
        "cycle": {"mode": "unknown", "signals": signals},
        "patch": None,
    }
