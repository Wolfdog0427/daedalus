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
from typing import Dict, Any, List, Optional

from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import compute_trust_score
from knowledge.consistency_checker import run_consistency_check
from knowledge.knowledge_graph import (
    compute_entity_centrality,
    get_connected_components,
    get_neighbors,
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
        "curiosity": True,
        "batch_ingestion": True,
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
        "shallow_clusters": 0,
        "frontier_domains": 0,
    },
    "blind_spots": [],
    "coverage_gaps": [],
    "frontier_domains": [],
    "subsystem_health": {},
    "storage": {},
    "trust_distribution": [],
}


# ------------------------------------------------------------
# INTERNAL ANALYSIS HELPERS
# ------------------------------------------------------------

_QUALITY_EMA_ALPHA_UP = 0.6
_QUALITY_EMA_ALPHA_DOWN = 0.35
_quality_ema: Optional[float] = None


def _compute_knowledge_quality(sample_cap: int = 2000) -> float:
    """
    Computes average trust score using reservoir sampling with
    asymmetric EMA damping (D3).

    At scale (millions of items), scanning every item per cycle
    is prohibitive. Reservoir sampling gives a statistically
    representative estimate in O(n) time but bounded memory,
    and the trust-score computation only runs on the sample.

    D3: Output is smoothed via asymmetric EMA. Improvements track
    faster (0.6) than declines (0.35), preventing random sample
    variance from eroding a legitimately high quality score.
    """
    global _quality_ema
    import random

    reservoir: list = []
    count = 0

    for item in _iter_items():
        count += 1
        if count <= sample_cap:
            reservoir.append(item)
        else:
            j = random.randint(0, count - 1)
            if j < sample_cap:
                reservoir[j] = item

    if not reservoir:
        return 0.0

    scores = []
    for item in reservoir:
        try:
            scores.append(compute_trust_score(item))
        except Exception:
            continue

    raw = sum(scores) / len(scores) if scores else 0.0

    if _quality_ema is None:
        _quality_ema = raw
    else:
        alpha = _QUALITY_EMA_ALPHA_UP if raw >= _quality_ema else _QUALITY_EMA_ALPHA_DOWN
        _quality_ema = alpha * raw + (1 - alpha) * _quality_ema

    return _quality_ema


# P3 + B5: Asymmetric coherence damper.
# When coherence is improving (raw > EMA), use alpha 0.6 to track faster.
# When coherence is declining (raw < EMA), use alpha 0.4 to resist harder.
# This lets genuine structural gains (from compaction) register quickly
# while still preventing sawtooth oscillation from transient dips.
_COHERENCE_EMA_ALPHA_UP = 0.6
_COHERENCE_EMA_ALPHA_DOWN = 0.4
_coherence_ema: Optional[float] = None


def _compute_graph_coherence() -> float:
    """
    Measures coherence based on:
    - component fragmentation ratio (entities / components)
    - centrality density (structured entities / total entities)

    P3+B5: Output is smoothed via asymmetric EMA. Improvements track
    faster (alpha=0.6) than declines (alpha=0.4), so compaction gains
    register quickly while random dips are damped harder.
    """
    global _coherence_ema

    centrality = compute_entity_centrality()
    components = get_connected_components()

    if not centrality:
        return _coherence_ema if _coherence_ema is not None else 0.0

    total_entities = sum(len(c) for c in components) if components else len(centrality)
    num_components = max(1, len(components))

    avg_component_size = total_entities / num_components
    comp_factor = min(1.0, avg_component_size / max(total_entities * 0.1, 1))
    cent_factor = min(1.0, len(centrality) / max(total_entities * 0.1, 1))

    raw = (comp_factor * 0.6) + (cent_factor * 0.4)

    if _coherence_ema is None:
        _coherence_ema = raw
    else:
        alpha = _COHERENCE_EMA_ALPHA_UP if raw >= _coherence_ema else _COHERENCE_EMA_ALPHA_DOWN
        _coherence_ema = alpha * raw + (1 - alpha) * _coherence_ema

    return _coherence_ema


_CONSISTENCY_EMA_ALPHA_UP = 0.6
_CONSISTENCY_EMA_ALPHA_DOWN = 0.35
_consistency_ema: Optional[float] = None


def _compute_consistency_score(consistency_report: Dict[str, Any]) -> float:
    """
    Converts consistency report into a scale-independent consistency
    score using severity-weighted defect rates with asymmetric EMA damping.

    Design properties:
    1. Scale-independent — expressed as defect *rate* (defects / items),
       so a 7M-item KB with 70 contradictions scores the same as a
       700-item KB with 7.
    2. Severity-weighted — contradictions and relation conflicts count
       10x more than duplicates or outdated items, because they
       directly degrade user-facing answer quality.
    3. Bounded — output is always in [0.05, 1.0] regardless of scale.
    4. Asymmetric EMA (C2-v3) — improvements tracked faster (0.6),
       declines resisted harder (0.35). Prevents random noise from
       eroding hard-won consistency gains.
    """
    global _consistency_ema

    s = consistency_report["summary"]
    total_items = s.get("total_items", 0)

    if total_items == 0:
        return 1.0

    WEIGHT_CONTRADICTION = 10.0
    WEIGHT_RELATION_CONFLICT = 8.0
    WEIGHT_RELATION_CYCLE = 5.0
    WEIGHT_LOW_TRUST = 2.0
    WEIGHT_OUTDATED = 1.0
    WEIGHT_DUPLICATE = 0.5

    weighted_defects = (
        s["contradiction_count"] * WEIGHT_CONTRADICTION
        + s["relation_conflict_count"] * WEIGHT_RELATION_CONFLICT
        + s["relation_cycle_count"] * WEIGHT_RELATION_CYCLE
        + s["low_trust_count"] * WEIGHT_LOW_TRUST
        + s["outdated_count"] * WEIGHT_OUTDATED
        + s["duplicate_count"] * WEIGHT_DUPLICATE
    )

    defect_rate = weighted_defects / total_items
    raw = 1.0 / (1.0 + defect_rate * 100)
    raw = max(0.05, min(1.0, raw))

    if _consistency_ema is None:
        _consistency_ema = raw
    else:
        alpha = _CONSISTENCY_EMA_ALPHA_UP if raw >= _consistency_ema else _CONSISTENCY_EMA_ALPHA_DOWN
        _consistency_ema = alpha * raw + (1 - alpha) * _consistency_ema

    return _consistency_ema


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


