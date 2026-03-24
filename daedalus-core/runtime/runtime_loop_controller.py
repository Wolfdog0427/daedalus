# runtime/runtime_loop_controller.py
"""
Governed, periodic runtime loop.

Runs :func:`runtime.runtime_loop_bootstrap.run_runtime_cycle_once` a fixed
number of times at a caller-controlled interval. Synchronous, single-threaded,
no scheduling, no autonomous behaviour.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------
# Phase 18: cadence config and in-memory autonomy state
# ------------------------------------------------------------

TIER1_AUTONOMY_CADENCE: int = 5

_autonomy_cycle_counter: int = 0

_last_autonomy_result: Optional[Dict[str, Any]] = None


def get_last_autonomy_result() -> Optional[Dict[str, Any]]:
    """Return the most recent active autonomy cycle result (or None)."""
    return _last_autonomy_result


def get_cycles_until_next_autonomy() -> int:
    """Return the number of runtime loop iterations until the next autonomy pass."""
    if TIER1_AUTONOMY_CADENCE <= 0:
        return 0
    remainder = _autonomy_cycle_counter % TIER1_AUTONOMY_CADENCE
    return TIER1_AUTONOMY_CADENCE - remainder


def _apply_expression_shaping(cycle_result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the full identity-stack pipeline to a cycle result.

    Pipeline order (aligned with architecture spec):
      1. Gather context  (posture, tier, operator context)
      2. Update session continuity
      3. Evaluate identity coherence
      4. Update stability regulator
      5. Expression shaping  (posture_expression → expression_engine)
      6. Interaction cycle shaping
      7. Interaction model flow shaping
      8. Capture telemetry  (coherence, stability, resonance)

    Falls back silently if any module is unavailable.
    """
    try:
        # ── 1. Context gathering ─────────────────────────────────
        pid = None
        tid = None
        op_ctx: dict = {}
        try:
            from runtime.posture_state import get_current_posture
            pid = get_current_posture()["posture_id"]
        except Exception:
            pass
        try:
            from runtime.autonomy_engine import get_effective_tier
            tid = get_effective_tier().get("tier_id")
        except Exception:
            pass
        try:
            from runtime.operator_context import get_context
            op_ctx = get_context()
        except Exception:
            pass

        # ── 1b. Governance audit (filtered through binding) ─────
        try:
            from governance.runtime_binding import get_governance_view
            from governance.audit_log import log_event as _gov_log
            gov_view = get_governance_view({
                "posture_id": pid,
                "tier_id": tid,
                "interaction_intent": op_ctx.get("interaction_intent"),
                "operator_focus_level": op_ctx.get("operator_focus_level"),
                "operator_engagement_style": op_ctx.get("operator_engagement_style"),
            })
            _gov_log("runtime_cycle", gov_view)
        except Exception:
            pass

        # ── 2. Update session continuity ─────────────────────────
        try:
            from runtime.session_continuity import update_continuity
            update_continuity(
                posture_id=pid,
                tier_id=tid,
                operator_context=op_ctx,
            )
        except Exception:
            pass

        # ── 3. Evaluate identity coherence ───────────────────────
        coh_state: dict = {}
        try:
            from runtime.identity_coherence import compute_coherence_state
            from runtime.session_continuity import get_continuity_state as _gcs
            cont_st = _gcs()
            coh_state = compute_coherence_state(
                pid or "COMPANION", tid, op_ctx, cont_st,
            )
            cycle_result["coherence_score"] = coh_state.get("coherence_score", 100.0)
            cycle_result["coherence_mismatches"] = coh_state.get("n_mismatches", 0)
        except Exception:
            pass

        # ── 4. Update stability regulator ────────────────────────
        try:
            from runtime.stability_regulator import update_stability
            from runtime.session_continuity import get_continuity_state as _gcs2
            stab = update_stability(
                posture_id=pid,
                tier_id=tid,
                continuity_state=_gcs2(),
                coherence_state=coh_state,
            )
            cycle_result["stability_score"] = stab.get("stability_score", 100.0)
            cycle_result["oscillation_index"] = stab.get("oscillation_index", 0.0)
            cycle_result["jitter_index"] = stab.get("jitter_index", 0.0)
        except Exception:
            pass

        # ── 5–7. Expression + interaction shaping ────────────────
        from runtime.posture_expression import apply_expression_profile
        from runtime.interaction_cycle import shape_interaction

        status = cycle_result.get("status", "")
        if isinstance(status, str) and status:
            shaped = apply_expression_profile(status, {"source": "runtime_loop"})
            shaped = shape_interaction(shaped)
            try:
                from runtime.interaction_model import shape_interaction_flow
                shaped = shape_interaction_flow(shaped)
            except Exception:
                pass
            cycle_result["status_shaped"] = shaped

        # ── 8. Capture resonance + governance telemetry ─────────
        try:
            from runtime.resonance_engine import resonance_summary
            rs = resonance_summary()
            cycle_result["resonance_intensity"] = rs.get("resonance_intensity", 0.0)
            cycle_result["resonance_color"] = rs.get("resonance_color", "neutral")
            cycle_result["resonance_blend"] = rs.get("blend_factor", 1.0)
        except Exception:
            pass

        try:
            from governance.kernel import compute_governance_health
            gh = compute_governance_health()
            cycle_result["governance_health"] = gh.get("governance_score", 100.0)
        except Exception:
            pass

        cycle_result["expression_shaped"] = True
    except Exception:
        cycle_result["expression_shaped"] = False
    return cycle_result


