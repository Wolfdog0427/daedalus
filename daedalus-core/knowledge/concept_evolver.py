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
    get_entity_info,
    get_relations_for,
    compute_entity_centrality,
    get_connected_components,
)
from knowledge.pattern_extractor import extract_entities, extract_relations
from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import compute_trust_score
from knowledge.storage_manager import replace_item
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
    """
    from knowledge.knowledge_graph import _load_graph, _save_graph, _load_entities, _save_entities

    graph = _load_graph()
    entities = _load_entities()

    # Redirect edges
    for subj, edges in graph.items():
        for edge in edges:
            if edge["object"] == b:
                edge["object"] = a

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
    """
    neighbors = get_neighbors(entity)
    refined = []

    for edge in neighbors:
        trust = edge["trust"]
        relation = edge["relation"]
        obj = edge["object"]

        # Strengthen if repeated across cluster
        cluster = get_connected_components()
        cluster_for_entity = None
        for comp in cluster:
            if entity in comp:
                cluster_for_entity = comp
                break

        if cluster_for_entity:
            freq = sum(
                1 for e in cluster_for_entity
                for r, o in get_relations_for(e)
                if r == relation and o == obj
            )
        else:
            freq = 1

        new_strength = min(1.0, trust * 0.7 + (freq / 10) * 0.3)

        refined.append({
            "relation": relation,
            "object": obj,
            "old_trust": trust,
            "new_trust": new_strength,
        })

    return {
        "entity": entity,
        "refined_relations": refined,
    }


# ------------------------------------------------------------
# FULL EVOLUTION CYCLE
# ------------------------------------------------------------

def evolution_cycle() -> Dict[str, Any]:
    """
    Runs a full conceptual evolution cycle:
    - find merge candidates
    - merge similar concepts
    - create abstract concepts
    - refine relationships
    """
    merges = find_merge_candidates()
    merge_results = []

    for a, b, sim in merges[:10]:  # safety cap
        merge_results.append(merge_concepts(a, b))

    abstracts = create_abstract_concepts()

    refined = []
    for concept, _, _ in merges[:10]:
        refined.append(refine_relationships(concept))

    return {
        "merged_concepts": merge_results,
        "abstract_concepts": abstracts,
        "refined_relationships": refined,
    }
