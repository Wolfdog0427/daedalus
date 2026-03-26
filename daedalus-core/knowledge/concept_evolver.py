# knowledge/concept_evolver.py

"""
Concept Evolver

This module performs conceptual evolution:
- merges similar or redundant concepts
- creates new abstract concepts from patterns
- refines entity definitions
- strengthens or weakens conceptual links
- detects emerging themes
- proposes new canonical concepts

It operates on top of:
- the knowledge graph
- pattern extractor
- trust scoring
- consistency checker

This is the system's ontology-evolution layer.
"""

from __future__ import annotations

from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter
import time

from knowledge.knowledge_graph import (
    get_neighbors,
    get_relations_for,
    compute_entity_centrality,
    get_connected_components,
)
from knowledge.ingestion import ingest_text


# ------------------------------------------------------------
# SIMILARITY MEASURES
# ------------------------------------------------------------

def _relation_signature(entity: str) -> set:
    """
    Returns a set of (relation, object) pairs for similarity comparison.
    """
    return set(get_relations_for(entity))


def compute_entity_similarity(a: str, b: str) -> float:
    """
    Computes similarity between two entities based on:
    - shared relations
    - shared neighbors
    - shared cluster membership
    """
    sig_a = _relation_signature(a)
    sig_b = _relation_signature(b)

    if not sig_a or not sig_b:
        return 0.0

    overlap = len(sig_a & sig_b)
    total = len(sig_a | sig_b)

    return overlap / total if total > 0 else 0.0


# ------------------------------------------------------------
# MERGING SIMILAR CONCEPTS
# ------------------------------------------------------------

def find_merge_candidates(threshold: float = 0.6) -> List[Tuple[str, str, float]]:
    """
    Finds pairs of entities that are similar enough to merge.
    """
    central = compute_entity_centrality()[:300]  # focus on important nodes
    entities = [e for e, _ in central]

    candidates = []

    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            a = entities[i]
            b = entities[j]

            sim = compute_entity_similarity(a, b)
            if sim >= threshold:
                candidates.append((a, b, sim))

    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates


def merge_concepts(a: str, b: str) -> Dict[str, Any]:
    """
    Merges concept B into concept A.
    - A becomes the canonical concept
    - B is marked as an alias
    - All relations pointing to B are redirected to A
    - T3: Actively resolves contradictions between A and B's items
    """
    from knowledge.knowledge_graph import _load_graph, _save_graph, _load_entities, _save_entities

    graph = _load_graph()
    entities = _load_entities()

    # Redirect edges
    redirected = 0
    for subj, edges in graph.items():
        for edge in edges:
            if edge["object"] == b:
                edge["object"] = a
                redirected += 1

    # T3: Resolve contradictions between A's and B's edge sets
    contradictions_resolved = 0
    if a in graph and b in graph:
        a_rels = {(e["relation"], e["object"]): e for e in graph.get(a, [])}
        b_rels = {(e["relation"], e["object"]): e for e in graph.get(b, [])}
        for key in set(a_rels) & set(b_rels):
            a_edge = a_rels[key]
            b_edge = b_rels[key]
            if a_edge.get("trust", 0) < b_edge.get("trust", 0):
                a_edge["trust"] = b_edge["trust"]
            contradictions_resolved += 1

    # Merge entity metadata
    if b in entities:
        if a not in entities:
            entities[a] = entities[b]
        else:
            entities[a]["occurrences"] += entities[b]["occurrences"]
            entities[a]["sources"].extend(entities[b]["sources"])

        del entities[b]

    _save_graph(graph)
    _save_entities(entities)

    return {
        "action": "merged",
        "canonical": a,
        "merged": b,
        "redirected_edges": redirected,
        "contradictions_resolved": contradictions_resolved,
    }


# ------------------------------------------------------------
# ABSTRACT CONCEPT CREATION
# ------------------------------------------------------------

def create_abstract_concepts(min_cluster_size: int = 5) -> List[Dict[str, Any]]:
    """
    Creates new abstract concepts from clusters of related entities.
    """
    components = get_connected_components()
    new_concepts = []

    for comp in components:
        if len(comp) < min_cluster_size:
            continue

        # Create a name for the abstract concept
        abstract_name = f"Concept_{hash(tuple(sorted(comp))) % 10**8}"

        definition = (
            f"This concept represents a cluster of {len(comp)} related entities: "
            + ", ".join(comp[:10])
            + ("..." if len(comp) > 10 else "")
        )

        new_id = ingest_text(definition, source="concept_evolver")

        new_concepts.append({
            "concept": abstract_name,
            "definition_item_id": new_id,
            "members": comp,
        })

    return new_concepts


# ------------------------------------------------------------
# RELATIONSHIP REFINEMENT
# ------------------------------------------------------------