def _posture_allows_autonomy() -> bool:
    """Check whether the active posture and autonomy tier permit actions.

    Consults the autonomy engine first (tier + posture), falling back
    to posture-only check, then to True if modules are unavailable.
    """
    try:
        from runtime.autonomy_engine import can_perform
        allowed, _ = can_perform("mutation")
        return allowed
    except Exception:
        pass
    try:
        from runtime.posture_autonomy import is_action_allowed
        allowed, _ = is_action_allowed("mutation")
        return allowed
    except Exception:
        return True


def _run_autonomy_pass() -> Dict[str, Any]:
    """
    Execute one autonomy pass: evaluate + execute eligible Tier-1 actions.

    Called inline from the main loop on cadence — never in the background.
    """
    from runtime.maintenance_actions import (
        get_default_tier1_actions,
        get_autonomy_settings,
        run_autonomy_loop,
        run_tier1_autonomy_cycle,
    )
    from runtime.system_dashboard import get_maintenance_envelope_summary

    actions = get_default_tier1_actions()
    envelope = get_maintenance_envelope_summary()
    settings = get_autonomy_settings()

    loop_report = run_autonomy_loop(actions, envelope)
    cycle_result = run_tier1_autonomy_cycle(actions, envelope)

    # Phase 28: record the cycle in the append-only log
    try:
        from runtime.autonomy_cycle_log import log_tier1_cycle

        executed = cycle_result.get("executed") or []
        skipped = cycle_result.get("skipped") or []
        if executed:
            result_tag = "success"
        elif skipped:
            result_tag = "skipped"
        else:
            result_tag = "skipped"
        log_tier1_cycle(time.time(), result_tag, envelope.get("summary", "unknown"))
    except Exception:
        pass

    return {
        "autonomy_enabled": settings.get("tier1_enabled", False),
        "envelope_summary": envelope.get("summary", "unknown"),
        "would_execute": loop_report.get("would_execute", []),
        "would_skip": loop_report.get("would_skip", []),
        "executed": cycle_result.get("executed", []),
        "skipped": cycle_result.get("skipped", []),
    }


def run_runtime_loop(
    iterations: int = 1,
    interval_seconds: float = 1.0,
) -> Dict[str, Any]:
    """
    Execute *iterations* passive cycles, sleeping *interval_seconds* between each.

    Returns a structured report with every cycle's output.  Individual cycle
    failures are caught and recorded without aborting subsequent iterations.
    """
    global _autonomy_cycle_counter, _last_autonomy_result

    if iterations < 1:
        raise ValueError(f"iterations must be >= 1, got {iterations}")
    if interval_seconds < 0.1:
        raise ValueError(f"interval_seconds must be >= 0.1, got {interval_seconds}")

    from runtime.runtime_loop_bootstrap import run_runtime_cycle_once

    results: List[Dict[str, Any]] = []

    for i in range(iterations):
        try:
            t0 = time.monotonic()
            cycle = run_runtime_cycle_once()
            dur = round(time.monotonic() - t0, 6)
            cycle["duration"] = dur
            _apply_expression_shaping(cycle)
            results.append(cycle)

            try:
                from runtime.telemetry import _TELEMETRY_BUFFER

                if _TELEMETRY_BUFFER:
                    _TELEMETRY_BUFFER[-1]["duration"] = dur
            except Exception:
                pass
        except Exception as exc:
            results.append({"status": "error", "error": str(exc)})

        # Phase 18: cadence-based Tier-1 autonomy pass
        # Phase 61: consult posture autonomy before executing
        _autonomy_cycle_counter += 1
        if _autonomy_cycle_counter % TIER1_AUTONOMY_CADENCE == 0:
            try:
                if _posture_allows_autonomy():
                    _last_autonomy_result = _run_autonomy_pass()
                else:
                    _last_autonomy_result = {
                        "autonomy_enabled": False,
                        "posture_blocked": True,
                        "reason": "active posture does not allow autonomy",
                    }
            except Exception:
                _last_autonomy_result = None
                try:
                    from runtime.autonomy_cycle_log import log_tier1_cycle
                    log_tier1_cycle(time.time(), "error", "unknown")
                except Exception:
                    pass

        if i < iterations - 1:
            time.sleep(interval_seconds)

    return {
        "status": "ok",
        "iterations": iterations,
        "interval": interval_seconds,
        "results": results,
    }