def _identify_coverage_gaps() -> List[Dict[str, Any]]:
    """
    Identifies structured coverage gaps by analyzing graph topology.
    Returns gaps categorized by type for the curiosity engine.
    """
    gaps: List[Dict[str, Any]] = []

    components = get_connected_components()
    shallow = [c for c in components if 1 < len(c) < 3]
    for comp in shallow[:10]:
        gaps.append({
            "type": "shallow_cluster",
            "entities": comp,
            "size": len(comp),
        })

    return gaps


def _identify_frontier_domains() -> List[str]:
    """
    Identifies domains at the frontier of the knowledge graph:
    entities referenced by high-centrality nodes but with minimal
    coverage themselves.
    """
    centrality = compute_entity_centrality()
    central_set = {e for e, _ in centrality[:30]}
    frontiers: List[str] = []

    for entity, _ in centrality[:20]:
        neighbor_edges = get_neighbors(entity)
        for edge in neighbor_edges:
            neighbor = edge["object"]
            if neighbor not in central_set:
                info = _load_entities_raw(neighbor)
                if info and info.get("occurrences", 0) < 2:
                    if neighbor not in frontiers:
                        frontiers.append(neighbor)

    return frontiers[:20]


def _load_entities_raw(entity: str) -> Optional[Dict[str, Any]]:
    """Load a single entity's metadata without full graph load."""
    try:
        from knowledge.knowledge_graph import get_entity_info
        return get_entity_info(entity)
    except Exception:
        return None


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
# SUBSYSTEM HEALTH PROBES
# ------------------------------------------------------------

def _probe_subsystem_health() -> Dict[str, str]:
    """
    Lightweight probes per subsystem. Each probe attempts a minimal
    operation; failure yields "degraded" or "down" instead of a
    hardcoded "ok".
    """
    health: Dict[str, str] = {}

    # Retrieval: try iterating one item from the knowledge store
    try:
        item_iter = _iter_items()
        next(item_iter, None)
        health["retrieval"] = "ok"
    except Exception:
        health["retrieval"] = "down"

    # Trust scoring: try computing a score on a synthetic item
    try:
        compute_trust_score({"id": "_probe", "text": "probe", "source": "self_model"})
        health["trust_scoring"] = "ok"
    except Exception:
        health["trust_scoring"] = "down"

    # Verification: check that the pipeline module is importable
    try:
        from knowledge.verification_pipeline import verify_new_information  # noqa: F401
        health["verification"] = "ok"
    except ImportError:
        health["verification"] = "down"
    except Exception:
        health["verification"] = "degraded"

    # Graph: try loading the graph file
    try:
        from knowledge.knowledge_graph import _load_graph
        g = _load_graph()
        health["graph"] = "ok" if isinstance(g, dict) else "degraded"
    except Exception:
        health["graph"] = "down"

    # Pattern extractor: try extracting from a trivial string
    try:
        extract_patterns()
        health["pattern_extractor"] = "ok"
    except Exception:
        health["pattern_extractor"] = "degraded"

    # Consistency checker: module importable and callable
    try:
        from knowledge.consistency_checker import run_consistency_check as _cc
        health["consistency_checker"] = "ok" if callable(_cc) else "degraded"
    except Exception:
        health["consistency_checker"] = "down"

    # Storage manager: try getting usage stats
    try:
        usage = get_storage_usage()
        health["storage_manager"] = "ok" if isinstance(usage, dict) else "degraded"
    except Exception:
        health["storage_manager"] = "down"

    return health


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

    # Coverage gaps and frontier analysis
    coverage_gaps = _identify_coverage_gaps()
    SELF_MODEL["coverage"]["shallow_clusters"] = len(
        [g for g in coverage_gaps if g["type"] == "shallow_cluster"]
    )
    SELF_MODEL["coverage_gaps"] = coverage_gaps

    frontier_domains = _identify_frontier_domains()
    SELF_MODEL["coverage"]["frontier_domains"] = len(frontier_domains)
    SELF_MODEL["frontier_domains"] = frontier_domains

    # Blind spots
    SELF_MODEL["blind_spots"] = _identify_blind_spots(patterns)

    # Storage
    SELF_MODEL["storage"] = get_storage_usage()

    # Trust distribution
    SELF_MODEL["trust_distribution"] = _compute_trust_distribution()

    SELF_MODEL["subsystem_health"] = _probe_subsystem_health()

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
        "shallow_clusters": SELF_MODEL["coverage"]["shallow_clusters"],
        "frontier_domains": SELF_MODEL["coverage"]["frontier_domains"],
        "blind_spots": SELF_MODEL["blind_spots"][:10],
        "coverage_gaps": len(SELF_MODEL["coverage_gaps"]),
        "frontier_domain_list": SELF_MODEL["frontier_domains"][:10],
        "storage_used": SELF_MODEL["storage"].get("used_bytes"),
        "storage_ratio": SELF_MODEL["storage"].get("ratio"),
    }
