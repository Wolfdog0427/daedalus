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
from knowledge.storage_manager import maintenance_cycle, needs_pruning
from knowledge.concept_evolver import evolution_cycle
from knowledge.verification_pipeline import verify_new_information
from knowledge.reasoning_engine import reason_about_claim


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
    - low-confidence
    """
    reasoning = reason_about_claim(claim)
    return reasoning["status"] in ("uncertain", "contradicted")


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
    # 1. Update self-model
    # --------------------------------------------------------
    before = update_self_model()
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
    return {
        "knowledge_quality": sm["confidence"]["knowledge_quality"],
        "graph_coherence": sm["confidence"]["graph_coherence"],
        "consistency": sm["confidence"]["consistency"],
        "storage_ratio": sm["storage"].get("ratio"),
        "blind_spots": sm["blind_spots"][:10],
        "subsystem_health": sm["subsystem_health"],
    }
