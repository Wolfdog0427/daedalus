# runtime/patch_engine.py

from __future__ import annotations
from typing import Dict, Any

from knowledge.patch_applier import apply_patch_live
from governor.proposal_manager import load_proposal_by_id


def apply_patch(proposal_id: str) -> Dict[str, Any]:
    """
    Apply the patch associated with proposal_id using the live patch applier.
    Routed through the governance kernel — patches require approval.

    Returns a dict like:
    {
        "status": "success" | "failed",
        "details": {...},
        "proposal_id": str,
    }
    """
    plan = load_proposal_by_id(proposal_id)
    if not plan:
        return {
            "status": "failed",
            "proposal_id": proposal_id,
            "details": {"error": "proposal not found"},
        }

    try:
        from governance.kernel import evaluate_change
        verdict = evaluate_change({
            "type": "patch_apply",
            "source": "patch_engine",
            "patch": {"proposal_id": proposal_id},
            "reversible": True,
        })
        if not verdict.get("allowed", False) or verdict.get("needs_approval", False):
            return {
                "status": "failed",
                "proposal_id": proposal_id,
                "details": {"error": "governance blocked", "verdict": verdict},
            }
    except ImportError:
        return {
            "status": "failed",
            "proposal_id": proposal_id,
            "details": {"error": "governance kernel missing — fail-closed"},
        }
    except Exception:
        return {
            "status": "failed",
            "proposal_id": proposal_id,
            "details": {"error": "governance evaluation failed — fail-closed"},
        }

    result = apply_patch_live(plan)
    result["proposal_id"] = proposal_id
    return result


def fetch_post_state() -> Dict[str, Any]:
    """
    Fetch updated state after patch application.

    This will be wired to the same sources as fetch_state()
    (drift, stability, diagnostics, patch_history), but evaluated
    after the patch has been applied.

    For now, this will be implemented once state_sources.py is finalized.
    """
    from runtime.state_sources import fetch_state  # local import to avoid cycles
    return fetch_state()
