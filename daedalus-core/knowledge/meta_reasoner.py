# knowledge/meta_reasoner.py

"""
Meta Reasoner

This module performs meta-cognition:
- reads the self-model
- evaluates subsystem health
- detects when maintenance is needed
- triggers safe, governed actions
- escalates to the user when human approval is required
- coordinates long-term stability

It does NOT modify knowledge directly.
It orchestrates other modules safely.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List

from knowledge.self_model import update_self_model, get_self_model
from knowledge.consistency_checker import run_consistency_check
from knowledge.storage_manager import maintenance_cycle
from knowledge.concept_evolver import evolution_cycle
from knowledge.verification_pipeline import verify_new_information
from knowledge.reasoning_engine import reason_about_claim
from knowledge.curiosity_engine import run_curiosity_cycle
from knowledge.batch_ingestion import verify_deferred_items

try:
    from knowledge.provider_discovery import (
        run_discovery_cycle,
        provider_registry,
    )
    _DISCOVERY_AVAILABLE = True
except ImportError:
    _DISCOVERY_AVAILABLE = False

try:
    from knowledge.flow_tuner import flow_tuner as _flow_tuner
    _FLOW_TUNER_AVAILABLE = True
except ImportError:
    _FLOW_TUNER_AVAILABLE = False


# ------------------------------------------------------------
# DECISION RULES
# ------------------------------------------------------------

def _needs_concept_evolution(self_model: Dict[str, Any]) -> bool:
    """
    Trigger concept evolution when:
    - graph coherence is low
    - entity count is high
    - topic clusters are fragmented
    """
    coherence = self_model["confidence"]["graph_coherence"]
    clusters = self_model["coverage"]["topic_clusters"]

    return coherence < 0.45 or clusters > 50


def _needs_consistency_repair(self_model: Dict[str, Any]) -> bool:
    """
    Trigger consistency repair when:
    - consistency score is low
    - many contradictions or conflicts exist
    """
    consistency = self_model["confidence"]["consistency"]
    return consistency < 0.5


def _needs_storage_maintenance(self_model: Dict[str, Any]) -> bool:
    """
    Trigger storage maintenance when:
    - storage ratio is high
    - free space is low
    """
    storage = self_model["storage"]
    return storage.get("ratio", 0) > 0.85


def _needs_verification(claim: str) -> bool:
    """
    Trigger verification when a claim is:
    - uncertain
    - contradictory
    - unknown (no relevant data found)
    """
    reasoning = reason_about_claim(claim)
    return reasoning["status"] in ("uncertain", "contradicted", "unknown")


def _needs_knowledge_expansion(self_model: Dict[str, Any]) -> bool:
    """
    Trigger curiosity-driven knowledge expansion when:
    - blind spots exceed a threshold
    - coverage gaps are detected (shallow clusters, frontier domains)
    - graph coherence would benefit from broader coverage

    This does NOT expand autonomy or modify behavior. It proposes
    knowledge acquisition goals that flow through the tier system.
    """
    blind_spots = self_model.get("blind_spots", [])
    coverage_gaps = self_model.get("coverage_gaps", [])
    frontier_domains = self_model.get("frontier_domains", [])
    coherence = self_model["confidence"]["graph_coherence"]

    has_blind_spots = len(blind_spots) > 5
    has_coverage_gaps = len(coverage_gaps) > 0
    has_frontiers = len(frontier_domains) > 0
    low_coherence = coherence < 0.5

    return has_blind_spots or has_coverage_gaps or has_frontiers or low_coherence


def _needs_deferred_verification(self_model: Dict[str, Any]) -> bool:
    """
    Trigger background verification of provisionally-ingested items.
    Runs when the system is otherwise healthy (not in maintenance).
    """
    consistency = self_model["confidence"]["consistency"]
    coherence = self_model["confidence"]["graph_coherence"]
    return consistency > 0.5 and coherence > 0.4


def _needs_provider_discovery(self_model: Dict[str, Any]) -> bool:
    """
    Trigger provider discovery when the system might benefit from
    LLM/AGI assistance but none is connected, or periodically to
    check for upgrades/new providers.
    """
    if not _DISCOVERY_AVAILABLE:
        return False
    active = provider_registry.get_active_count()
    if active == 0:
        return True
    has_expansion_need = _needs_knowledge_expansion(self_model)
    return has_expansion_need


def _needs_flow_tuning() -> bool:
    """Trigger flow tuning when the pipeline has enough metric data."""
    if not _FLOW_TUNER_AVAILABLE:
        return False
    return _flow_tuner.metrics.batch_throughput.count() >= 5


# ------------------------------------------------------------
# META-REASONING ACTIONS
# ------------------------------------------------------------

def run_meta_cycle(claim: str | None = None) -> Dict[str, Any]:
    """
    Runs a full meta-reasoning cycle:
    - updates self-model
    - evaluates system health
    - triggers safe maintenance actions
    - optionally verifies a claim
    - returns a structured meta-report
    """
    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "actions": [],
        "claim_verification": None,
        "self_model_before": None,
        "self_model_after": None,
    }

    # --------------------------------------------------------
    # 1. Update self-model (throttled by flow tuner interval)
    # --------------------------------------------------------
    _sm_interval = 30.0
    if _FLOW_TUNER_AVAILABLE:
        _sm_interval = _flow_tuner.get_recommended_self_model_interval()
    last_model = get_self_model()
    last_updated = last_model.get("last_updated", 0)
    if time.time() - last_updated >= _sm_interval:
        before = update_self_model()
    else:
        before = last_model
    report["self_model_before"] = before

    # --------------------------------------------------------
    # 2. Decide actions based on self-model
    # --------------------------------------------------------

    # Storage maintenance
    if _needs_storage_maintenance(before):
        result = maintenance_cycle()
        report["actions"].append({
            "type": "storage_maintenance",
            "result": result,
        })

    # Consistency repair
    if _needs_consistency_repair(before):
        consistency = run_consistency_check()
        report["actions"].append({
            "type": "consistency_repair",
            "result": consistency,
        })

    # Concept evolution
    if _needs_concept_evolution(before):
        evo = evolution_cycle()
        report["actions"].append({
            "type": "concept_evolution",
            "result": evo,
        })

    # Knowledge expansion (curiosity engine)
    if _needs_knowledge_expansion(before):
        curiosity_report = run_curiosity_cycle(self_model=before)
        report["actions"].append({
            "type": "knowledge_expansion",
            "result": curiosity_report,
        })

    # Deferred verification (background processing of provisional items)
    if _needs_deferred_verification(before):
        deferred_report = verify_deferred_items(limit=10)
        report["actions"].append({
            "type": "deferred_verification",
            "result": deferred_report,
        })

    # Provider discovery (find/upgrade LLM/AGI providers)
    if _needs_provider_discovery(before):
        try:
            discovery_report = run_discovery_cycle(provider_registry)
            report["actions"].append({
                "type": "provider_discovery",
                "result": discovery_report,
            })
        except Exception as e:
            report["actions"].append({
                "type": "provider_discovery",
                "result": {"error": str(e)},
            })

    # Flow tuning (optimize pipeline parameters)
    if _needs_flow_tuning():
        try:
            tuning_report = _flow_tuner.tune()
            report["actions"].append({
                "type": "flow_tuning",
                "result": tuning_report,
            })
        except Exception as e:
            report["actions"].append({
                "type": "flow_tuning",
                "result": {"error": str(e)},
            })

    # --------------------------------------------------------
    # 3. Optional claim verification
    # --------------------------------------------------------
    if claim is not None:
        if _needs_verification(claim):
            verification = verify_new_information(
                claim,
                source="meta_reasoner",
                use_web=False,
            )
            report["claim_verification"] = verification
            report["actions"].append({
                "type": "claim_verification",
                "claim": claim,
                "result": verification,
            })
        else:
            report["claim_verification"] = {
                "status": "no_verification_needed",
                "claim": claim,
            }

    # --------------------------------------------------------
    # 4. Update self-model again after actions
    # --------------------------------------------------------
    after = update_self_model()
    report["self_model_after"] = after

    return report


# ------------------------------------------------------------
# HIGH-LEVEL META-QUERIES
# ------------------------------------------------------------

def meta_status() -> Dict[str, Any]:
    """
    Returns a high-level summary of system health and meta-state.
    """
    sm = get_self_model()

    status: Dict[str, Any] = {
        "knowledge_quality": sm["confidence"]["knowledge_quality"],
        "graph_coherence": sm["confidence"]["graph_coherence"],
        "consistency": sm["confidence"]["consistency"],
        "storage_ratio": sm["storage"].get("ratio"),
        "blind_spots": sm["blind_spots"][:10],
        "coverage_gaps": len(sm.get("coverage_gaps", [])),
        "frontier_domains": sm.get("frontier_domains", [])[:10],
        "expansion_needed": _needs_knowledge_expansion(sm),
        "subsystem_health": sm["subsystem_health"],
    }

    if _DISCOVERY_AVAILABLE:
        status["active_providers"] = provider_registry.get_active_count()
        status["provider_notifications"] = len(
            provider_registry.get_notifications(unacknowledged_only=True)
        )

    if _FLOW_TUNER_AVAILABLE:
        status["flow_tuner"] = _flow_tuner.dashboard()

    return status