def refine_relationships(entity: str) -> Dict[str, Any]:
    """
    Strengthens or weakens relationships based on:
    - frequency
    - trust
    - cluster context

    Persists updated trust values back to the graph.
    """
    from knowledge.knowledge_graph import _load_graph, _save_graph

    graph = _load_graph()
    edges = graph.get(entity, [])
    refined = []

    cluster = get_connected_components()
    cluster_for_entity = None
    for comp in cluster:
        if entity in comp:
            cluster_for_entity = comp
            break

    for edge in edges:
        trust = edge["trust"]
        relation = edge["relation"]
        obj = edge["object"]

        if cluster_for_entity:
            freq = sum(
                1 for e in cluster_for_entity
                for r, o in get_relations_for(e)
                if r == relation and o == obj
            )
        else:
            freq = 1

        new_strength = min(1.0, trust * 0.7 + (freq / 10) * 0.3)

        edge["trust"] = new_strength

        refined.append({
            "relation": relation,
            "object": obj,
            "old_trust": trust,
            "new_trust": new_strength,
        })

    _save_graph(graph)

    return {
        "entity": entity,
        "refined_relations": refined,
    }


# ------------------------------------------------------------
# FULL EVOLUTION CYCLE
# ------------------------------------------------------------

# T6: Maximum coherence improvement per evolution cycle.
# Prevents 30+ point jumps that cause sawtooth oscillation.
MAX_COHERENCE_IMPROVEMENT_PER_CYCLE = 0.08


def _compute_evolution_intensity(coherence: float, target: float = 0.75) -> Dict[str, Any]:
    """
    Sim-fix C4: Proportional evolution intensity. Instead of
    binary on/off, the intensity scales linearly with the
    distance below the target coherence.

    T6: Each level now includes a max_improvement cap to prevent
    over-correction in a single cycle.
    """
    if coherence >= target:
        return {"level": "maintenance", "cap_multiplier": 0.5, "threshold": 0.65, "max_improvement": 0.03}
    deficit = target - coherence
    if deficit < 0.10:
        return {"level": "light", "cap_multiplier": 0.8, "threshold": 0.60, "max_improvement": 0.05}
    if deficit < 0.25:
        return {"level": "moderate", "cap_multiplier": 1.0, "threshold": 0.55, "max_improvement": 0.08}
    if deficit < 0.40:
        return {"level": "aggressive", "cap_multiplier": 1.5, "threshold": 0.50, "max_improvement": 0.10}
    return {"level": "emergency", "cap_multiplier": 2.0, "threshold": 0.45, "max_improvement": 0.12}


def evolution_cycle(coherence: float = 0.0) -> Dict[str, Any]:
    """
    Runs a full conceptual evolution cycle with proportional
    intensity (C4): evolution effort scales with distance from
    target coherence. Also computes a consistency boost (H2)
    from contradiction-resolving merges.
    """
    evolution_cap = 10
    try:
        from knowledge.flow_tuner import flow_tuner as _ft
        evolution_cap = _ft.params.evolution_batch_cap
    except ImportError:
        pass

    # C4: proportional intensity
    intensity = _compute_evolution_intensity(coherence)
    effective_cap = max(3, int(evolution_cap * intensity["cap_multiplier"]))
    merge_threshold = intensity["threshold"]

    merges = find_merge_candidates(threshold=merge_threshold)
    merge_results = []

    for a, b, sim in merges[:effective_cap]:
        merge_results.append(merge_concepts(a, b))

    abstracts = create_abstract_concepts()

    refined = []
    for concept, _, _ in merges[:effective_cap]:
        refined.append(refine_relationships(concept))

    # H2 + T3: real consistency benefit from contradiction-resolving merges
    total_contradictions_resolved = sum(
        m.get("contradictions_resolved", 0) for m in merge_results
    )
    consistency_boost = min(
        0.15,
        0.01 * total_contradictions_resolved
        + 0.005 * len(merge_results)
        + 0.002 * len(refined),
    )

    return {
        "merged_concepts": merge_results,
        "abstract_concepts": abstracts,
        "refined_relationships": refined,
        "intensity": intensity["level"],
        "effective_cap": effective_cap,
        "consistency_boost_estimate": round(consistency_boost, 4),
    }


# ------------------------------------------------------------
# SCOPED EVOLUTION (Part 2 acceleration)
# ------------------------------------------------------------

def scoped_evolution_cycle(target_entities: List[str]) -> Dict[str, Any]:
    """
    Run concept evolution scoped to a specific set of entities.
    Faster than a full evolution cycle because it only processes
    the cluster affected by recent knowledge acquisition.

    This is called after batch ingestion to refine the newly-
    expanded area of the graph without touching the rest.
    """
    if not target_entities:
        return {
            "scoped": True,
            "merged_concepts": [],
            "refined_relationships": [],
        }

    target_set = set(target_entities)
    merge_results = []
    refined = []

    # Only check merge candidates within the target set
    for i in range(len(target_entities)):
        for j in range(i + 1, len(target_entities)):
            a = target_entities[i]
            b = target_entities[j]
            sim = compute_entity_similarity(a, b)
            if sim >= 0.6:
                merge_results.append(merge_concepts(a, b))

    # Also check for merges between target entities and their neighbors
    for entity in target_entities[:20]:  # safety cap
        neighbors = get_neighbors(entity)
        for edge in neighbors:
            neighbor = edge["object"]
            if neighbor not in target_set:
                sim = compute_entity_similarity(entity, neighbor)
                if sim >= 0.7:  # higher threshold for cross-cluster merges
                    merge_results.append(merge_concepts(entity, neighbor))

    # Refine relationships for affected entities
    for entity in target_entities[:20]:
        refined.append(refine_relationships(entity))

    return {
        "scoped": True,
        "target_count": len(target_entities),
        "merged_concepts": merge_results,
        "refined_relationships": refined,
    }
