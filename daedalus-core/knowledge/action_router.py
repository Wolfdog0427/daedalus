# knowledge/action_router.py

"""
Action Router

Maps natural-language console commands to concrete system actions.

This module is intentionally thin: it interprets the user's command,
routes it to the appropriate subsystem (SHO, stability engine, dashboard,
trust scoring, autonomy governor), and returns a human-readable summary.
"""

from __future__ import annotations

import json
from typing import Optional

from knowledge.system_dashboard import dashboard_summary
from knowledge.stability_engine import enforce_stability
from knowledge.trust_scoring import verify_and_ingest

# These subsystems are optional and may evolve over time.
# We import them defensively to avoid hard crashes if they change.
try:
    import knowledge.self_healing_orchestrator as sho
except ImportError:  # pragma: no cover
    sho = None  # type: ignore[assignment]

try:
    import knowledge.autonomy_governor as governor
except ImportError:  # pragma: no cover
    governor = None  # type: ignore[assignment]

try:
    from knowledge.integration_layer import (
        do_curiosity_cycle,
        do_approve_knowledge_goal,
        do_execute_knowledge_goal,
        do_knowledge_acquisition,
        do_quality_gate,
        do_concept_evolution,
        do_consistency_scan,
        do_storage_maintenance,
        do_claim_verification,
        do_meta_cycle,
        do_provider_discovery,
        do_flow_tuning,
        do_active_consolidation,
        do_delayed_poison_audit,
        do_entropy_budget_report,
        do_epoch_status,
        do_start_epoch,
        do_end_epoch,
        do_renewal_cycle,
        do_drift_court,
        do_graph_compaction,
        do_canonical_template_summary,
        do_renewal_status,
        do_drift_court_summary,
        do_apply_canonization,
    )
    _INTEGRATION_AVAILABLE = True
except ImportError:
    _INTEGRATION_AVAILABLE = False

try:
    from knowledge.meta_reasoner import run_meta_cycle, meta_status
    _META_AVAILABLE = True
except ImportError:
    _META_AVAILABLE = False

try:
    from knowledge.llm_adapter import llm_adapter as _llm_adapter
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False


try:
    from knowledge.knowledge_goal import list_goals as _list_goals
    _GOALS_AVAILABLE = True
except ImportError:
    _GOALS_AVAILABLE = False


# -------------------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------------------

def _normalize(cmd: str) -> str:
    return cmd.strip().lower()


def _extract_after_colon(cmd: str) -> str:
    if ":" in cmd:
        return cmd.split(":", 1)[1].strip()
    return ""


# -------------------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------------------

