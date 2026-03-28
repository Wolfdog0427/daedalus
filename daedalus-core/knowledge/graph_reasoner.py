# knowledge/graph_reasoner.py

"""
Graph Reasoner

This module performs structured reasoning over the knowledge graph.
It supports:
- multi-hop inference
- trust-weighted path evaluation
- missing-link prediction
- analogy detection
- cluster-based reasoning
- conceptual neighborhood exploration

This is the symbolic reasoning layer that sits on top of the
knowledge graph and supports higher-level cognition.
"""

from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, deque

from knowledge.knowledge_graph import (
    get_neighbors,
    get_entity_info,
    find_path,
    compute_entity_centrality,
    get_connected_components,
    get_relations_for,
)
from knowledge.retrieval import search_knowledge


# ------------------------------------------------------------
# MULTI-HOP REASONING
# ------------------------------------------------------------

def infer_relationship(start: str, end: str, max_depth: int = 4) -> Dict[str, Any]:
    """
    Attempts to infer a relationship between two entities using:
    - direct edges
    - multi-hop paths
    - trust-weighted evaluation
    """
    # Direct relations first
    direct = get_relations_for(start)
    direct_matches = [rel for rel in direct if rel[1] == end]

    if direct_matches:
        return {
            "type": "direct",
            "path": [start, end],
            "relations": direct_matches,
            "confidence": 0.9,
        }

    # Multi-hop search
    path = find_path(start, end, max_depth=max_depth)
    if path:
        return {
            "type": "multi-hop",
            "path": path,
            "confidence": max(0.3, 0.8 - 0.1 * (len(path) - 2)),
        }

    return {
        "type": "none",
        "path": None,
        "confidence": 0.0,
    }


# ------------------------------------------------------------
# MISSING LINK PREDICTION
# ------------------------------------------------------------

def predict_missing_links(entity: str, limit: int = 10) -> List[Tuple[str, float]]:
    """
    Predicts missing relationships by:
    - looking at neighbors of neighbors
    - scoring based on frequency and trust
    """
    neighbors = get_neighbors(entity)
    second_hop = defaultdict(float)

    for edge in neighbors:
        nxt = edge["object"]
        nxt_neighbors = get_neighbors(nxt)

        for edge2 in nxt_neighbors:
            candidate = edge2["object"]
            if candidate == entity:
                continue
            second_hop[candidate] += edge.get("trust", 0.5) * 0.5 + edge2.get("trust", 0.5) * 0.5

    ranked = sorted(second_hop.items(), key=lambda x: x[1], reverse=True)
    return ranked[:limit]


# ------------------------------------------------------------
# ANALOGY DETECTION
# ------------------------------------------------------------

def find_analogies(entity: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Finds entities with similar relationship patterns.
    """
    base_relations = get_relations_for(entity)
    base_patterns = {(rel, obj) for rel, obj in base_relations}

    analogies = []

    # Compare with central entities first
    central = compute_entity_centrality()[:200]

    for other, _ in central:
        if other == entity:
            continue

        other_relations = get_relations_for(other)
        other_patterns = {(rel, obj) for rel, obj in other_relations}

        overlap = len(base_patterns & other_patterns)
        if overlap > 0:
            analogies.append({
                "entity": other,
                "overlap": overlap,
                "shared_relations": list(base_patterns & other_patterns),
            })

    analogies.sort(key=lambda x: x["overlap"], reverse=True)
    return analogies[:limit]


# ------------------------------------------------------------
# CLUSTER-AWARE REASONING
# ------------------------------------------------------------

def get_entity_cluster(entity: str) -> Optional[List[str]]:
    """
    Returns the connected component containing the entity.
    """
    components = get_connected_components()
    for comp in components:
        if entity in comp:
            return comp
    return None


def cluster_summary(entity: str) -> Dict[str, Any]:
    """
    Summarizes the conceptual cluster around an entity.
    """
    cluster = get_entity_cluster(entity)
    if not cluster:
        return {
            "entity": entity,
            "cluster": None,
            "size": 0,
            "top_relations": [],
        }

    relation_counts = defaultdict(int)
    for e in cluster:
        for rel, obj in get_relations_for(e):
            relation_counts[rel] += 1

    top_relations = sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "entity": entity,
        "cluster": cluster[:50],  # safety cap
        "size": len(cluster),
        "top_relations": top_relations[:10],
    }


# ------------------------------------------------------------
# GRAPH-BASED CLAIM REASONING
# ------------------------------------------------------------

def reason_over_graph(claim: str) -> Dict[str, Any]:
    """
    Uses the graph to reason about a claim by:
    - retrieving relevant entities
    - checking their relationships
    - inferring likely connections
    """
    # Extract candidate entities from the claim
    candidates = search_knowledge(claim, limit=5)
    entities = []

    for c in candidates:
        ents = []
        for word in c.text.split():
            if word.istitle():
                ents.append(word)
        entities.extend(ents)

    entities = list(set(entities))

    if not entities:
        return {
            "claim": claim,
            "status": "no_entities_found",
            "reasoning": [],
        }

    reasoning_steps = []

    for e in entities:
        info = get_entity_info(e)
        if info:
            reasoning_steps.append({
                "entity": e,
                "occurrences": info["occurrences"],
                "sources": info["sources"][:5],
            })

    # Try to infer relationships between all pairs
    inferred = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            a = entities[i]
            b = entities[j]
            rel = infer_relationship(a, b)
            inferred.append({
                "pair": (a, b),
                "inference": rel,
            })

    return {
        "claim": claim,
        "entities": entities,
        "inferred_relationships": inferred,
        "entity_context": reasoning_steps,
    }
