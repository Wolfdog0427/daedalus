# runtime/system_dashboard.py
"""
Unified, read-only system health dashboard.

Composes every telemetry signal (Phases 1–4) into a single view.
No persistence, no threads, no subsystem calls, no mutation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_maintenance_envelope_summary() -> Dict[str, Any]:
    """
    Unified maintenance envelope: readiness gate + checklist in one view.

    Purely informational — NOT an autonomy signal.
    """
    try:
        from runtime.telemetry import (
            compute_maintenance_readiness,
            compute_premaintenance_checklist,
        )
    except Exception:
        return {
            "readiness_gate": {},
            "checklist": {},
            "summary": "fail",
            "reasons": ["telemetry unavailable"],
        }

    gate = compute_maintenance_readiness(50)
    checklist = compute_premaintenance_checklist(50)

    gate_level = gate.get("level", "red")
    cl_overall = checklist.get("overall", "fail")

    if gate_level == "red" or cl_overall == "fail":
        summary = "fail"
    elif gate_level == "yellow" or cl_overall == "caution":
        summary = "caution"
    else:
        summary = "pass"

    reasons: List[str] = list(gate.get("reasons") or [])
    for item in checklist.get("checklist") or []:
        if item.get("status") != "ok":
            reasons.append(f"{item.get('item', '?')}: {item.get('status', '?')} ({item.get('details', '')})")

    return {
        "readiness_gate": gate,
        "checklist": checklist,
        "summary": summary,
        "reasons": reasons,
    }


def format_maintenance_envelope_summary() -> str:
    """Human-readable maintenance envelope narrative (plain text, no ANSI)."""
    try:
        env = get_maintenance_envelope_summary()
    except Exception:
        return "Maintenance envelope unavailable."

    lines: List[str] = ["=== MAINTENANCE ENVELOPE ===", ""]

    lines.append(f"Envelope: {env.get('summary', '?')}")

    gate = env.get("readiness_gate") or {}
    lines.append(f"Readiness gate: {gate.get('level', '?')}  (ready={gate.get('ready', False)})")

    cl = env.get("checklist") or {}
    lines.append(f"Checklist: {cl.get('overall', '?')}")

    lines.append("")
    reasons = env.get("reasons") or []
    if reasons:
        lines.append("Reasons:")
        for r in reasons:
            lines.append(f"  - {r}")
    else:
        lines.append("No issues detected.")

    return "\n".join(lines)


def get_tier1_autonomy_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """Compose classification, eligibility, settings, and auto-execute verdict."""
    try:
        from runtime.maintenance_actions import (
            classify_maintenance_action,
            check_autonomy_eligibility,
            get_autonomy_settings,
            evaluate_tier1_autonomy,
        )
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    return {
        "classification": classify_maintenance_action(action),
        "eligibility": check_autonomy_eligibility(action, envelope),
        "settings": get_autonomy_settings(),
        "verdict": evaluate_tier1_autonomy(action, envelope),
    }


def get_tier1_autonomy_cycle_preview(
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Preview what a tier-1 autonomy cycle would do, without executing."""
    try:
        from runtime.maintenance_actions import (
            classify_maintenance_action,
            check_autonomy_eligibility,
            get_autonomy_settings,
            evaluate_tier1_autonomy,
        )
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    settings = get_autonomy_settings()

    per_action: List[Dict[str, Any]] = []
    would_execute: List[str] = []
    would_skip: List[str] = []

    for action in actions:
        classification = classify_maintenance_action(action)
        eligibility = check_autonomy_eligibility(action, envelope)
        verdict = evaluate_tier1_autonomy(action, envelope)

        name = action.get("name", "?")
        if verdict["should_auto_execute"]:
            would_execute.append(name)
        else:
            would_skip.append(name)

        per_action.append({
            "action": action,
            "classification": classification,
            "eligibility": eligibility,
            "verdict": verdict,
        })

    return {
        "envelope": envelope,
        "settings": settings,
        "actions": per_action,
        "would_execute": would_execute,
        "would_skip": would_skip,
    }


def get_active_tier1_autonomy_state() -> Optional[Dict[str, Any]]:
    """Return the last active autonomy cycle result from the runtime loop."""
    try:
        from runtime.runtime_loop_controller import get_last_autonomy_result

        return get_last_autonomy_result()
    except Exception:
        return None


def get_tier1_action_registry() -> List[Dict[str, Any]]:
    """Return the Tier-1 registry with per-action classification."""
    try:
        from runtime.maintenance_actions import (
            get_registered_tier1_actions,
            classify_maintenance_action,
        )

        actions = get_registered_tier1_actions()
        return [
            {
                "action": a,
                "classification": classify_maintenance_action(a),
            }
            for a in actions
        ]
    except Exception:
        return []


def get_tier1_promotion_events() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import get_tier1_promotion_events as _get

        return _get()
    except Exception:
        return []


def get_tier1_demotion_events() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import get_tier1_demotion_events as _get

        return _get()
    except Exception:
        return []


def get_tier2_action_registry() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import (
            get_registered_tier2_actions,
            classify_maintenance_action,
        )

        return [
            {"action": a, "classification": classify_maintenance_action(a)}
            for a in get_registered_tier2_actions()
        ]
    except Exception:
        return []


def get_tier2_pending_queue() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import get_tier2_pending_queue as _get

        return _get()
    except Exception:
        return []


def get_tier2_execution_events() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import get_tier2_execution_events as _get

        return _get()
    except Exception:
        return []


def get_tier2_promotion_candidates() -> List[Dict[str, Any]]:
    try:
        from runtime.maintenance_actions import get_tier2_promotion_candidates as _get

        return _get()
    except Exception:
        return []


def get_tier2_lifecycle_status() -> Dict[str, Any]:
    """Compose Tier-2 lifecycle summary from registries and event log."""
    try:
        from runtime.maintenance_actions import (
            get_registered_tier2_actions,
            get_tier2_pending_queue as _pq,
            get_tier2_execution_events as _evt,
            get_tier2_lifecycle_log,
        )

        reg = get_registered_tier2_actions()
        pq = _pq()
        evts = _evt()
        log = get_tier2_lifecycle_log()
        last_op = log[-1] if log else None

        return {
            "registry_count": len(reg),
            "pending_count": len(pq),
            "event_count": len(evts),
            "lifecycle_log_count": len(log),
            "last_operation": last_op,
        }
    except Exception:
        return {
            "registry_count": 0, "pending_count": 0,
            "event_count": 0, "lifecycle_log_count": 0,
            "last_operation": None,
        }