def route_command(cmd: str, claim: Optional[str] = None) -> str:
    """
    Route a natural-language command to the appropriate subsystem.

    Parameters
    ----------
    cmd:
        The raw command string entered by the user.
    claim:
        Optional extracted claim text (for "verify this:" / "explain this:" patterns).

    Returns
    -------
    str
        A human-readable result string to display in the console.
    """
    norm = _normalize(cmd)

    # ------------------------------------------------------------
    # STORAGE / MAINTENANCE
    # ------------------------------------------------------------
    if norm.startswith("clean up storage") or norm.startswith("cleanup storage") or norm.startswith("clean storage") or norm == "storage maintenance":
        if _INTEGRATION_AVAILABLE:
            result = do_storage_maintenance()
            return f"[STORAGE MAINTENANCE]\n{json.dumps(result, indent=2)}"
        return "[STORAGE] Storage maintenance module not available."

    # ------------------------------------------------------------
    # META-REASONING CYCLE
    # ------------------------------------------------------------
    if norm.startswith("run meta cycle") or norm.startswith("meta cycle") or norm == "meta":
        if _INTEGRATION_AVAILABLE:
            result = do_meta_cycle()
            if result.get("allowed") and result.get("result"):
                actions = [a["type"] for a in result["result"].get("actions", [])]
                return (
                    f"[META CYCLE] Completed.\n"
                    f"Actions taken: {', '.join(actions) if actions else 'none'}\n"
                    f"{json.dumps(result, indent=2, default=str)}"
                )
            return f"[META CYCLE]\n{json.dumps(result, indent=2, default=str)}"
        if _META_AVAILABLE:
            result = run_meta_cycle()
            actions = [a["type"] for a in result.get("actions", [])]
            return (
                f"[META CYCLE] Completed.\n"
                f"Actions taken: {', '.join(actions) if actions else 'none'}\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
        return "[META] Meta-reasoning module not available."

    if norm.startswith("meta status") or norm == "system health":
        if _META_AVAILABLE:
            status = meta_status()
            return f"[META STATUS]\n{json.dumps(status, indent=2, default=str)}"
        return "[META] Meta-reasoning module not available."

    # ------------------------------------------------------------
    # CURIOSITY / KNOWLEDGE GOALS
    # ------------------------------------------------------------
    if norm.startswith("run curiosity") or norm == "curiosity" or norm.startswith("discover gaps"):
        if _INTEGRATION_AVAILABLE:
            result = do_curiosity_cycle()
            return f"[CURIOSITY]\n{json.dumps(result, indent=2, default=str)}"
        return "[CURIOSITY] Curiosity engine not available."

    if norm.startswith("approve goal"):
        goal_id = _extract_after_colon(cmd) or cmd.split()[-1] if len(cmd.split()) > 2 else ""
        if not goal_id:
            return "[GOALS] No goal ID provided. Usage: approve goal: <goal_id>"
        if _INTEGRATION_AVAILABLE:
            result = do_approve_knowledge_goal(goal_id)
            return f"[GOAL APPROVED]\n{json.dumps(result, indent=2, default=str)}"
        return "[GOALS] Integration layer not available."

    if norm.startswith("list goals") or norm == "goals":
        if _GOALS_AVAILABLE:
            goals = _list_goals()
            summary = [
                {"id": g.id, "topic": g.topic, "status": g.status, "priority": g.priority}
                for g in goals
            ]
            return f"[KNOWLEDGE GOALS]\n{json.dumps(summary, indent=2, default=str)}"
        return "[GOALS] Knowledge goal module not available."

    if norm.startswith("acquire") or norm.startswith("ingest batch"):
        text = _extract_after_colon(cmd)
        if not text:
            return "[ACQUIRE] No content provided. Usage: acquire: <text>"
        if _INTEGRATION_AVAILABLE:
            items = [{"text": text.strip()}]
            result = do_knowledge_acquisition(items, source="operator")
            return f"[ACQUISITION]\n{json.dumps(result, indent=2, default=str)}"
        return "[ACQUIRE] Integration layer not available."

    if norm.startswith("execute goal") or norm.startswith("run goal"):
        goal_id = _extract_after_colon(cmd) or cmd.split()[-1] if len(cmd.split()) > 2 else ""
        if not goal_id:
            return "[EXECUTE GOAL] No goal ID provided. Usage: execute goal: <goal_id>"
        if _INTEGRATION_AVAILABLE:
            result = do_execute_knowledge_goal(goal_id)
            return f"[GOAL EXECUTION]\n{json.dumps(result, indent=2, default=str)}"
        return "[EXECUTE GOAL] Integration layer not available."

    if norm.startswith("quality gate"):
        goal_id = _extract_after_colon(cmd) or cmd.split()[-1] if len(cmd.split()) > 2 else ""
        if not goal_id:
            return "[QUALITY GATE] No goal ID provided. Usage: quality gate: <goal_id>"
        if _INTEGRATION_AVAILABLE:
            result = do_quality_gate(goal_id)
            return f"[QUALITY GATE]\n{json.dumps(result, indent=2, default=str)}"
        return "[QUALITY GATE] Integration layer not available."

    # ------------------------------------------------------------
    # GOVERNED CONCEPT EVOLUTION (through integration layer)
    # ------------------------------------------------------------
    if norm.startswith("evolve concepts") or norm.startswith("run evolution") or norm.startswith("evolve"):
        if _INTEGRATION_AVAILABLE:
            result = do_concept_evolution()
            return f"[EVOLUTION]\n{json.dumps(result, indent=2, default=str)}"
        if sho is not None and hasattr(sho, "run_evolution_cycle"):
            result = sho.run_evolution_cycle()
            return f"[EVOLUTION]\n{result}"
        return "[EVOLUTION] Concept evolution is not available."

    # ------------------------------------------------------------
    # GOVERNED CONSISTENCY SCAN (through integration layer)
    # ------------------------------------------------------------
    if norm.startswith("run a consistency scan") or norm.startswith("run consistency scan") or norm == "consistency scan":
        if _INTEGRATION_AVAILABLE:
            result = do_consistency_scan()
            return f"[CONSISTENCY SCAN]\n{json.dumps(result, indent=2, default=str)}"
        if sho is not None and hasattr(sho, "run_consistency_scan"):
            result = sho.run_consistency_scan()
            return f"[CONSISTENCY SCAN]\n{result}"
        return "[CONSISTENCY SCAN] Not available."

    # ------------------------------------------------------------
    # LLM / PROVIDER MANAGEMENT
    # ------------------------------------------------------------
    if norm.startswith("list providers") or norm == "providers":
        if _LLM_AVAILABLE:
            providers = _llm_adapter.list_providers()
            return f"[LLM PROVIDERS]\n{json.dumps(providers, indent=2, default=str)}"
        return "[LLM] LLM adapter not available."

    if norm.startswith("provider notifications") or norm.startswith("provider alerts"):
        if _LLM_AVAILABLE:
            notifs = _llm_adapter.get_notifications()
            return f"[PROVIDER NOTIFICATIONS]\n{json.dumps(notifs, indent=2, default=str)}"
        return "[LLM] LLM adapter not available."

    if norm.startswith("discover providers") or norm.startswith("run discovery"):
        if _INTEGRATION_AVAILABLE:
            result = do_provider_discovery()
            return f"[PROVIDER DISCOVERY]\n{json.dumps(result, indent=2, default=str)}"
        return "[DISCOVERY] Provider discovery not available."

    # ------------------------------------------------------------
    # FLOW TUNING
    # ------------------------------------------------------------
    if norm.startswith("tune flow") or norm.startswith("flow tuning") or norm == "tune":
        if _INTEGRATION_AVAILABLE:
            result = do_flow_tuning()
            return f"[FLOW TUNER]\n{json.dumps(result, indent=2, default=str)}"
        return "[FLOW] Flow tuner not available."

    if norm.startswith("flow dashboard") or norm.startswith("pipeline health"):
        if _INTEGRATION_AVAILABLE:
            try:
                from knowledge.flow_tuner import flow_tuner as _ft
                result = _ft.dashboard()
                return f"[PIPELINE HEALTH]\n{json.dumps(result, indent=2, default=str)}"
            except ImportError:
                pass
        return "[FLOW] Flow tuner not available."

    # ------------------------------------------------------------
    # CIRCUIT BREAKER / LONG-TERM TRENDS / REGRESSION STATUS
    # ------------------------------------------------------------
    if norm.startswith("circuit breaker") or norm.startswith("breaker status"):
        try:
            from knowledge.adaptive_pacer import get_circuit_breaker, get_long_term_trends
            cb = get_circuit_breaker().status()
            lt = get_long_term_trends()
            combined = {"circuit_breaker": cb, "long_term_trends": lt}
            return f"[CIRCUIT BREAKER]\n{json.dumps(combined, indent=2, default=str)}"
        except ImportError:
            return "[CIRCUIT BREAKER] Adaptive pacer not available."

    if norm.startswith("regression status"):
        try:
            from knowledge.meta_reasoner import get_regression_detector, get_stability_tracker, get_severity_context
            result = {
                "regression": get_regression_detector().status(),
                "stability": get_stability_tracker().status(),
                "severity": get_severity_context().status(),
            }
            return f"[REGRESSION STATUS]\n{json.dumps(result, indent=2, default=str)}"
        except ImportError:
            return "[REGRESSION] Meta-reasoner not available."

    if norm.startswith("set severity"):
        level = _extract_after_colon(cmd) or cmd.split()[-1] if len(cmd.split()) > 2 else ""
        if not level:
            return "[SEVERITY] No level provided. Usage: set severity: <nominal|elevated|stressed|severe|catastrophic>"
        try:
            from knowledge.meta_reasoner import get_severity_context
            ctx = get_severity_context()
            ctx.set_level(level.strip())
            return f"[SEVERITY] Severity set to: {ctx.current_level}"
        except ImportError:
            return "[SEVERITY] Meta-reasoner not available."

    if norm.startswith("trust momentum") or norm.startswith("trust stats"):
        try:
            from knowledge.trust_scoring import get_trust_momentum_summary
            result = get_trust_momentum_summary()
            return f"[TRUST MOMENTUM]\n{json.dumps(result, indent=2, default=str)}"
        except ImportError:
            return "[TRUST] Trust momentum not available."

    # ------------------------------------------------------------
    # ACTIVE CONSOLIDATION (C1) / POISON AUDIT (M2) / COORDINATOR (C2)
    # ------------------------------------------------------------
    if norm.startswith("consolidat") or norm.startswith("active consolidat"):
        if _INTEGRATION_AVAILABLE:
            result = do_active_consolidation()
            return f"[ACTIVE CONSOLIDATION]\n{json.dumps(result, indent=2, default=str)}"
        return "[CONSOLIDATION] Not available."

    if norm.startswith("poison audit") or norm.startswith("delayed poison"):
        if _INTEGRATION_AVAILABLE:
            result = do_delayed_poison_audit()
            return f"[POISON AUDIT]\n{json.dumps(result, indent=2, default=str)}"
        return "[POISON AUDIT] Not available."

    if norm.startswith("quarantine review") or norm.startswith("review quarantine"):
        if _INTEGRATION_AVAILABLE:
            try:
                from knowledge.integration_layer import do_quarantine_review
                result = do_quarantine_review()
                return f"[QUARANTINE REVIEW]\n{json.dumps(result, indent=2, default=str)}"
            except ImportError:
                pass
        return "[QUARANTINE] Not available."

    if norm.startswith("quarantine status") or norm.startswith("quarantine"):
        if _INTEGRATION_AVAILABLE:
            try:
                from knowledge.integration_layer import do_quarantine_status
                result = do_quarantine_status()
                return f"[QUARANTINE STATUS]\n{json.dumps(result, indent=2, default=str)}"
            except ImportError:
                pass
        try:
            from knowledge.source_integrity import get_quarantine_status
            result = get_quarantine_status()
            return f"[QUARANTINE STATUS]\n{json.dumps(result, indent=2, default=str)}"
        except ImportError:
            return "[QUARANTINE] Not available."

    if norm.startswith("confidence") or norm.startswith("epistemic"):
        try:
            from knowledge.trust_scoring import compute_calibrated_trust, compute_epistemic_confidence
            from knowledge.retrieval import _iter_items
            import random as _rnd
            sample = []
            for item in _iter_items():
                sample.append(item)
                if len(sample) >= 10:
                    break
            results = []
            for item in sample:
                ec = compute_epistemic_confidence(item)
                ct = compute_calibrated_trust(item)
                results.append({
                    "id": item.get("id", "?"),
                    "trust": round(ct, 3),
                    "confidence": ec["confidence"],
                    "corroboration": ec["corroboration"],
                })
            return f"[EPISTEMIC CONFIDENCE]\n{json.dumps(results, indent=2, default=str)}"
        except ImportError:
            return "[CONFIDENCE] Trust scoring not available."

    if norm.startswith("defensive status") or norm.startswith("coordinator status"):
        try:
            from knowledge.meta_reasoner import get_defensive_coordinator, get_regression_detector, get_stability_tracker, get_severity_context
            result = {
                "coordinator": get_defensive_coordinator().status(),
                "regression": get_regression_detector().status(),
                "stability": get_stability_tracker().status(),
                "severity": get_severity_context().status(),
            }
            return f"[DEFENSIVE STATUS]\n{json.dumps(result, indent=2, default=str)}"
        except ImportError:
            return "[DEFENSIVE] Meta-reasoner not available."

    # ------------------------------------------------------------
    # ANTI-ENTROPY LAYER
    # ------------------------------------------------------------
    if norm.startswith("entropy budget") or norm.startswith("entropy report") or norm == "entropy":
        if _INTEGRATION_AVAILABLE:
            result = do_entropy_budget_report()
            return f"[ENTROPY BUDGET]\n{json.dumps(result, indent=2, default=str)}"
        return "[ENTROPY] Anti-entropy layer not available."

    if norm.startswith("epoch status") or norm.startswith("current epoch"):
        if _INTEGRATION_AVAILABLE:
            result = do_epoch_status()
            return f"[EPOCH STATUS]\n{json.dumps(result, indent=2, default=str)}"
        return "[EPOCH] Epoch engine not available."

    if norm.startswith("start epoch"):
        hours_str = _extract_after_colon(cmd)
        hours = float(hours_str) if hours_str else 48.0
        if _INTEGRATION_AVAILABLE:
            result = do_start_epoch(duration_hours=hours)
            return f"[EPOCH STARTED]\n{json.dumps(result, indent=2, default=str)}"
        return "[EPOCH] Epoch engine not available."

    if norm.startswith("end epoch"):
        if _INTEGRATION_AVAILABLE:
            result = do_end_epoch()
            return f"[EPOCH ENDED]\n{json.dumps(result, indent=2, default=str)}"
        return "[EPOCH] Epoch engine not available."

    if norm.startswith("run renewal") or norm.startswith("renewal cycle"):
        dry = "dry" in norm
        if _INTEGRATION_AVAILABLE:
            result = do_renewal_cycle(dry_run=dry)
            return f"[RENEWAL]\n{json.dumps(result, indent=2, default=str)}"
        return "[RENEWAL] Renewal layer not available."

    if norm.startswith("renewal status") or norm.startswith("renewal health"):
        if _INTEGRATION_AVAILABLE:
            result = do_renewal_status()
            return f"[RENEWAL STATUS]\n{json.dumps(result, indent=2, default=str)}"
        return "[RENEWAL] Renewal layer not available."

    if norm.startswith("drift court") or norm.startswith("run drift court"):
        if _INTEGRATION_AVAILABLE:
            result = do_drift_court()
            return f"[DRIFT COURT]\n{json.dumps(result, indent=2, default=str)}"
        return "[DRIFT COURT] Drift court not available."

    if norm.startswith("court summary") or norm.startswith("drift summary"):
        if _INTEGRATION_AVAILABLE:
            result = do_drift_court_summary()
            return f"[COURT SUMMARY]\n{json.dumps(result, indent=2, default=str)}"
        return "[DRIFT COURT] Drift court not available."

    if norm.startswith("graph compact") or norm.startswith("compact graph") or norm.startswith("run compaction"):
        if _INTEGRATION_AVAILABLE:
            result = do_graph_compaction()
            return f"[GRAPH COMPACTION]\n{json.dumps(result, indent=2, default=str)}"
        return "[COMPACTION] Graph compactor not available."

    if norm.startswith("canonical template") or norm.startswith("template status"):
        if _INTEGRATION_AVAILABLE:
            result = do_canonical_template_summary()
            return f"[CANONICAL TEMPLATE]\n{json.dumps(result, indent=2, default=str)}"
        return "[TEMPLATE] Canonical template not available."

    if norm.startswith("canonize") or norm.startswith("apply canonization"):
        proposal_id = _extract_after_colon(cmd) or (cmd.split()[-1] if len(cmd.split()) > 1 else "")
        if not proposal_id:
            return "[CANONIZE] No proposal ID. Usage: canonize: <proposal_id>"
        if _INTEGRATION_AVAILABLE:
            result = do_apply_canonization(proposal_id)
            return f"[CANONIZE]\n{json.dumps(result, indent=2, default=str)}"
        return "[CANONIZE] Not available."

    # ------------------------------------------------------------
    # STABILITY
    # ------------------------------------------------------------
    if norm.startswith("check stability") or norm == "stability":
        stability = enforce_stability()
        score = stability.get("stability_score")
        risk = stability.get("risk")
        notes = stability.get("notes", {})
        return (
            "=== STABILITY CHECK ===\n"
            f"Stability Score: {score}\n"
            f"Risk:            {risk}\n"
            f"Notes:           {notes}\n"
        )

    # ------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------
    if norm.startswith("show dashboard") or norm == "dashboard":
        return dashboard_summary()

    # ------------------------------------------------------------
    # AUTONOMY GOVERNOR
    # ------------------------------------------------------------
    if norm.startswith("open up autonomy") or norm.startswith("open autonomy") or norm.startswith("permissive mode"):
        if governor is not None and hasattr(governor, "set_autonomy_mode"):
            result = governor.set_autonomy_mode("permissive")
            return f"[AUTONOMY] Mode set to 'permissive'. {json.dumps(result)}"
        return "[AUTONOMY] Governor module not available."

    if norm.startswith("normal mode") or norm.startswith("guided mode"):
        if governor is not None and hasattr(governor, "set_autonomy_mode"):
            result = governor.set_autonomy_mode("normal")
            return f"[AUTONOMY] Mode set to 'normal'. {json.dumps(result)}"
        return "[AUTONOMY] Governor module not available."

    if norm.startswith("lock down to strict") or norm.startswith("lock down") or norm.startswith("strict mode"):
        if governor is not None and hasattr(governor, "set_autonomy_mode"):
            result = governor.set_autonomy_mode("strict")
            return f"[AUTONOMY] Mode set to 'strict'. {json.dumps(result)}"
        return "[AUTONOMY] Governor module not available."

    # ------------------------------------------------------------
    # VERIFY / EXPLAIN CLAIMS (through integration layer when available)
    # ------------------------------------------------------------
    if norm.startswith("verify this") or norm.startswith("verify:") or norm.startswith("verify "):
        text = claim or _extract_after_colon(cmd)
        if not text:
            return "[VERIFY] No claim provided."
        if _INTEGRATION_AVAILABLE:
            result = do_claim_verification(text)
            return f"[VERIFY]\n{json.dumps(result, indent=2, default=str)}"
        item_id = verify_and_ingest(text, source="verified")
        return f"[VERIFY] Claim ingested and marked verified. Item ID: {item_id}"

    if norm.startswith("explain this") or norm.startswith("explain:") or norm.startswith("explain "):
        text = claim or _extract_after_colon(cmd)
        if not text:
            return "[EXPLAIN] No claim provided."
        if _INTEGRATION_AVAILABLE:
            try:
                from knowledge.integration_layer import do_reasoning
                result = do_reasoning(text)
                return f"[EXPLAIN]\n{json.dumps(result, indent=2, default=str)}"
            except ImportError:
                pass
        if _META_AVAILABLE:
            try:
                from knowledge.reasoning_engine import reason_about_claim
                result = reason_about_claim(text)
                return f"[EXPLAIN]\n{json.dumps(result, indent=2, default=str)}"
            except Exception:
                pass
        return f"[EXPLAIN] Explanation requested for:\n{text}"

    # ------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------
    return f"[UNKNOWN COMMAND] I didn't recognize: {cmd!r}"
