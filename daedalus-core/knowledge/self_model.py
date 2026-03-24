# knowledge/self_model.py

"""
Self Model

This module maintains a structured, evolving model of the system itself:
- capabilities
- limitations
- confidence levels
- subsystem health
- knowledge coverage
- blind spots
- reasoning strengths
- storage status
- trust distribution

It integrates signals from:
- retrieval
- trust scoring
- consistency checker
- knowledge graph
- storage manager
- reasoning engine

This is the system's meta-cognition layer.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List

from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import compute_trust_score
from knowledge.consistency_checker import run_consistency_check
from knowledge.knowledge_graph import (
    compute_entity_centrality,
    get_connected_components,
)
from knowledge.storage_manager import get_storage_usage
from knowledge.pattern_extractor import extract_patterns


# ------------------------------------------------------------
# SELF-MODEL STRUCTURE
# ------------------------------------------------------------

SELF_MODEL: Dict[str, Any] = {
    "last_updated": None,
    "capabilities": {
        "ingestion": True,
        "retrieval": True,
        "trust_scoring": True,
        "verification": True,
        "reasoning": True,
        "graph_reasoning": True,
        "pattern_extraction": True,
        "concept_evolution": True,
    },
    "limitations": {
        "no_raw_web_access": True,
        "no_unbounded_memory": True,
        "no_unverified_replacements": True,
        "no_unsafe_autonomy": True,
    },
    "confidence": {
        "knowledge_quality": 0.0,
        "graph_coherence": 0.0,
        "consistency": 0.0,
    },
    "coverage": {
        "entity_count": 0,
        "relation_count": 0,
        "topic_clusters": 0,
    },
    "blind_spots": [],
    "subsystem_health": {},
    "storage": {},
    "trust_distribution": [],
}


# ------------------------------------------------------------
# INTERNAL ANALYSIS HELPERS
# ------------------------------------------------------------

def _compute_knowledge_quality() -> float:
    """
    Computes average trust score across the knowledge base.
    """
    scores = []
    for item in _iter_items():
        try:
            scores.append(compute_trust_score(item))
        except Exception:
            continue

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def _compute_graph_coherence() -> float:
    """
    Measures coherence based on:
    - centrality distribution
    - number of connected components
    """
    centrality = compute_entity_centrality()
    components = get_connected_components()

    if not centrality:
        return 0.0

    # Fewer components = more coherence
    comp_factor = max(0.1, 1.0 / len(components))

    # Higher centrality = more structure
    cent_factor = min(1.0, len(centrality) / 100)

    return (comp_factor * 0.6) + (cent_factor * 0.4)


def _compute_consistency_score(consistency_report: Dict[str, Any]) -> float:
    """
    Converts consistency report into a coherence score.
    """
    total_issues = (
        consistency_report["summary"]["contradiction_count"]
        + consistency_report["summary"]["low_trust_count"]
        + consistency_report["summary"]["duplicate_count"]
        + consistency_report["summary"]["relation_conflict_count"]
        + consistency_report["summary"]["relation_cycle_count"]
        + consistency_report["summary"]["outdated_count"]
    )

    # More issues = lower consistency
    if total_issues == 0:
        return 1.0

    return max(0.05, 1.0 / (1 + total_issues / 10))


def _identify_blind_spots(patterns: Dict[str, Any]) -> List[str]:
    """
    Identifies blind spots based on:
    - missing entities
    - sparse clusters
    - low-frequency topics
    """
    keywords = patterns["keyword_frequency"]
    if not keywords:
        return ["insufficient_data"]

    low_freq = [kw for kw, freq in keywords if freq == 1]
    return low_freq[:20]


def _compute_trust_distribution() -> List[Dict[str, Any]]:
    """
    Returns distribution of trust scores across the knowledge base.
    """
    dist = []
    for item in _iter_items():
        try:
            dist.append({
                "id": item["id"],
                "score": compute_trust_score(item),
            })
        except Exception:
            continue

    dist.sort(key=lambda x: x["score"])
    return dist[:200]  # safety cap


# ------------------------------------------------------------
# SELF-MODEL UPDATE
# ------------------------------------------------------------

def update_self_model() -> Dict[str, Any]:
    """
    Recomputes the entire self-model.
    """
    global SELF_MODEL

    consistency = run_consistency_check()
    patterns = extract_patterns()

    SELF_MODEL["last_updated"] = time.time()

    # Confidence metrics
    SELF_MODEL["confidence"]["knowledge_quality"] = _compute_knowledge_quality()
    SELF_MODEL["confidence"]["graph_coherence"] = _compute_graph_coherence()
    SELF_MODEL["confidence"]["consistency"] = _compute_consistency_score(consistency)

    # Coverage
    SELF_MODEL["coverage"]["entity_count"] = len(patterns["entity_frequency"])
    SELF_MODEL["coverage"]["relation_count"] = len(patterns["relations"])
    SELF_MODEL["coverage"]["topic_clusters"] = len(patterns["topic_clusters"])

    # Blind spots
    SELF_MODEL["blind_spots"] = _identify_blind_spots(patterns)

    # Storage
    SELF_MODEL["storage"] = get_storage_usage()

    # Trust distribution
    SELF_MODEL["trust_distribution"] = _compute_trust_distribution()

    # Subsystem health (simple for now)
    SELF_MODEL["subsystem_health"] = {
        "retrieval": "ok",
        "trust_scoring": "ok",
        "verification": "ok",
        "graph": "ok",
        "pattern_extractor": "ok",
        "consistency_checker": "ok",
        "storage_manager": "ok",
    }

    return SELF_MODEL


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------

def get_self_model() -> Dict[str, Any]:
    """
    Returns the current self-model.
    """
    return SELF_MODEL


def summarize_self_model() -> Dict[str, Any]:
    """
    Returns a human-readable summary of the system's self-understanding.
    """
    return {
        "knowledge_quality": SELF_MODEL["confidence"]["knowledge_quality"],
        "graph_coherence": SELF_MODEL["confidence"]["graph_coherence"],
        "consistency": SELF_MODEL["confidence"]["consistency"],
        "entity_count": SELF_MODEL["coverage"]["entity_count"],
        "relation_count": SELF_MODEL["coverage"]["relation_count"],
        "topic_clusters": SELF_MODEL["coverage"]["topic_clusters"],
        "blind_spots": SELF_MODEL["blind_spots"][:10],
        "storage_used": SELF_MODEL["storage"].get("used_bytes"),
        "storage_ratio": SELF_MODEL["storage"].get("ratio"),
  }