def get_autonomy_loop_preview(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Full autonomy-loop dry-run — no execution, no sandbox mutation."""
    try:
        from runtime.maintenance_actions import run_autonomy_loop
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    return run_autonomy_loop(actions, envelope)


def get_maintenance_action_classification(action: Dict[str, Any]) -> Dict[str, Any]:
    """Classify *action* into tier1/tier2/tier3."""
    try:
        from runtime.maintenance_actions import classify_maintenance_action

        return classify_maintenance_action(action)
    except Exception:
        return {"action": action, "class": "unknown", "reason": "unavailable"}


def get_autonomy_eligibility_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """Check whether *action* meets autonomy eligibility criteria."""
    try:
        from runtime.maintenance_actions import check_autonomy_eligibility

        envelope = get_maintenance_envelope_summary()
        return check_autonomy_eligibility(action, envelope)
    except Exception:
        return {"eligible": False, "class": "unknown", "reasons": ["unavailable"]}


def get_maintenance_operation_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full operation preview: simulation layers (Phase 12) plus a real
    sandbox operation and its rollback.

    The sandbox operation runs only when the envelope is "pass".
    All effects are confined to ``_MAINTENANCE_SANDBOX``.
    """
    try:
        from runtime.maintenance_actions import (
            validate_maintenance_action,
            dry_run_maintenance_action,
            prepare_maintenance_execution_plan,
            execute_maintenance_plan_all,
            rollback_maintenance_plan,
            perform_maintenance_operation,
            rollback_maintenance_operation,
        )
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    validation = validate_maintenance_action(action, envelope)
    dry_run = dry_run_maintenance_action(action)
    plan = prepare_maintenance_execution_plan(action)
    sim_executed = execute_maintenance_plan_all(plan)
    sim_rollback = rollback_maintenance_plan(sim_executed)

    real_result = perform_maintenance_operation(action, envelope)
    real_rollback = rollback_maintenance_operation(real_result)

    return {
        "envelope": envelope,
        "validation": validation,
        "dry_run": dry_run,
        "execution_plan": plan,
        "execution_simulation": sim_executed,
        "rollback_simulation": sim_rollback,
        "real_operation": real_result,
        "real_rollback": real_rollback,
    }


def get_maintenance_execution_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full execution simulation: envelope + validation + dry-run + plan +
    simulated execute-all + simulated rollback.

    Read-only — no real maintenance is performed.
    """
    try:
        from runtime.maintenance_actions import (
            validate_maintenance_action,
            dry_run_maintenance_action,
            prepare_maintenance_execution_plan,
            execute_maintenance_plan_all,
            rollback_maintenance_plan,
        )
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    validation = validate_maintenance_action(action, envelope)
    dry_run = dry_run_maintenance_action(action)
    plan = prepare_maintenance_execution_plan(action)
    executed = execute_maintenance_plan_all(plan)
    rolled_back = rollback_maintenance_plan(executed)

    return {
        "envelope": envelope,
        "validation": validation,
        "dry_run": dry_run,
        "execution_plan": plan,
        "execution_simulation": executed,
        "rollback_simulation": rolled_back,
    }


def get_maintenance_action_preview(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose envelope, validation, dry-run, and execution plan for *action*.

    Read-only preview — no maintenance is performed.
    """
    try:
        from runtime.maintenance_actions import (
            validate_maintenance_action,
            dry_run_maintenance_action,
            prepare_maintenance_execution_plan,
        )
    except Exception:
        return {"error": "maintenance_actions module unavailable"}

    envelope = get_maintenance_envelope_summary()
    validation = validate_maintenance_action(action, envelope)
    dry_run = dry_run_maintenance_action(action)
    plan = prepare_maintenance_execution_plan(action)

    return {
        "envelope": envelope,
        "validation": validation,
        "dry_run": dry_run,
        "execution_plan": plan,
    }


def get_system_dashboard() -> Dict[str, Any]:
    """Single dict containing all telemetry-derived signals."""
    try:
        from runtime.telemetry import (
            get_recent_telemetry,
            compute_error_rate,
            compute_stability_signal,
            compute_sho_trend,
            compute_system_health,
            compute_readiness_level,
            compute_cycle_durations,
            compute_runtime_drift,
            compute_integrity_flags,
            compute_degradation_level,
            compute_maintenance_readiness,
            compute_premaintenance_checklist,
        )
    except Exception:
        return {
            "latest_cycle": None,
            "recent_cycles": [],
            "error_rates": {},
            "stability": {},
            "sho_trend": {},
            "system_health": {},
            "readiness": {},
            "cycle_durations": {},
            "runtime_drift": {},
            "integrity_flags": {},
            "degradation": {},
            "maintenance_readiness": {},
            "premaintenance_checklist": {},
            "maintenance_envelope": {},
            "maintenance_action_preview": None,
            "maintenance_execution_preview": None,
            "maintenance_operation_preview": None,
            "maintenance_action_classification": None,
            "autonomy_eligibility_preview": None,
            "tier1_autonomy_preview": None,
            "tier1_autonomy_cycle_preview": None,
            "autonomy_loop_preview": None,
            "active_tier1_autonomy": None,
            "tier1_action_registry": [],
            "tier1_promotion_events": [],
            "tier1_demotion_events": [],
            "tier2_action_registry": [],
            "tier2_pending_queue": [],
            "tier2_execution_events": [],
            "tier2_promotion_candidates": [],
            "tier2_lifecycle": {},
            "system_settings": {},
            "tier1_cycle_log": [],
            "tier1_next_cycle_eta": None,
            "autonomy_drift": {},
            "tier3_proposals": [],
            "tier3_execution_log": [],
            "tier3_action_types": {},
            "tier3_last_dispatch": None,
            "tier3_reversible_ledger": [],
            "tier3_migrations": [],
            "tier3_pending_approvals": [],
            "tier3_dryruns": [],
            "tier3_plans": [],
            "tier3_policies": [],
            "tier3_policy_scheduling": [],
            "tier3_adaptive_insights": [],
            "tier3_adaptive_recommendations": [],
        }

    recent_50 = get_recent_telemetry(50)
    recent_10 = recent_50[-10:] if len(recent_50) >= 10 else list(recent_50)
    latest = recent_50[-1] if recent_50 else None

    return {
        "latest_cycle": latest,
        "recent_cycles": recent_10,
        "error_rates": compute_error_rate(50),
        "stability": compute_stability_signal(50),
        "sho_trend": compute_sho_trend(20),
        "system_health": compute_system_health(50),
        "readiness": compute_readiness_level(50),
        "cycle_durations": compute_cycle_durations(50),
        "runtime_drift": compute_runtime_drift(50),
        "integrity_flags": compute_integrity_flags(50),
        "degradation": compute_degradation_level(50),
        "maintenance_readiness": compute_maintenance_readiness(50),
        "premaintenance_checklist": compute_premaintenance_checklist(50),
        "maintenance_envelope": get_maintenance_envelope_summary(),
        "maintenance_action_preview": None,
        "maintenance_execution_preview": None,
        "maintenance_operation_preview": None,
        "maintenance_action_classification": None,
        "autonomy_eligibility_preview": None,
        "tier1_autonomy_preview": None,
        "tier1_autonomy_cycle_preview": None,
        "autonomy_loop_preview": None,
        "active_tier1_autonomy": get_active_tier1_autonomy_state(),
        "tier1_action_registry": get_tier1_action_registry(),
        "tier1_promotion_events": get_tier1_promotion_events(),
        "tier1_demotion_events": get_tier1_demotion_events(),
        "tier2_action_registry": get_tier2_action_registry(),
        "tier2_pending_queue": get_tier2_pending_queue(),
        "tier2_execution_events": get_tier2_execution_events(),
        "tier2_promotion_candidates": get_tier2_promotion_candidates(),
        "tier2_lifecycle": get_tier2_lifecycle_status(),
        "system_settings": _get_system_settings_safe(),
        "tier1_cycle_log": _get_tier1_cycle_log_safe(),
        "tier1_next_cycle_eta": _get_next_cycle_eta_safe(),
        "autonomy_drift": _get_autonomy_drift_safe(),
        "tier3_proposals": _get_tier3_proposals_safe(),
        "tier3_execution_log": _get_tier3_execution_log_safe(),
        "tier3_action_types": _get_tier3_action_types_safe(),
        "tier3_last_dispatch": _get_tier3_last_dispatch_safe(),
        "tier3_reversible_ledger": _get_tier3_reversible_ledger_safe(),
        "tier3_migrations": _get_tier3_migrations_safe(),
        "tier3_pending_approvals": _get_tier3_pending_approvals_safe(),
        "tier3_dryruns": _get_tier3_dryruns_safe(),
        "tier3_plans": _get_tier3_plans_safe(),
        "tier3_policies": _get_tier3_policies_safe(),
        "tier3_policy_scheduling": _get_tier3_policy_scheduling_safe(),
        "tier3_adaptive_insights": _get_tier3_adaptive_insights_safe(),
        "tier3_adaptive_recommendations": _get_tier3_adaptive_recommendations_safe(),
        "tier3_governance_profiles": _get_tier3_governance_profiles_safe(),
        "tier3_runbooks": _get_tier3_runbooks_safe(),
        "tier3_templates_and_scenarios": _get_tier3_templates_and_scenarios_safe(),
        "tier3_environments": _get_tier3_environments_safe(),
        "tier3_environment_promotion": _get_tier3_promotion_safe(),
        "tier3_envpacks": _get_tier3_envpacks_safe(),
        "tier3_env_health_drift": _get_tier3_env_health_drift_safe(),
        "tier3_promotion_readiness_guardrails": _get_tier3_readiness_guardrails_safe(),
        "tier3_multi_env": _get_tier3_multi_env_safe(),
        "tier3_snapshots_audits": _get_tier3_snapshots_audits_safe(),
        "tier3_forecasting_anomalies": _get_tier3_forecasting_anomalies_safe(),
        "tier3_strategic_modeling": _get_tier3_strategic_modeling_safe(),
        "tier3_governance_planning": _get_tier3_governance_planning_safe(),
        "tier3_scorecards_kpis": _get_tier3_scorecards_kpis_safe(),
        "tier3_sla_risk_exec": _get_tier3_sla_risk_exec_safe(),
        "tier3_benchmarking_maturity": _get_tier3_benchmarking_maturity_safe(),
        "tier3_meta_governance": _get_tier3_meta_governance_safe(),
        "tier3_personas_envelopes": _get_tier3_personas_envelopes_safe(),
        "runtime_posture": _get_runtime_posture_safe(),
        "expression_framework": _get_expression_framework_safe(),
        "autonomy_tiers": _get_autonomy_tiers_safe(),
        "operator_interaction": _get_operator_interaction_safe(),
        "identity_continuity": _get_identity_continuity_safe(),
        "identity_coherence": _get_identity_coherence_safe(),
        "expressive_stability": _get_expressive_stability_safe(),
        "expressive_resonance": _get_expressive_resonance_safe(),
        "governance": _get_governance_safe(),
        "identity_introspection": _get_identity_introspection_safe(),
    }


def _get_identity_introspection_safe() -> Dict[str, Any]:
    try:
        from runtime.self_description import describe_current_state
        return describe_current_state()
    except Exception:
        return {}


def _get_governance_safe() -> Dict[str, Any]:
    try:
        from governance.kernel import get_kernel_state
        from governance.drift_detector import compute_drift_report
        from governance.proposal_engine import get_proposals
        from governance.patch_lifecycle import get_patches
        from governance.audit_log import get_log_summary
        from governance.change_contracts import get_contract_log

        return {
            "kernel_state": get_kernel_state(),
            "drift_report": compute_drift_report(),
            "proposals": get_proposals(limit=5),
            "patches": get_patches(limit=5),
            "audit_summary": get_log_summary(),
            "contract_log": get_contract_log(5),
        }
    except Exception:
        return {}


def _get_expressive_resonance_safe() -> Dict[str, Any]:
    try:
        from runtime.resonance_engine import resonance_summary, get_resonance_log
        return {
            "summary": resonance_summary(),
            "recent_log": get_resonance_log(5),
        }
    except Exception:
        return {}


def _get_expressive_stability_safe() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state, get_stability_log
        from runtime.long_arc_engine import long_arc_summary, get_smoothing_log
        return {
            "stability_state": get_stability_state(),
            "long_arc_summary": long_arc_summary(),
            "recent_stability": get_stability_log(5),
            "recent_smoothing": get_smoothing_log(5),
        }
    except Exception:
        return {}


def _get_identity_coherence_safe() -> Dict[str, Any]:
    try:
        from runtime.identity_coherence import get_coherence_summary, get_coherence_log
        from runtime.self_alignment_engine import get_alignment_summary, get_alignment_log
        return {
            "coherence_summary": get_coherence_summary(),
            "alignment_summary": get_alignment_summary(),
            "recent_coherence": get_coherence_log(5),
            "recent_alignment": get_alignment_log(5),
        }
    except Exception:
        return {}


def _get_identity_continuity_safe() -> Dict[str, Any]:
    try:
        from runtime.session_continuity import get_continuity_state, get_continuity_log
        from runtime.identity_continuity_engine import (
            continuity_summary, get_continuity_shaped_log,
        )
        return {
            "state": get_continuity_state(),
            "engine_summary": continuity_summary(),
            "recent_log": get_continuity_log(5),
            "recent_shaped": get_continuity_shaped_log(5),
        }
    except Exception:
        return {}


def _get_operator_interaction_safe() -> Dict[str, Any]:
    try:
        from runtime.operator_context import get_context, get_context_log
        from runtime.interaction_model import get_interaction_summary, get_interaction_log
        return {
            "operator_context": get_context(),
            "interaction_summary": get_interaction_summary(),
            "recent_context_events": get_context_log(5),
            "recent_interactions": get_interaction_log(5),
        }
    except Exception:
        return {}


def _get_autonomy_tiers_safe() -> Dict[str, Any]:
    try:
        from runtime.autonomy_engine import get_effective_tier, explain_tier, get_transition_log
        return {
            "effective_tier": get_effective_tier(),
            "explanation": explain_tier(),
            "recent_transitions": get_transition_log(5),
        }
    except Exception:
        return {}


def _get_expression_framework_safe() -> Dict[str, Any]:
    try:
        from runtime.posture_expression import get_expression_profile
        from runtime.interaction_cycle import get_cycle_state, get_cycle_log
        from runtime.expression_engine import get_shaped_response_log
        return {
            "profile": get_expression_profile(),
            "cycle_state": get_cycle_state(),
            "recent_cycle_events": get_cycle_log(5),
            "recent_shaped": get_shaped_response_log(5),
        }
    except Exception:
        return {}


def _get_runtime_posture_safe() -> Dict[str, Any]:
    try:
        from runtime.posture_engine import get_active_posture, explain_posture, get_transition_log
        current = get_active_posture()
        explanation = explain_posture()
        transitions = get_transition_log(5)
        return {
            "current": current,
            "explanation": explanation,
            "recent_transitions": transitions,
        }
    except Exception:
        return {}


def _get_tier3_personas_envelopes_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_personas import get_persona_registry
        from runtime.tier3_modes import get_mode_registry
        from runtime.tier3_envelope import get_envelope_log
        return {
            "personas": get_persona_registry(10),
            "modes": get_mode_registry(10),
            "recent_envelopes": get_envelope_log(5),
        }
    except Exception:
        return {}


def _get_tier3_meta_governance_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_objectives import get_objective_registry
        from runtime.tier3_alignment import get_alignment_log
        from runtime.tier3_meta_model import get_meta_model_log
        return {
            "objectives": get_objective_registry(10),
            "recent_alignments": get_alignment_log(5),
            "recent_meta_models": get_meta_model_log(5),
        }
    except Exception:
        return {}


def _get_tier3_benchmarking_maturity_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_benchmark import get_benchmark_log
        from runtime.tier3_maturity import get_maturity_log
        from runtime.tier3_comparison import get_comparison_log
        return {
            "recent_benchmarks": get_benchmark_log(5),
            "recent_maturity": get_maturity_log(5),
            "recent_comparisons": get_comparison_log(5),
        }
    except Exception:
        return {}


def _get_tier3_sla_risk_exec_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_sla import get_sla_log
        from runtime.tier3_risk import get_risk_log
        from runtime.tier3_heatmap import get_heatmap_log
        from runtime.tier3_exec_report import get_exec_report_log
        return {
            "recent_sla": get_sla_log(5),
            "recent_risk": get_risk_log(5),
            "recent_heatmaps": get_heatmap_log(3),
            "recent_exec_reports": get_exec_report_log(3),
        }
    except Exception:
        return {}


def _get_tier3_scorecards_kpis_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_kpis import get_kpi_log
        from runtime.tier3_scorecards import get_scorecard_log
        from runtime.tier3_strategic_dashboard import get_strategic_dashboard_log
        return {
            "recent_kpis": get_kpi_log(5),
            "recent_scorecards": get_scorecard_log(5),
            "recent_dashboards": get_strategic_dashboard_log(3),
        }
    except Exception:
        return {}


def _get_tier3_governance_planning_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_planning import get_planning_log, get_plan_registry
        from runtime.tier3_planning_sim import get_plan_sim_log
        plans = get_plan_registry(5)
        plan_summaries = []
        for p in plans:
            plan_summaries.append({
                "plan_id": p["plan_id"],
                "scope": p.get("scope", "?"),
                "n_phases": len(p.get("phases", [])),
                "confidence": p.get("confidence", "?"),
                "timestamp": p.get("timestamp", 0),
            })
        return {
            "recent_plans": plan_summaries,
            "recent_planning_activity": get_planning_log(5),
            "recent_plan_simulations": get_plan_sim_log(5),
        }
    except Exception:
        return {}


def _get_tier3_strategic_modeling_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_strategy import get_strategy_log
        from runtime.tier3_scenario_sim import get_simulation_log
        return {
            "recent_strategy": get_strategy_log(5),
            "recent_simulations": get_simulation_log(5),
        }
    except Exception:
        return {}


def _get_tier3_forecasting_anomalies_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_forecast import get_forecast_log
        from runtime.tier3_anomaly import (
            get_anomaly_registry, get_governance_insights,
        )
        return {
            "recent_forecasts": get_forecast_log(5),
            "recent_anomalies": get_anomaly_registry(5),
            "recent_insights": get_governance_insights(5),
        }
    except Exception:
        return {}


def _get_tier3_snapshots_audits_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_snapshots import list_snapshots
        from runtime.tier3_snapshot_diff import get_diff_log
        from runtime.tier3_audit import get_audit_log
        return {
            "snapshots": list_snapshots()[-5:],
            "recent_diffs": get_diff_log(5),
            "recent_audits": get_audit_log(5),
        }
    except Exception:
        return {}


def _get_tier3_multi_env_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_multi_env import get_multi_env_log
        from runtime.tier3_lineage import get_lineage_log
        return {
            "recent_multi_env": get_multi_env_log(5),
            "recent_lineage": get_lineage_log(10),
        }
    except Exception:
        return {}


def _get_tier3_readiness_guardrails_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_env_health import get_readiness_log
        from runtime.tier3_env_guardrails import get_guardrail_log
        return {
            "recent_readiness": get_readiness_log(5),
            "recent_guardrails": get_guardrail_log(5),
        }
    except Exception:
        return {}


def _get_tier3_env_health_drift_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_env_health import get_health_log
        from runtime.tier3_env_drift import get_drift_log
        return {
            "recent_health": get_health_log(5),
            "recent_drift": get_drift_log(5),
        }
    except Exception:
        return {}


def _get_tier3_envpacks_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_envpacks import list_envpacks, get_pack_application_log
        from runtime.tier3_environments import list_environments
        packs = list_envpacks()
        env_packs = []
        for e in list_environments():
            applied = e.get("applied_pack_ids") or []
            if applied:
                env_packs.append({
                    "env_id": e["env_id"],
                    "env_name": e["name"],
                    "applied_pack_ids": applied,
                    "default_policies": len(e.get("default_policy_ids", [])),
                    "default_flags": e.get("default_feature_flags", {}),
                })
        return {
            "packs": packs,
            "env_pack_mappings": env_packs,
            "recent_applications": get_pack_application_log(5),
        }
    except Exception:
        return {}


def _get_tier3_promotion_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_promotion import get_promotion_log
        from runtime.tier3_environments import list_environments
        envs = list_environments()
        relations = [
            {"env_id": e["env_id"], "name": e["name"],
             "upstream": e.get("upstream_env_id"),
             "downstream": e.get("downstream_env_ids") or []}
            for e in envs
            if e.get("upstream_env_id") or e.get("downstream_env_ids")
        ]
        return {
            "relations": relations,
            "recent_log": get_promotion_log(5),
        }
    except Exception:
        return {}


def _get_tier3_environments_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_environments import (
            get_active_environment, list_environments, get_env_activation_log,
        )
        active = get_active_environment()
        return {
            "active_environment": active,
            "total_environments": len(list_environments()),
            "recent_activations": get_env_activation_log(5),
        }
    except Exception:
        return {}


def _get_tier3_templates_and_scenarios_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_runbook_templates import list_templates, get_instantiation_log
        from runtime.tier3_scenarios import list_scenarios
        return {
            "templates": list_templates(),
            "scenarios": list_scenarios(),
            "recent_instantiations": get_instantiation_log(5),
        }
    except Exception:
        return {}


def _get_tier3_runbooks_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_runbooks import list_runbooks
        return list_runbooks()
    except Exception:
        return []


def _get_tier3_governance_profiles_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_profiles import (
            get_active_profile, list_profiles, get_activation_log,
        )
        active = get_active_profile()
        return {
            "active_profile": active,
            "total_profiles": len(list_profiles()),
            "recent_activations": get_activation_log(5),
        }
    except Exception:
        return {}


def _get_tier3_adaptive_recommendations_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_adaptive_bridge import get_applied_recommendations

        return get_applied_recommendations(5)
    except Exception:
        return []


def _get_tier3_adaptive_insights_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_adaptive import get_insights

        return get_insights(5)
    except Exception:
        return []


def _get_tier3_policy_scheduling_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_policies import get_policies, get_next_eligible_time

        result = []
        for p in get_policies()[-5:]:
            result.append({
                "policy_id": p.get("policy_id", "?"),
                "name": p.get("name", "?"),
                "enabled": p.get("enabled", False),
                "evaluation_interval_seconds": p.get("evaluation_interval_seconds"),
                "allowed_windows": p.get("allowed_windows") or [],
                "last_evaluated_at": p.get("last_evaluated_at"),
                "next_eligible": get_next_eligible_time(p),
                "rate_limit": p.get("rate_limit"),
                "trigger_count": len(p.get("trigger_count_window") or []),
            })
        return result
    except Exception:
        return []


def _get_tier3_policies_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_policies import get_policies

        return get_policies()[-5:]
    except Exception:
        return []


def _get_tier3_plans_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_plans import get_plans

        return get_plans()[-5:]
    except Exception:
        return []


def _get_tier3_pending_approvals_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_proposals import get_proposals_awaiting_approval

        return get_proposals_awaiting_approval()
    except Exception:
        return []


def _get_tier3_dryruns_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_execution import get_tier3_dryrun_log

        return get_tier3_dryrun_log(5)
    except Exception:
        return []


def _get_tier3_migrations_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_execution import get_tier3_migration_log

        return get_tier3_migration_log(5)
    except Exception:
        return []


def _get_tier3_reversible_ledger_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_execution import get_tier3_reversible_ledger

        return get_tier3_reversible_ledger(5)
    except Exception:
        return []


def _get_tier3_last_dispatch_safe() -> Optional[Dict[str, Any]]:
    try:
        from runtime.tier3_execution import get_last_tier3_dispatch

        return get_last_tier3_dispatch()
    except Exception:
        return None


def _get_tier3_action_types_safe() -> Dict[str, Any]:
    try:
        from runtime.tier3_actions import get_tier3_action_types

        return get_tier3_action_types()
    except Exception:
        return {}


def _get_tier3_execution_log_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_execution import get_tier3_execution_log

        return get_tier3_execution_log()
    except Exception:
        return []


def _get_tier3_proposals_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.tier3_proposals import get_tier3_proposals

        return get_tier3_proposals()
    except Exception:
        return []


def _get_autonomy_drift_safe() -> Dict[str, Any]:
    try:
        from runtime.autonomy_cycle_log import get_autonomy_drift_report

        return get_autonomy_drift_report()
    except Exception:
        return {}


def _get_tier1_cycle_log_safe() -> List[Dict[str, Any]]:
    try:
        from runtime.autonomy_cycle_log import get_tier1_cycle_log

        return get_tier1_cycle_log()
    except Exception:
        return []


def _get_next_cycle_eta_safe() -> Optional[int]:
    try:
        from runtime.runtime_loop_controller import get_cycles_until_next_autonomy

        return get_cycles_until_next_autonomy()
    except Exception:
        return None


def _get_system_settings_safe() -> Dict[str, Any]:
    try:
        from runtime.system_settings import get_system_settings

        return get_system_settings()
    except Exception:
        return {}


def format_system_dashboard() -> str:
    """Human-readable dashboard (plain text, no ANSI)."""
    try:
        dash = get_system_dashboard()
    except Exception:
        return "System dashboard unavailable."

    lines: List[str] = ["=== SYSTEM DASHBOARD ===", ""]

    latest = dash.get("latest_cycle")
    if latest:
        lines.append(f"Latest cycle: {latest.get('timestamp')}")
        subs = latest.get("subsystems") or {}
        for k, v in subs.items():
            lines.append(f"  {k}: {v}")
    else:
        lines.append("No telemetry records.")

    lines.append("")
    rates = (dash.get("error_rates") or {}).get("rates") or {}
    window = (dash.get("error_rates") or {}).get("window", "?")
    lines.append(f"Error rates (last {window} cycles):")
    for k, v in rates.items():
        lines.append(f"  {k}: {v:.1%}")

    lines.append("")
    stab = dash.get("stability") or {}
    label = "STABLE" if stab.get("stable") else "UNSTABLE"
    lines.append(
        f"Stability: {label}  "
        f"(error-free {stab.get('error_free_cycles', '?')}"
        f"/{stab.get('total_cycles', '?')} cycles)"
    )

    sho = dash.get("sho_trend") or {}
    lines.append(
        f"SHO trend: {sho.get('trend', '?')}  "
        f"(ok={sho.get('sho_ok', '?')} err={sho.get('sho_error', '?')})"
    )

    lines.append("")
    health = dash.get("system_health") or {}
    lines.append(f"System health: {health.get('overall', '?')}")

    rd = dash.get("readiness") or {}
    lines.append(
        f"Readiness: level {rd.get('level', '?')} — {rd.get('description', '?')}"
    )

    lines.append("")
    cd = dash.get("cycle_durations") or {}
    lines.append(
        f"Cycle durations (last {cd.get('window', '?')} cycles):  "
        f"avg={cd.get('avg', '?')}s  min={cd.get('min', '?')}s  max={cd.get('max', '?')}s"
    )

    drift = dash.get("runtime_drift") or {}
    lines.append(f"Runtime drift: {drift.get('drift', '?')}")

    lines.append("")
    iflags = (dash.get("integrity_flags") or {}).get("flags") or {}
    active = [k for k, v in iflags.items() if v]
    lines.append(f"Integrity flags: {', '.join(active) if active else 'none'}")

    deg = dash.get("degradation") or {}
    lines.append(
        f"Degradation: level {deg.get('level', '?')} — {deg.get('description', '?')}"
    )

    lines.append("")
    mr = dash.get("maintenance_readiness") or {}
    gate = mr.get("level", "?")
    ready = mr.get("ready", False)
    lines.append(f"Maintenance gate: {gate}  (ready={ready})")
    for reason in mr.get("reasons") or []:
        lines.append(f"  - {reason}")

    lines.append("")
    pc = dash.get("premaintenance_checklist") or {}
    lines.append(f"Pre-maintenance checklist: {pc.get('overall', '?')}")
    for item in pc.get("checklist") or []:
        lines.append(f"  [{item.get('status', '?'):4s}] {item.get('item', '?')}  ({item.get('details', '')})")

    lines.append("")
    env = dash.get("maintenance_envelope") or {}
    lines.append(f"Maintenance envelope: {env.get('summary', '?')}")
    for r in env.get("reasons") or []:
        lines.append(f"  - {r}")

    cls = dash.get("maintenance_action_classification") or {}
    if cls:
        lines.append("")
        lines.append(f"Action classification: {cls.get('class', '?')}")
        lines.append(f"  reason: {cls.get('reason', '?')}")

    elig = dash.get("autonomy_eligibility_preview") or {}
    if elig:
        lines.append("")
        lines.append(f"Autonomy eligibility: eligible={elig.get('eligible', '?')}  class={elig.get('class', '?')}")
        for r in elig.get("reasons") or []:
            lines.append(f"  - {r}")

    t1 = dash.get("tier1_autonomy_preview") or {}
    if t1:
        verdict = t1.get("verdict") or {}
        settings = t1.get("settings") or {}
        lines.append("")
        lines.append(f"Tier-1 autonomy: enabled={settings.get('tier1_enabled', '?')}  "
                      f"should_auto_execute={verdict.get('should_auto_execute', '?')}")
        for r in verdict.get("reasons") or []:
            lines.append(f"  - {r}")

    cyc = dash.get("tier1_autonomy_cycle_preview") or {}
    if cyc:
        lines.append("")
        lines.append(f"Tier-1 autonomy cycle: "
                      f"would_execute={cyc.get('would_execute', [])}  "
                      f"would_skip={cyc.get('would_skip', [])}")
        for entry in cyc.get("actions") or []:
            v = entry.get("verdict") or {}
            a = entry.get("action") or {}
            lines.append(f"  {a.get('name', '?')}: "
                          f"class={v.get('class', '?')}  "
                          f"auto_execute={v.get('should_auto_execute', '?')}")

    aloop = dash.get("autonomy_loop_preview") or {}
    if aloop and not aloop.get("error"):
        lines.append("")
        lines.append(f"Autonomy loop: enabled={aloop.get('autonomy_enabled', '?')}  "
                      f"envelope={aloop.get('envelope_summary', '?')}")
        lines.append(f"  would_execute: {aloop.get('would_execute', [])}")
        lines.append(f"  would_skip:    {aloop.get('would_skip', [])}")
        for entry in aloop.get("actions") or []:
            a = entry.get("action") or {}
            c = entry.get("classification") or {}
            v = entry.get("verdict") or {}
            lines.append(f"  {a.get('name', '?')}: "
                          f"class={c.get('class', '?')}  "
                          f"eligible={v.get('eligible', '?')}  "
                          f"auto_execute={v.get('should_auto_execute', '?')}")

    reg = dash.get("tier1_action_registry") or []
    if reg:
        lines.append("")
        lines.append(f"Registered Tier-1 actions ({len(reg)}):")
        for entry in reg:
            a = entry.get("action") or {}
            c = entry.get("classification") or {}
            steps = a.get("steps") or []
            lines.append(f"  {a.get('name', '?')} ({len(steps)} steps)  "
                          f"class={c.get('class', '?')}")

    promo = dash.get("tier1_promotion_events") or []
    demo = dash.get("tier1_demotion_events") or []
    if promo or demo:
        lines.append("")
        lines.append(f"Tier-1 promotion/demotion events ({len(promo)} promotions, {len(demo)} demotions):")
        for evt in (promo + demo)[-10:]:
            lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                          f"{evt.get('reason', '?')}")

    t2reg = dash.get("tier2_action_registry") or []
    if t2reg:
        lines.append("")
        lines.append(f"Registered Tier-2 actions ({len(t2reg)}):")
        for entry in t2reg:
            a = entry.get("action") or {}
            steps = a.get("steps") or []
            lines.append(f"  {a.get('name', '?')} ({len(steps)} steps)")

    t2q = dash.get("tier2_pending_queue") or []
    if t2q:
        lines.append("")
        lines.append(f"Tier-2 pending queue ({len(t2q)}):")
        for a in t2q:
            lines.append(f"  {a.get('name', '?')}")

    t2evt = dash.get("tier2_execution_events") or []
    if t2evt:
        lines.append("")
        lines.append(f"Tier-2 execution events ({len(t2evt)}):")
        for evt in t2evt[-10:]:
            lines.append(f"  [{evt.get('result', '?')}] {evt.get('action_name', '?')}: "
                          f"{evt.get('reason', '?')}")

    t2pc = dash.get("tier2_promotion_candidates") or []
    if t2pc:
        lines.append("")
        lines.append(f"Tier-2 promotion candidates ({len(t2pc)}):")
        for c in t2pc:
            lines.append(f"  {c.get('name', '?')}:  "
                          f"runs={c.get('total_runs', 0)} "
                          f"(ok={c.get('successful_runs', 0)} "
                          f"fail={c.get('failed_runs', 0)})  "
                          f"last={c.get('last_result', '?')}  "
                          f"-> {c.get('recommendation', '?')}")

    lc = dash.get("tier2_lifecycle") or {}
    if lc:
        lines.append("")
        lines.append(f"Tier-2 lifecycle: "
                      f"registry={lc.get('registry_count', 0)}  "
                      f"pending={lc.get('pending_count', 0)}  "
                      f"events={lc.get('event_count', 0)}  "
                      f"ops={lc.get('lifecycle_log_count', 0)}")
        last_op = lc.get("last_operation")
        if last_op:
            lines.append(f"  last: [{last_op.get('result', '?')}] "
                          f"{last_op.get('operation', '?')} "
                          f"{last_op.get('action_name', '?')}: "
                          f"{last_op.get('reason', '?')}")

    ss = dash.get("system_settings") or {}
    if ss:
        lines.append("")
        lines.append("Runtime settings:")
        for k, v in ss.items():
            lines.append(f"  {k}: {v}")

    t1cl = dash.get("tier1_cycle_log") or []
    if t1cl:
        lines.append("")
        lines.append(f"Tier-1 cycle history (last {len(t1cl)}):")
        for entry in t1cl:
            ts = entry.get("timestamp", 0)
            lines.append(f"  t={ts:.1f}  result={entry.get('result', '?')}  "
                          f"envelope={entry.get('envelope', '?')}")

    eta = dash.get("tier1_next_cycle_eta")
    if eta is not None:
        lines.append("")
        lines.append(f"Next Tier-1 autonomy cycle in {eta} loop iteration(s).")

    adrift = dash.get("autonomy_drift") or {}
    if adrift:
        lines.append("")
        lines.append("Autonomy drift:")
        sr = adrift.get("skip_rate") or {}
        lines.append(f"  skip rate: {sr.get('skip_rate', 0):.1%}  "
                      f"({sr.get('skip_count', 0)}/{sr.get('total_count', 0)})  "
                      f"severity={sr.get('severity', '?')}")
        es = adrift.get("envelope_stability") or {}
        lines.append(f"  envelope stability: {es.get('fail_rate', 0):.1%} non-pass  "
                      f"({es.get('fail_count', 0)}/{es.get('total_count', 0)})  "
                      f"severity={es.get('severity', '?')}")
        cd = adrift.get("cadence_drift") or {}
        lines.append(f"  cadence drift: avg_delta={cd.get('avg_delta', 0)}s  "
                      f"expected={cd.get('expected', '?')}s  "
                      f"drift={cd.get('drift', 0)}s  "
                      f"severity={cd.get('severity', '?')}")

    t3at = dash.get("tier3_action_types") or {}
    if t3at:
        lines.append("")
        lines.append(f"Tier-3 action types ({len(t3at)}):")
        for name, spec in t3at.items():
            rev = "reversible" if spec.get("reversible") else "irreversible"
            lines.append(f"  {name}: {spec.get('description', '?')} ({rev})")

    t3p = dash.get("tier3_proposals") or []
    if t3p:
        lines.append("")
        lines.append(f"Tier-3 proposals ({len(t3p)}):")
        for p in t3p:
            pid = p.get("id", "?")[:8]
            at = p.get("action_type", "")
            suffix = f"  type={at}" if at else ""
            lines.append(f"  [{p.get('status', '?')}] {pid}..  "
                          f"{p.get('title', '?')}{suffix}")

    t3x = dash.get("tier3_execution_log") or []
    if t3x:
        lines.append("")
        lines.append(f"Tier-3 execution log ({len(t3x)}):")
        for entry in t3x:
            pid = entry.get("proposal_id", "?")[:8]
            lines.append(f"  {pid}..  t={entry.get('timestamp', 0):.1f}  "
                          f"{entry.get('note', '')}")

    t3ld = dash.get("tier3_last_dispatch")
    if t3ld:
        lines.append("")
        rev = "reversible" if t3ld.get("reversible") else "irreversible"
        lines.append(f"Last Tier-3 dispatch: "
                      f"type={t3ld.get('action_type', '?')}  "
                      f"({rev})  "
                      f"t={t3ld.get('timestamp', 0):.1f}")
        hr = t3ld.get("handler_result") or {}
        if hr.get("intent"):
            lines.append(f"  intent: {hr['intent']}")

    t3rl = dash.get("tier3_reversible_ledger") or []
    if t3rl:
        lines.append("")
        lines.append(f"Tier-3 reversible ledger (last {len(t3rl)}):")
        for le in t3rl:
            rev = "reversible" if le.get("reversible") else "irreversible"
            pid = le.get("proposal_id", "?")[:8]
            lines.append(f"  {pid}..  {le.get('action_type', '?')}  "
                          f"({rev})  t={le.get('timestamp', 0):.1f}")
            old = le.get("old_values") or {}
            new = le.get("new_values") or {}
            if old:
                lines.append(f"    old: {old}")
            if new:
                lines.append(f"    new: {new}")

    t3m = dash.get("tier3_migrations") or []
    if t3m:
        lines.append("")
        lines.append(f"Tier-3 migrations (last {len(t3m)}):")
        for m in t3m:
            lines.append(
                f"  {m.get('migration_name', '?')}  "
                f"status={m.get('status', '?')}  "
                f"steps={m.get('steps_succeeded', 0)}/{m.get('total_steps', 0)}  "
                f"t={m.get('timestamp', 0):.1f}"
            )

    t3pa = dash.get("tier3_pending_approvals") or []
    if t3pa:
        lines.append("")
        lines.append(f"Tier-3 migration approvals ({len(t3pa)}):")
        for p in t3pa:
            pid = p.get("id", "?")[:8]
            dr = p.get("dryrun") or {}
            name = (p.get("payload") or {}).get("migration_name", "?")
            lines.append(f"  {pid}..  {p.get('title', '?')}  "
                          f"migration={name}  dryrun={dr.get('status', '?')}")
            for sd in (dr.get("step_diffs") or []):
                d = sd.get("diff")
                if d:
                    lines.append(f"    [{sd.get('index')}] {sd.get('step_type')}: "
                                  f"{d.get('before')} -> {d.get('after')}")

    t3dr = dash.get("tier3_dryruns") or []
    if t3dr:
        lines.append("")
        lines.append(f"Tier-3 dry-runs (last {len(t3dr)}):")
        for dr in t3dr:
            lines.append(
                f"  {dr.get('migration_name', '?')}  "
                f"status={dr.get('status', '?')}  "
                f"steps={dr.get('steps_evaluated', 0)}/{dr.get('total_steps', 0)}  "
                f"t={dr.get('timestamp', 0):.1f}"
            )

    t3pl = dash.get("tier3_plans") or []
    if t3pl:
        lines.append("")
        lines.append(f"Tier-3 execution plans ({len(t3pl)}):")
        for pl in t3pl:
            pr = pl.get("proposal_results") or {}
            succeeded = sum(1 for r in pr.values() if r.get("status") == "success")
            failed_c = sum(1 for r in pr.values() if r.get("status") == "failed")
            skipped_c = sum(1 for r in pr.values() if r.get("status") == "skipped")
            total = len(pl.get("proposal_ids", []))
            lines.append(
                f"  {pl.get('plan_id', '?')[:8]}..  {pl.get('name', '?')}  "
                f"status={pl.get('status', '?')}  "
                f"proposals={total}  "
                f"ok={succeeded} fail={failed_c} skip={skipped_c}"
            )

    t3pol = dash.get("tier3_policies") or []
    if t3pol:
        lines.append("")
        lines.append(f"Tier-3 policies ({len(t3pol)}):")
        for pol in t3pol:
            flag = "ON" if pol.get("enabled") else "OFF"
            last_result = pol.get("last_eval_result") or "never"
            last_time = pol.get("last_eval_time")
            t_str = f"t={last_time:.1f}" if last_time else "t=never"
            lines.append(
                f"  {pol.get('policy_id', '?')[:8]}..  {pol.get('name', '?')}  "
                f"[{flag}]  last={last_result}  "
                f"proposals={pol.get('proposals_generated', 0)}  "
                f"plans={pol.get('plans_generated', 0)}  "
                f"{t_str}"
            )

    t3ps = dash.get("tier3_policy_scheduling") or []
    if t3ps:
        lines.append("")
        lines.append(f"Tier-3 policy scheduling ({len(t3ps)}):")
        for ps in t3ps:
            pid = ps.get("policy_id", "?")[:8]
            flag = "ON" if ps.get("enabled") else "OFF"
            iv = ps.get("evaluation_interval_seconds")
            iv_str = f"{iv}s" if iv else "none"
            last = ps.get("last_evaluated_at")
            last_str = f"{last:.1f}" if last else "never"
            nxt = ps.get("next_eligible")
            nxt_str = f"{nxt:.1f}" if nxt else "anytime"
            rl = ps.get("rate_limit")
            rl_str = f"{rl}/hr" if rl else "none"
            tc = ps.get("trigger_count", 0)
            wins = ps.get("allowed_windows") or []
            win_str = ", ".join(f"{w.get('start','?')}-{w.get('end','?')}" for w in wins) if wins else "always"
            lines.append(
                f"  {pid}..  {ps.get('name', '?')}  [{flag}]  "
                f"interval={iv_str}  last={last_str}  next={nxt_str}  "
                f"rate={tc}/{rl_str}  windows={win_str}"
            )

    t3ai = dash.get("tier3_adaptive_insights") or []
    if t3ai:
        lines.append("")
        lines.append(f"Tier-3 adaptive insights ({len(t3ai)}):")
        for ins in t3ai:
            iid = ins.get("insight_id", "?")[:8]
            itype = ins.get("insight_type", "?")
            t_ins = ins.get("timestamp", 0)
            pols = ins.get("related_policy_ids") or []
            props = ins.get("related_proposal_ids") or []
            linked = []
            if pols:
                linked.append(f"policies={[p[:8] + '..' for p in pols]}")
            if props:
                linked.append(f"proposals={[p[:8] + '..' for p in props]}")
            link_str = "  ".join(linked) if linked else ""
            lines.append(
                f"  {iid}..  [{itype}]  t={t_ins:.1f}  "
                f"{ins.get('summary', '')}"
            )
            lines.append(
                f"    -> {ins.get('recommended_action', '')}"
            )
            if link_str:
                lines.append(f"    {link_str}")

    t3ar = dash.get("tier3_adaptive_recommendations") or []
    if t3ar:
        lines.append("")
        lines.append(f"Tier-3 adaptive recommendations ({len(t3ar)}):")
        for rec in t3ar:
            iid = rec.get("insight_id", "?")[:8]
            kind = rec.get("action_kind", "?")
            r = rec.get("result") or {}
            applied = r.get("applied", False)
            artifact = r.get("artifact_type", "?")
            status = "applied" if applied else "not applied"
            t_rec = rec.get("timestamp", 0)
            detail = ""
            if applied and artifact == "plan":
                detail = f"  plan={r.get('plan_id', '?')[:8]}.."
            elif applied and artifact == "proposal":
                detail = f"  proposal={r.get('proposal_id', '?')[:8]}.."
            elif applied and artifact == "policy_edit":
                op = r.get("operation", "?")
                detail = f"  op={op}"
                if r.get("new_policy_id"):
                    detail += f"  new={r['new_policy_id'][:8]}.. (disabled)"
                if r.get("retired_policy_ids"):
                    detail += f"  retired={[p[:8] + '..' for p in r['retired_policy_ids']]}"
                elif r.get("policy_id"):
                    detail += f"  policy={r['policy_id'][:8]}.."
            lines.append(
                f"  {iid}..  {kind}  [{status}]{detail}  t={t_rec:.1f}"
            )

    runbooks = dash.get("tier3_runbooks") or []
    if runbooks:
        lines.append("")
        lines.append("--- Tier-3 Runbooks ---")
        lines.append(f"Defined: {len(runbooks)}")
        for rb in runbooks[-5:]:
            rid = rb.get("runbook_id", "?")[:8]
            name = rb.get("name", "?")
            status = rb.get("status", "?")
            n_steps = len(rb.get("steps", []))
            sr = rb.get("step_results") or []
            ok = sum(1 for s in sr if s.get("status") == "success")
            fail = sum(1 for s in sr if s.get("status") == "failed")
            ts = rb.get("last_executed_at")
            ts_str = f"  t={ts:.1f}" if ts else ""
            lines.append(
                f"  {rid}..  '{name}'  [{status}]  "
                f"steps={n_steps}  ok={ok} fail={fail}{ts_str}"
            )

    ts_data = dash.get("tier3_templates_and_scenarios") or {}
    if ts_data:
        templates = ts_data.get("templates") or []
        scenarios = ts_data.get("scenarios") or []
        recent = ts_data.get("recent_instantiations") or []
        lines.append("")
        lines.append("--- Tier-3 Runbook Templates & Scenarios ---")
        lines.append(f"Templates: {len(templates)}  Scenarios: {len(scenarios)}")
        for t in templates[-5:]:
            tid = t.get("template_id", "?")[:8]
            n_steps = len(t.get("step_blueprints", []))
            lines.append(f"  template {tid}..  '{t.get('name', '?')}'  steps={n_steps}")
        for s in scenarios:
            lines.append(f"  scenario '{s.get('name', '?')}': {s.get('description', '-')[:50]}")
        if recent:
            lines.append(f"Recent instantiations ({len(recent)}):")
            for inst in recent[-3:]:
                tid = inst.get("template_id", "?")[:8]
                rid = inst.get("runbook_id", "?")[:8]
                ts = inst.get("timestamp", 0)
                lines.append(
                    f"  template={tid}..  runbook={rid}..  t={ts:.1f}"
                )

    env_data = dash.get("tier3_environments") or {}
    if env_data:
        lines.append("")
        lines.append("--- Tier-3 Environments ---")
        ae = env_data.get("active_environment")
        total_env = env_data.get("total_environments", 0)
        if ae:
            dp = ae.get("default_profile_id")
            dp_str = dp[:8] + ".." if dp else "none"
            lines.append(
                f"Active: {ae['env_id'][:8]}.. '{ae.get('name', '?')}'  "
                f"profiles={len(ae.get('allowed_profile_ids', []))}  "
                f"policies={len(ae.get('allowed_policy_ids', []))}  "
                f"templates={len(ae.get('allowed_runbook_template_ids', []))}  "
                f"default_profile={dp_str}"
            )
        else:
            lines.append("Active: none")
        lines.append(f"Total environments: {total_env}")
        recent_env = env_data.get("recent_activations") or []
        if recent_env:
            lines.append(f"Recent activations ({len(recent_env)}):")
            for act in recent_env[-3:]:
                eid = act.get("env_id", "?")[:8]
                action = act.get("action", "?")
                ts = act.get("timestamp", 0)
                lines.append(f"  {eid}..  {action}  t={ts:.1f}")

    promo = dash.get("tier3_environment_promotion") or {}
    if promo:
        relations = promo.get("relations") or []
        recent_log = promo.get("recent_log") or []
        lines.append("")
        lines.append("--- Tier-3 Environment Promotion ---")
        if relations:
            lines.append(f"Relations ({len(relations)}):")
            for rel in relations:
                eid = rel.get("env_id", "?")[:8]
                up = rel.get("upstream")
                down = rel.get("downstream") or []
                up_str = up[:8] + ".." if up else "-"
                down_str = ", ".join(d[:8] + ".." for d in down) if down else "-"
                lines.append(
                    f"  {eid}.. '{rel.get('name', '?')}'  "
                    f"up={up_str}  down=[{down_str}]"
                )
        else:
            lines.append("Relations: none")
        if recent_log:
            lines.append(f"Recent activity ({len(recent_log)}):")
            for entry in recent_log[-5:]:
                etype = entry.get("type", "?")
                ts = entry.get("timestamp", 0)
                src = entry.get("source_env_id", "?")[:8]
                tgt = entry.get("target_env_id", "?")[:8]
                detail = ""
                if etype == "plan":
                    detail = f"  ops={entry.get('n_operations', 0)}"
                elif etype == "runbook":
                    rid = entry.get("runbook_id", "?")[:8]
                    detail = f"  runbook={rid}.."
                lines.append(
                    f"  {etype}  {src}.. -> {tgt}..  "
                    f"scope={entry.get('scope', '?')}{detail}  t={ts:.1f}"
                )

    ep = dash.get("tier3_envpacks") or {}
    if ep:
        packs = ep.get("packs") or []
        mappings = ep.get("env_pack_mappings") or []
        recent_app = ep.get("recent_applications") or []
        lines.append("")
        lines.append("--- Tier-3 Environment Governance Packs ---")
        lines.append(f"Packs: {len(packs)}")
        for pk in packs[-5:]:
            pid = pk.get("pack_id", "?")[:8]
            n_pol = len(pk.get("policy_ids", []))
            n_flags = len(pk.get("feature_flag_overrides", {}))
            lines.append(f"  {pid}..  '{pk.get('name', '?')}'  policies={n_pol} flags={n_flags}")
        if mappings:
            lines.append(f"Applied ({len(mappings)} envs):")
            for m in mappings:
                eid = m.get("env_id", "?")[:8]
                n_packs = len(m.get("applied_pack_ids", []))
                n_dpol = m.get("default_policies", 0)
                flags = m.get("default_flags", {})
                flag_str = "  ".join(f"{k}={v}" for k, v in flags.items()) if flags else "-"
                lines.append(
                    f"  {eid}.. '{m.get('env_name', '?')}'  "
                    f"packs={n_packs} default_policies={n_dpol} flags: {flag_str}"
                )
        if recent_app:
            lines.append(f"Recent applications ({len(recent_app)}):")
            for app in recent_app[-3:]:
                eid = app.get("env_id", "?")[:8]
                pid = app.get("pack_id", "?")[:8]
                ts = app.get("timestamp", 0)
                lines.append(f"  env={eid}..  pack={pid}..  t={ts:.1f}")

    hd = dash.get("tier3_env_health_drift") or {}
    if hd:
        rh = hd.get("recent_health") or []
        rd = hd.get("recent_drift") or []
        lines.append("")
        lines.append("--- Tier-3 Environment Health & Drift ---")
        if rh:
            lines.append(f"Recent health ({len(rh)}):")
            for h in rh[-5:]:
                eid = h.get("env_id", "?")[:8]
                grade = h.get("grade", "?")
                n = h.get("findings_count", 0)
                dr = "drift" if h.get("has_drift") else "-"
                ts = h.get("timestamp", 0)
                lines.append(
                    f"  {eid}..  grade={grade}  findings={n}  {dr}  t={ts:.1f}"
                )
        else:
            lines.append("Recent health: none")
        if rd:
            lines.append(f"Recent drift ({len(rd)}):")
            for d in rd[-5:]:
                ea = d.get("env_a", "?")[:8]
                eb = d.get("env_b", "?")[:8]
                dr = "YES" if d.get("has_drift") else "none"
                ts = d.get("timestamp", 0)
                lines.append(f"  {ea}.. vs {eb}..  drift={dr}  t={ts:.1f}")
        else:
            lines.append("Recent drift: none")

    rg = dash.get("tier3_promotion_readiness_guardrails") or {}
    if rg:
        rr = rg.get("recent_readiness") or []
        rgl = rg.get("recent_guardrails") or []
        lines.append("")
        lines.append("--- Tier-3 Promotion Readiness & Guardrails ---")
        if rr:
            lines.append(f"Recent readiness ({len(rr)}):")
            for r in rr[-5:]:
                src = r.get("source_env_id", "?")[:8]
                tgt = r.get("target_env_id", "?")[:8]
                score = r.get("readiness_score", "?")
                nb = r.get("n_blockers", 0)
                nw = r.get("n_warnings", 0)
                ts = r.get("timestamp", 0)
                lines.append(
                    f"  {src}.. -> {tgt}..  score={score}  "
                    f"blockers={nb} warnings={nw}  t={ts:.1f}"
                )
        else:
            lines.append("Recent readiness: none")
        if rgl:
            lines.append(f"Recent guardrails ({len(rgl)}):")
            for g in rgl[-5:]:
                status = "PASS" if g.get("allowed") else "BLOCK"
                nb = len(g.get("blocking_reasons", []))
                nw = len(g.get("warnings", []))
                ts = g.get("timestamp", 0)
                lines.append(
                    f"  {g.get('action', '?')}  {status}  "
                    f"blockers={nb} warnings={nw}  t={ts:.1f}"
                )
        else:
            lines.append("Recent guardrails: none")

    me = dash.get("tier3_multi_env") or {}
    if me:
        rme = me.get("recent_multi_env") or []
        rlin = me.get("recent_lineage") or []
        lines.append("")
        lines.append("--- Tier-3 Multi-Environment Orchestration ---")
        if rme:
            lines.append(f"Recent activity ({len(rme)}):")
            for entry in rme[-5:]:
                etype = entry.get("type", "?")
                src = entry.get("source_env_id", "?")[:8]
                tgt = entry.get("target_env_id", "?")[:8]
                ts = entry.get("timestamp", 0)
                detail = ""
                if etype == "plan":
                    n_ops = entry.get("total_operations", 0)
                    n_gf = entry.get("n_guardrail_failures", 0)
                    detail = f"  ops={n_ops} gf={n_gf}"
                elif etype == "runbook":
                    rid = entry.get("runbook_id", "?")[:8]
                    detail = f"  runbook={rid}.."
                lines.append(
                    f"  {etype}  {src}..→{tgt}..{detail}  t={ts:.1f}"
                )
        else:
            lines.append("Recent activity: none")
        if rlin:
            lines.append(f"Recent lineage ({len(rlin)}):")
            for r in rlin[-5:]:
                oid = r["object_id"][:10]
                origin = r["origin_env_id"][:8]
                derived = r["derived_env_id"][:8]
                ts = r.get("timestamp", 0)
                lines.append(
                    f"  {r['object_type']}  {oid}  "
                    f"{origin}..→{derived}..  {r['operation']}  t={ts:.1f}"
                )
        else:
            lines.append("Recent lineage: none")

    sa = dash.get("tier3_snapshots_audits") or {}
    if sa:
        snaps = sa.get("snapshots") or []
        diffs = sa.get("recent_diffs") or []
        audits = sa.get("recent_audits") or []
        lines.append("")
        lines.append("--- Tier-3 Governance Snapshots & Audits ---")
        if snaps:
            lines.append(f"Snapshots ({len(snaps)}):")
            for s in snaps[-3:]:
                sid = s.get("snapshot_id", "?")[:8]
                sm = s.get("summary", {})
                total = sum(sm.values()) if sm else 0
                ts = s.get("created_at", 0)
                lines.append(
                    f"  {sid}..  '{s.get('label', '?')}'  "
                    f"objects={total}  t={ts:.1f}"
                )
        else:
            lines.append("Snapshots: none")
        if diffs:
            lines.append(f"Recent diffs ({len(diffs)}):")
            for d in diffs[-3:]:
                dtype = d.get("type", "?")
                ch = "YES" if d.get("has_changes") else "none"
                ts = d.get("timestamp", 0)
                lines.append(f"  {dtype}  changes={ch}  t={ts:.1f}")
        if audits:
            lines.append(f"Recent audits ({len(audits)}):")
            for a in audits[-3:]:
                atype = a.get("type", "?")
                ts = a.get("timestamp", 0)
                lines.append(f"  {atype}  t={ts:.1f}")

    fa = dash.get("tier3_forecasting_anomalies") or {}
    if fa:
        rfc = fa.get("recent_forecasts") or []
        ran = fa.get("recent_anomalies") or []
        rin = fa.get("recent_insights") or []
        lines.append("")
        lines.append("--- Tier-3 Forecasting & Anomalies ---")
        if rfc:
            lines.append(f"Recent forecasts ({len(rfc)}):")
            for f in rfc[-3:]:
                ftype = f.get("type", "?")
                pred = f.get("prediction", "?")
                conf = f.get("confidence", "?")
                ts = f.get("timestamp", 0)
                lines.append(
                    f"  {ftype}  pred={pred}  conf={conf}  t={ts:.1f}"
                )
        else:
            lines.append("Recent forecasts: none")
        if ran:
            lines.append(f"Recent anomalies ({len(ran)}):")
            for a in ran[-5:]:
                sev = a.get("severity", "?")
                atype = a.get("anomaly_type", "?")
                lines.append(f"  [{sev}] {atype}: {a.get('detail', '?')[:60]}")
        else:
            lines.append("Recent anomalies: none")
        if rin:
            lines.append(f"Governance insights ({len(rin)}):")
            for i in rin[-3:]:
                itype = i.get("insight_type", "?")
                ts = i.get("timestamp", 0)
                lines.append(
                    f"  [{itype}] {i.get('summary', '?')[:50]}  t={ts:.1f}"
                )

    sm = dash.get("tier3_strategic_modeling") or {}
    if sm:
        rs = sm.get("recent_strategy") or []
        rsi = sm.get("recent_simulations") or []
        lines.append("")
        lines.append("--- Tier-3 Strategic Modeling & Optimization ---")
        if rs:
            lines.append(f"Recent strategy entries ({len(rs)}):")
            for s in rs[-3:]:
                stype = s.get("type", "?")
                n = s.get("n_projections", s.get("n_suggestions", "?"))
                conf = s.get("confidence", "")
                ts = s.get("timestamp", 0)
                detail = f"  {stype}  n={n}"
                if conf:
                    detail += f"  conf={conf}"
                detail += f"  t={ts:.1f}"
                lines.append(detail)
        else:
            lines.append("Recent strategy entries: none")
        if rsi:
            lines.append(f"Recent simulations ({len(rsi)}):")
            for s in rsi[-3:]:
                stype = s.get("type", "?")
                n = s.get("n_impacts", "?")
                ts = s.get("timestamp", 0)
                lines.append(f"  {stype}  impacts={n}  t={ts:.1f}")
        else:
            lines.append("Recent simulations: none")

    gpl = dash.get("tier3_governance_planning") or {}
    if gpl:
        rp = gpl.get("recent_plans") or []
        rpa = gpl.get("recent_planning_activity") or []
        rps = gpl.get("recent_plan_simulations") or []
        lines.append("")
        lines.append("--- Tier-3 Governance Planning ---")
        if rp:
            lines.append(f"Recent plans ({len(rp)}):")
            for p in rp[-3:]:
                pid = p.get("plan_id", "?")[:8]
                scope = p.get("scope", "?")
                n = p.get("n_phases", "?")
                conf = p.get("confidence", "?")
                ts = p.get("timestamp", 0)
                lines.append(
                    f"  {pid}..  scope={scope}  phases={n}  "
                    f"conf={conf}  t={ts:.1f}"
                )
        else:
            lines.append("Recent plans: none")
        if rpa:
            lines.append(f"Recent planning activity ({len(rpa)}):")
            for a in rpa[-3:]:
                atype = a.get("type", "?")
                ts = a.get("timestamp", 0)
                lines.append(f"  {atype}  t={ts:.1f}")
        if rps:
            lines.append(f"Recent plan simulations ({len(rps)}):")
            for s in rps[-3:]:
                pid = s.get("plan_id", "?")[:8]
                dr = s.get("drift_reduction", 0)
                ri = s.get("readiness_improvement", 0)
                ar = s.get("anomaly_reduction", 0)
                lines.append(
                    f"  {pid}..  drift-{dr}%  readiness+{ri}%  anomalies-{ar}%"
                )

    sk = dash.get("tier3_scorecards_kpis") or {}
    if sk:
        rkp = sk.get("recent_kpis") or []
        rsc = sk.get("recent_scorecards") or []
        rdb = sk.get("recent_dashboards") or []
        lines.append("")
        lines.append("--- Tier-3 Strategic Scorecards & KPIs ---")
        if rsc:
            lines.append(f"Recent scorecards ({len(rsc)}):")
            for s in rsc[-3:]:
                stype = s.get("type", "?")
                grade = s.get("grade", "?")
                score = s.get("score", "?")
                ts = s.get("timestamp", 0)
                lines.append(f"  {stype}  grade={grade}  score={score}  t={ts:.1f}")
        else:
            lines.append("Recent scorecards: none")
        if rkp:
            lines.append(f"Recent KPI reports ({len(rkp)}):")
            for k in rkp[-3:]:
                ktype = k.get("type", "?")
                ts = k.get("timestamp", 0)
                lines.append(f"  {ktype}  t={ts:.1f}")
        else:
            lines.append("Recent KPI reports: none")
        if rdb:
            lines.append(f"Strategic dashboard builds ({len(rdb)}):")
            for d in rdb[-3:]:
                grade = d.get("grade", "?")
                score = d.get("score", "?")
                ts = d.get("timestamp", 0)
                lines.append(f"  grade={grade}  score={score}  t={ts:.1f}")

    rp = dash.get("runtime_posture") or {}
    if rp:
        cur = rp.get("current") or {}
        expl = rp.get("explanation") or {}
        trans = rp.get("recent_transitions") or []
        lines.append("")
        lines.append("--- Runtime Posture & Expression ---")
        if cur:
            lines.append(
                f"Current: {cur.get('name', '?')} ({cur.get('posture_id', '?')})  "
                f"category={cur.get('category', '?')}  "
                f"reason={cur.get('reason', '?')}"
            )
        expr = expl.get("expression_profile") or {}
        if expr and not expr.get("error"):
            lines.append(
                f"  Expression: tone={expr.get('tone', '?')}  "
                f"verbosity={expr.get('verbosity', '?')}  "
                f"framing={expr.get('framing', '?')}"
            )
        auto = expl.get("autonomy_profile") or {}
        if auto and not auto.get("error"):
            cats = auto.get("allowed_categories", [])
            lines.append(
                f"  Autonomy: {', '.join(cats) if cats else 'none'}"
            )
        if trans:
            lines.append(f"Recent transitions ({len(trans)}):")
            for t in trans[-3:]:
                ttype = t.get("type", "?")
                lines.append(
                    f"  {ttype}: {t.get('from_posture', '?')} -> "
                    f"{t.get('to_posture', '?')}  "
                    f"reason={t.get('reason', '?')}"
                )

    ef = dash.get("expression_framework") or {}
    if ef:
        prof = ef.get("profile") or {}
        cs = ef.get("cycle_state") or {}
        rce = ef.get("recent_cycle_events") or []
        rsh = ef.get("recent_shaped") or []
        lines.append("")
        lines.append("--- Expression Framework ---")
        if prof:
            lines.append(
                f"Profile: tone={prof.get('tone', '?')}  "
                f"verbosity={prof.get('verbosity', '?')}  "
                f"framing={prof.get('framing_style', prof.get('framing', '?'))}"
            )
            lines.append(
                f"  Comfort layer: {prof.get('comfort_layer', False)}  "
                f"Continuity: {prof.get('continuity_cues', False)}  "
                f"Attunement: {prof.get('operator_attunement', False)}"
            )
        if cs:
            lines.append(
                f"Cycle: interactions={cs.get('interaction_count', 0)}  "
                f"last_event={cs.get('last_event', 'none')}"
            )
        if rsh:
            lines.append(f"Recent shaped responses ({len(rsh)}):")
            for s in rsh[-3:]:
                lines.append(
                    f"  {s.get('posture_id', '?')}  "
                    f"tone={s.get('tone', '?')}  "
                    f"len={s.get('original_len', 0)}->{s.get('shaped_len', 0)}"
                )

    intro = dash.get("identity_introspection") or {}
    if intro:
        lines.append("")
        lines.append("--- Identity Introspection ---")
        lines.append(
            f"Posture: {intro.get('posture_id', '?')}  "
            f"Tier: {intro.get('autonomy_tier', '?')}"
        )
        oc = intro.get("operator_context") or {}
        lines.append(
            f"Intent: {oc.get('interaction_intent', '?')}  "
            f"Focus: {oc.get('operator_focus_level', '?')}  "
            f"Style: {oc.get('operator_engagement_style', '?')}"
        )
        cs = intro.get("continuity_state") or {}
        coh = intro.get("coherence_state") or {}
        lines.append(
            f"Continuity: {cs.get('continuity_strength', '?')}  "
            f"Coherence: {coh.get('coherence_score', '?')}/100 "
            f"(mismatches={coh.get('mismatches', 0)})"
        )
        ss = intro.get("stability_state") or {}
        lines.append(f"Stability: {ss.get('stability_score', '?')}/100")
        rs = intro.get("resonance_state") or {}
        lines.append(
            f"Resonance: intensity={rs.get('intensity', '?')} "
            f"color={rs.get('color', '?')}"
        )
        gs = intro.get("governance_state") or {}
        lines.append(f"Governance health: {gs.get('governance_score', '?')}")
        if intro.get("suppressed"):
            lines.append("[posture-suppressed: some layers inactive]")

    gov = dash.get("governance") or {}
    if gov:
        ks = gov.get("kernel_state") or {}
        dr = gov.get("drift_report") or {}
        proposals = gov.get("proposals") or []
        patches = gov.get("patches") or []
        audit = gov.get("audit_summary") or {}
        clog = gov.get("contract_log") or []

        persona = ks.get("persona") or {}
        mode = ks.get("mode") or {}
        health = ks.get("health") or {}
        envelope = ks.get("envelope") or {}

        lines.append("")
        lines.append("--- Governance Overview ---")
        lines.append(
            f"Persona: {persona.get('persona_id', '?')} ({persona.get('name', '?')})  "
            f"Mode: {mode.get('mode_id', '?')} ({mode.get('name', '?')})"
        )
        lines.append(
            f"Health: {health.get('governance_score', '?')}/100  "
            f"Kill: {ks.get('kill_switch', False)}  "
            f"CB: {ks.get('circuit_breaker', False)}  "
            f"Stabilise: {ks.get('stabilise_mode', False)}"
        )

        lines.append("")
        lines.append("--- Change Contracts ---")
        lines.append(
            f"Risk ceiling: {envelope.get('risk_ceiling', '?')}  "
            f"Approval: {envelope.get('patch_approval_threshold', '?')}  "
            f"Reversibility: {envelope.get('reversibility_required', '?')}"
        )
        if clog:
            lines.append(f"Recent contracts ({len(clog)}):")
            for c in clog[-3:]:
                lines.append(
                    f"  {c.get('change_type', '?')}: "
                    f"allowed={c.get('allowed', '?')} "
                    f"risk={c.get('risk_score', '?')}"
                )

        lines.append("")
        lines.append("--- Proposals & Patches ---")
        if proposals:
            lines.append(f"Proposals ({len(proposals)}):")
            for p in proposals[-3:]:
                lines.append(
                    f"  {p.get('proposal_id', '?')}: {p.get('title', '?')} "
                    f"[{p.get('status', '?')}] risk={p.get('risk_score', '?')}"
                )
        else:
            lines.append("No proposals.")
        if patches:
            lines.append(f"Patches ({len(patches)}):")
            for p in patches[-3:]:
                lines.append(
                    f"  {p.get('patch_id', '?')}: "
                    f"[{p.get('status', '?')}] {p.get('description', '?')}"
                )
        else:
            lines.append("No patches.")

        lines.append("")
        lines.append("--- Drift & Stability ---")
        lines.append(
            f"Total drift: {dr.get('total_drift_score', '?')}  "
            f"Avg: {dr.get('average_drift_score', '?')}  "
            f"Alert: {dr.get('alert', False)}"
        )
        dims = dr.get("dimensions") or {}
        for dname, dinfo in dims.items():
            lines.append(f"  {dname}: {dinfo.get('drift_score', '?')}")

        lines.append("")
        lines.append("--- Audit Log ---")
        lines.append(
            f"Total events: {audit.get('total_events', 0)}  "
            f"Types: {len(audit.get('event_types', {}))}"
        )

    eres = dash.get("expressive_resonance") or {}
    if eres:
        rsumm = eres.get("summary") or {}
        rlog = eres.get("recent_log") or []
        lines.append("")
        lines.append("--- Expressive Resonance ---")
        lines.append(
            f"Posture: {rsumm.get('posture_id', '?')}  "
            f"Intensity: {rsumm.get('resonance_intensity', '?')}  "
            f"Color: {rsumm.get('resonance_color', '?')}"
        )
        lines.append(
            f"Decay: {rsumm.get('resonance_decay_rate', '?')}  "
            f"Blend: {rsumm.get('blend_factor', '?')}  "
            f"Previous: {rsumm.get('previous_posture_id', 'none')}"
        )
        if rlog:
            lines.append(f"Recent resonance ({len(rlog)}):")
            for rl in rlog[-3:]:
                lines.append(
                    f"  {rl.get('posture_id', '?')}  "
                    f"eff={rl.get('effective_intensity', '?')}  "
                    f"blend={rl.get('blend_factor', '?')}  "
                    f"{rl.get('action', '?')}"
                )

    estab = dash.get("expressive_stability") or {}
    if estab:
        sstate = estab.get("stability_state") or {}
        lasumm = estab.get("long_arc_summary") or {}
        rstab = estab.get("recent_stability") or []
        rsmooth = estab.get("recent_smoothing") or []
        lines.append("")
        lines.append("--- Expressive Stability ---")
        lines.append(
            f"Score: {sstate.get('stability_score', '?')}  "
            f"Oscillation: {sstate.get('oscillation_index', '?')}  "
            f"Jitter: {sstate.get('jitter_index', '?')}"
        )
        lines.append(f"Updates: {sstate.get('update_count', 0)}")
        rp = sstate.get("recent_postures") or []
        if rp:
            lines.append(f"Recent postures: {', '.join(str(p) for p in rp[-5:])}")
        rt = sstate.get("recent_tiers") or []
        if rt:
            lines.append(f"Recent tiers: {', '.join(str(t) for t in rt[-5:])}")
        if rstab:
            lines.append(f"Recent stability ({len(rstab)}):")
            for rs in rstab[-3:]:
                lines.append(
                    f"  score={rs.get('stability_score', '?')}  "
                    f"osc={rs.get('oscillation_index', '?')}  "
                    f"jitter={rs.get('jitter_index', '?')}"
                )
        if rsmooth:
            lines.append(f"Recent smoothing ({len(rsmooth)}):")
            for sm in rsmooth[-3:]:
                lines.append(
                    f"  {sm.get('target', '?')}  {sm.get('posture_id', '?')}  "
                    f"stab={sm.get('stability_score', '?')}"
                )

    icoh = dash.get("identity_coherence") or {}
    if icoh:
        csumm = icoh.get("coherence_summary") or {}
        asumm = icoh.get("alignment_summary") or {}
        rcoh = icoh.get("recent_coherence") or []
        raln = icoh.get("recent_alignment") or []
        lines.append("")
        lines.append("--- Identity Coherence ---")
        lines.append(
            f"Score: {csumm.get('last_score', '?')}  "
            f"Mismatches: {csumm.get('last_n_mismatches', 0)}  "
            f"Evaluations: {csumm.get('total_evaluations', 0)}"
        )
        res_list = csumm.get("last_resolutions") or []
        lines.append(
            f"Resolutions: {', '.join(res_list) if res_list else 'none'}"
        )
        lines.append(
            f"Alignment: corrections={asumm.get('last_corrections_applied', 0)}  "
            f"total={asumm.get('total_alignments', 0)}"
        )
        if rcoh:
            lines.append(f"Recent coherence ({len(rcoh)}):")
            for c in rcoh[-3:]:
                lines.append(
                    f"  score={c.get('score', '?')}  "
                    f"mismatches={c.get('n_mismatches', 0)}  "
                    f"posture={c.get('posture_id', '?')}"
                )
        if raln:
            lines.append(f"Recent alignment ({len(raln)}):")
            for a in raln[-3:]:
                lines.append(
                    f"  posture={a.get('posture_id', '?')}  "
                    f"score={a.get('coherence_score', '?')}  "
                    f"corrections={a.get('corrections_applied', 0)}  "
                    f"len={a.get('original_len', 0)}->{a.get('aligned_len', 0)}"
                )

    idc = dash.get("identity_continuity") or {}
    if idc:
        cstate = idc.get("state") or {}
        esumm = idc.get("engine_summary") or {}
        rshaped = idc.get("recent_shaped") or []
        lines.append("")
        lines.append("--- Identity Continuity ---")
        lines.append(
            f"Active: {cstate.get('continuity_active', False)}  "
            f"Strength: {cstate.get('continuity_strength', 'low')}  "
            f"Weight: {esumm.get('continuity_weight', 0.0)}"
        )
        lines.append(
            f"Last posture: {cstate.get('last_posture_id', 'none')}  "
            f"Last tier: {cstate.get('last_tier_id', 'none')}"
        )
        lines.append(
            f"Last intent: {cstate.get('last_interaction_intent', 'none')}  "
            f"Last focus: {cstate.get('last_focus_level', 'none')}"
        )
        if rshaped:
            lines.append(f"Recent continuity-shaped ({len(rshaped)}):")
            for rs in rshaped[-3:]:
                lines.append(
                    f"  {rs.get('posture_id', '?')}  w={rs.get('weight', 0):.2f}  "
                    f"{rs.get('action', '?')}  "
                    f"len={rs.get('original_len', 0)}->{rs.get('shaped_len', 0)}"
                )

    oi = dash.get("operator_interaction") or {}
    if oi:
        octx = oi.get("operator_context") or {}
        isumm = oi.get("interaction_summary") or {}
        rctx = oi.get("recent_context_events") or []
        rint = oi.get("recent_interactions") or []
        lines.append("")
        lines.append("--- Operator Interaction Model ---")
        lines.append(
            f"Intent: {octx.get('interaction_intent', '?')}  "
            f"Focus: {octx.get('operator_focus_level', '?')}  "
            f"Style: {octx.get('operator_engagement_style', '?')}"
        )
        lines.append(
            f"Continuity window: {octx.get('continuity_window_active', False)}"
        )
        fr = isumm.get("flow_rules") or {}
        lines.append(
            f"Flow: comfort={fr.get('comfort_layer', False)}  "
            f"continuity={fr.get('continuity_cues', False)}  "
            f"soft_transitions={fr.get('soft_transitions', False)}"
        )
        lines.append(
            f"Posture: {isumm.get('posture_id', '?')}  "
            f"Tier: {isumm.get('tier_id', '?')}"
        )
        if rint:
            lines.append(f"Recent shaped interactions ({len(rint)}):")
            for ri in rint[-3:]:
                lines.append(
                    f"  {ri.get('posture_id', '?')}  {ri.get('action', '?')}  "
                    f"len={ri.get('original_len', 0)}->{ri.get('shaped_len', 0)}"
                )

    atd = dash.get("autonomy_tiers") or {}
    if atd:
        et = atd.get("effective_tier") or {}
        expl = atd.get("explanation") or {}
        rtrans = atd.get("recent_transitions") or []
        lines.append("")
        lines.append("--- Autonomy Tiers ---")
        lines.append(
            f"Effective tier: {et.get('name', '?')} ({et.get('tier_id', '?')})"
        )
        lines.append(f"  Reason: {et.get('reason', '?')}")
        pf = expl.get("posture_forced_tier")
        if pf:
            lines.append(f"  Posture-forced: {pf}")
        if expl.get("operator_override"):
            lines.append(f"  Operator override: yes")
        allowed = et.get("allowed_action_categories", [])
        disallowed = et.get("disallowed_action_categories", [])
        lines.append(f"  Allowed: {', '.join(allowed) if allowed else 'none'}")
        lines.append(f"  Disallowed: {', '.join(disallowed) if disallowed else 'none'}")
        if rtrans:
            lines.append(f"Recent tier transitions ({len(rtrans)}):")
            for tr in rtrans[-3:]:
                lines.append(
                    f"  {tr.get('from_tier', '?')} -> {tr.get('to_tier', '?')}  "
                    f"reason={tr.get('reason', '?')}  t={tr.get('timestamp', 0):.1f}"
                )

    sre = dash.get("tier3_sla_risk_exec") or {}
    if sre:
        rsla = sre.get("recent_sla") or []
        rrsk = sre.get("recent_risk") or []
        rhm = sre.get("recent_heatmaps") or []
        rer = sre.get("recent_exec_reports") or []
        lines.append("")
        lines.append("--- Tier-3 Governance SLAs, Risk & Executive Reports ---")
        if rsla:
            lines.append(f"Recent SLA evaluations ({len(rsla)}):")
            for s in rsla[-3:]:
                stype = s.get("type", "?")
                ok = "PASS" if s.get("passed") else "FAIL"
                fail = s.get("failures", 0)
                ts = s.get("timestamp", 0)
                lines.append(f"  {stype}  {ok}  failures={fail}  t={ts:.1f}")
        else:
            lines.append("Recent SLA evaluations: none")
        if rrsk:
            lines.append(f"Recent risk scores ({len(rrsk)}):")
            for r in rrsk[-3:]:
                rtype = r.get("type", "?")
                score = r.get("risk_score", "?")
                tier = r.get("risk_tier", "?")
                ts = r.get("timestamp", 0)
                lines.append(f"  {rtype}  score={score}  tier={tier}  t={ts:.1f}")
        else:
            lines.append("Recent risk scores: none")
        if rhm:
            lines.append(f"Recent heatmaps ({len(rhm)}):")
            for h in rhm[-3:]:
                htype = h.get("type", "?")
                n_hot = h.get("n_hot", h.get("heat", "?"))
                ts = h.get("timestamp", 0)
                lines.append(f"  {htype}  hot={n_hot}  t={ts:.1f}")
        if rer:
            lines.append(f"Executive reports ({len(rer)}):")
            for e in rer[-3:]:
                grade = e.get("grade", "?")
                risk_tier = e.get("risk_tier", "?")
                ts = e.get("timestamp", 0)
                lines.append(f"  grade={grade}  risk={risk_tier}  t={ts:.1f}")

    bm = dash.get("tier3_benchmarking_maturity") or {}
    if bm:
        rb = bm.get("recent_benchmarks") or []
        rm = bm.get("recent_maturity") or []
        rc = bm.get("recent_comparisons") or []
        lines.append("")
        lines.append("--- Tier-3 Governance Benchmarking & Maturity ---")
        if rb:
            lines.append(f"Recent benchmarks ({len(rb)}):")
            for b in rb[-3:]:
                btype = b.get("type", "?")
                grade = b.get("grade", "?")
                ts = b.get("timestamp", 0)
                lines.append(f"  {btype}  grade={grade}  t={ts:.1f}")
        else:
            lines.append("Recent benchmarks: none")
        if rm:
            lines.append(f"Recent maturity evaluations ({len(rm)}):")
            for m in rm[-3:]:
                mtype = m.get("type", "?")
                tier = m.get("tier", "?")
                score = m.get("score", "?")
                ts = m.get("timestamp", 0)
                lines.append(f"  {mtype}  tier={tier}  score={score}  t={ts:.1f}")
        else:
            lines.append("Recent maturity evaluations: none")
        if rc:
            lines.append(f"Recent comparisons ({len(rc)}):")
            for c in rc[-3:]:
                ctype = c.get("type", "?")
                ts = c.get("timestamp", 0)
                lines.append(f"  {ctype}  t={ts:.1f}")

    mg = dash.get("tier3_meta_governance") or {}
    if mg:
        objs = mg.get("objectives") or []
        ra = mg.get("recent_alignments") or []
        rmm = mg.get("recent_meta_models") or []
        lines.append("")
        lines.append("--- Tier-3 Meta-Governance & Objectives ---")
        if objs:
            lines.append(f"Objectives ({len(objs)}):")
            for o in objs[-5:]:
                lines.append(
                    f"  {o.get('objective_id', '?')[:8]}.. "
                    f"'{o.get('name', '?')}'"
                )
        else:
            lines.append("Objectives: none")
        if ra:
            lines.append(f"Recent alignments ({len(ra)}):")
            for a in ra[-3:]:
                atype = a.get("type", "?")
                score = a.get("score", "?")
                ts = a.get("timestamp", 0)
                lines.append(f"  {atype}  score={score}  t={ts:.1f}")
        if rmm:
            lines.append(f"Recent meta-models ({len(rmm)}):")
            for m in rmm[-3:]:
                mtype = m.get("type", "?")
                ts = m.get("timestamp", 0)
                extra = ""
                if "trajectory" in m:
                    extra = f"  trajectory={m['trajectory']}"
                elif "feasibility" in m:
                    extra = f"  feasibility={m['feasibility']}"
                lines.append(f"  {mtype}{extra}  t={ts:.1f}")

    pe = dash.get("tier3_personas_envelopes") or {}
    if pe:
        personas = pe.get("personas") or []
        modes = pe.get("modes") or []
        envs = pe.get("recent_envelopes") or []
        lines.append("")
        lines.append("--- Tier-3 Governance Personas & Envelopes ---")
        if personas:
            lines.append(f"Personas ({len(personas)}):")
            for p in personas[-5:]:
                lines.append(
                    f"  {p.get('persona_id', '?')[:8]}.. "
                    f"'{p.get('name', '?')}'  "
                    f"objectives={len(p.get('objective_bindings', []))}"
                )
        else:
            lines.append("Personas: none")
        if modes:
            lines.append(f"Orchestration modes ({len(modes)}):")
            for m in modes[-5:]:
                lines.append(
                    f"  {m.get('mode_id', '?')[:8]}.. "
                    f"'{m.get('name', '?')}'"
                )
        else:
            lines.append("Orchestration modes: none")
        if envs:
            lines.append(f"Recent envelopes ({len(envs)}):")
            for e in envs[-3:]:
                lines.append(
                    f"  {e.get('persona_name', '?')} + "
                    f"{e.get('mode_name', '?')}  "
                    f"composite={e.get('composite_score', '?')}  "
                    f"constraints={e.get('constraints_met', 0)}/"
                    f"{e.get('constraints_total', 0)}  "
                    f"pressure={e.get('pressure_points_count', 0)}  "
                    f"conflicts={e.get('conflicts_count', 0)}"
                )

    gp = dash.get("tier3_governance_profiles") or {}
    if gp:
        lines.append("")
        lines.append("--- Tier-3 Governance Profiles ---")
        ap = gp.get("active_profile")
        total = gp.get("total_profiles", 0)
        if ap:
            flags = ap.get("tier3_feature_flags", {})
            flag_str = "  ".join(f"{k}={v}" for k, v in flags.items())
            lines.append(
                f"Active: {ap['profile_id'][:8]}.. '{ap.get('name', '?')}'  "
                f"policies={len(ap.get('attached_policy_ids', []))}  "
                f"flags: {flag_str}"
            )
            overrides = ap.get("scheduling_overrides", {})
            if overrides:
                lines.append(f"  scheduling overrides: {len(overrides)} policies")
        else:
            lines.append("Active: none")
        lines.append(f"Total profiles: {total}")
        recent = gp.get("recent_activations") or []
        if recent:
            lines.append(f"Recent activations ({len(recent)}):")
            for act in recent[-3:]:
                pid = act.get("profile_id", "?")[:8]
                action = act.get("action", "?")
                ts = act.get("timestamp", 0)
                lines.append(f"  {pid}..  {action}  t={ts:.1f}")

    at1 = dash.get("active_tier1_autonomy")
    if at1:
        lines.append("")
        lines.append(f"Active Tier-1 autonomy: enabled={at1.get('autonomy_enabled', '?')}  "
                      f"envelope={at1.get('envelope_summary', '?')}")
        exec_names = [e.get("action", {}).get("name", "?") for e in at1.get("executed") or []]
        skip_names = [s.get("action", {}).get("name", "?") for s in at1.get("skipped") or []]
        lines.append(f"  executed: {exec_names}")
        lines.append(f"  skipped:  {skip_names}")
        for s in at1.get("skipped") or []:
            v = s.get("verdict") or {}
            lines.append(f"    {s.get('action', {}).get('name', '?')}: "
                          + ", ".join(v.get("reasons") or []))

    return "\n".join(lines)
