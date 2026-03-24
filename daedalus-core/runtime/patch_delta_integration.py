# runtime/patch_delta_integration.py

from __future__ import annotations

from typing import Any, Dict

from analytics.delta_validation import record_delta_outcome
from runtime.metrics_capture import build_metrics_from_state


def build_pre_metrics(
    drift: Dict[str, Any],
    stability: Dict[str, Any],
    diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience wrapper to build pre-patch metrics.
    """
    return build_metrics_from_state(drift, stability, diagnostics)


def build_post_metrics(
    drift: Dict[str, Any],
    stability: Dict[str, Any],
    diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience wrapper to build post-patch metrics.
    """
    return build_metrics_from_state(drift, stability, diagnostics)


def record_patch_deltas(
    cycle_id: str,
    proposal_id: str,
    plan: Dict[str, Any],
    pre_metrics: Dict[str, Any],
    post_metrics: Dict[str, Any],
) -> None:
    """
    Single call to log predicted vs actual deltas.

    Safe to call from:
    - SHO orchestrator
    - Post-patch maintenance cycle
    - Any place where you have plan + pre/post metrics
    """
    record_delta_outcome(
        cycle_id=cycle_id,
        proposal_id=proposal_id,
        plan=plan,
        pre_metrics=pre_metrics,
        post_metrics=post_metrics,
    )
