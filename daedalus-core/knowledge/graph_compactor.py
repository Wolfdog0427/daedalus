# knowledge/graph_compactor.py

"""
Graph Compactor — Primary Coherence Fix

The root cause of coherence degradation at scale is graph fragmentation:
as the knowledge base grows, new entities and relations form isolated
clusters that aren't connected to the main knowledge body. The coherence
metric measures (avg_component_size / total_entities), which drops as
the number of disconnected components grows relative to their size.

This module performs four compaction phases at epoch boundaries:

Phase 1 — Entity Deduplication:
  Merge entities that represent the same concept (e.g., "machine learning"
  and "ML", "United States" and "US"). Uses relation-signature similarity
  from concept_evolver plus string-based heuristics.

Phase 2 — Orphan Pruning:
  Remove entities with zero relations (truly isolated) or a single low-trust
  relation. These contribute to component count without carrying knowledge.

Phase 3 — Fragment Bridging:
  Find small disconnected components and attempt to bridge them to the
  largest component using shared entity-name substring matching and
  relation-type compatibility. This directly increases avg_component_size
  and reduces component count.

Phase 4 — Edge Quality Pruning:
  Remove duplicate edges and very-low-trust edges that add noise without
  improving coherence.

Impact on coherence metric:
  - Fewer components (merges + bridges + orphan removal)
  - Larger average component size (bridges)
  - Higher centrality density (dedup concentrates edges)
  All three factors improve the raw coherence signal.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Tuple, Set
from collections import defaultdict


# ------------------------------------------------------------------
# Phase 1: Entity Deduplication
# ------------------------------------------------------------------

def _string_similarity(a: str, b: str) -> float:
    """Lightweight string similarity for entity-name matching."""
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()

    if a_lower == b_lower:
        return 1.0

    if a_lower in b_lower or b_lower in a_lower:
        return 0.8

    a_tokens = set(a_lower.split())
    b_tokens = set(b_lower.split())
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens & b_tokens)
    total = len(a_tokens | b_tokens)
    return overlap / total if total > 0 else 0.0


def _find_dedup_candidates(
    entities: Dict[str, Dict[str, Any]],
    graph: Dict[str, list],
    threshold: float = 0.7,
    scan_limit: int = 500,
) -> List[Tuple[str, str, float]]:
    """
    Find entity pairs that should be merged based on:
    - String similarity of names
    - Shared relation targets
    """
    entity_list = sorted(
        entities.keys(),
        key=lambda e: entities[e].get("occurrences", 0),
        reverse=True,
    )[:scan_limit]

    candidates = []
    seen = set()

    for i, a in enumerate(entity_list):
        for b in entity_list[i + 1:]:
            if (a, b) in seen or (b, a) in seen:
                continue

            name_sim = _string_similarity(a, b)
            if name_sim < 0.5:
                continue

            a_targets = {e.get("object") for e in graph.get(a, [])}
            b_targets = {e.get("object") for e in graph.get(b, [])}
            shared_targets = len(a_targets & b_targets)
            target_sim = shared_targets / max(len(a_targets | b_targets), 1)

            combined = name_sim * 0.6 + target_sim * 0.4
            if combined >= threshold:
                candidates.append((a, b, combined))
                seen.add((a, b))

    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates


def dedup_entities(
    graph: Dict[str, list],
    entities: Dict[str, Dict[str, Any]],
    merge_limit: int = 50,
) -> Dict[str, Any]:
    """
    Phase 1: Merge duplicate entities.
    Returns the mutated graph/entities and a report.
    """
    candidates = _find_dedup_candidates(entities, graph)
    merged = 0
    redirected_total = 0
    merged_into: Dict[str, str] = {}

    for canonical, duplicate, score in candidates[:merge_limit]:
        if duplicate in merged_into or canonical in merged_into:
            continue

        redirected = 0
        for subj, edges in graph.items():
            for edge in edges:
                if edge.get("object") == duplicate:
                    edge["object"] = canonical
                    redirected += 1

        if duplicate in graph:
            graph.setdefault(canonical, []).extend(graph.pop(duplicate))

        if duplicate in entities:
            if canonical in entities:
                entities[canonical]["occurrences"] = (
                    entities[canonical].get("occurrences", 0)
                    + entities[duplicate].get("occurrences", 0)
                )
                entities[canonical].setdefault("sources", []).extend(
                    entities[duplicate].get("sources", [])
                )
                entities[canonical].setdefault("aliases", []).append(duplicate)
            else:
                entities[canonical] = entities[duplicate]
            del entities[duplicate]

        merged_into[duplicate] = canonical
        merged += 1
        redirected_total += redirected

    return {
        "merged": merged,
        "redirected_edges": redirected_total,
        "candidates_found": len(candidates),
    }


# ------------------------------------------------------------------
# Phase 2: Orphan Pruning
# ------------------------------------------------------------------

def prune_orphans(
    graph: Dict[str, list],
    entities: Dict[str, Dict[str, Any]],
    min_relations: int = 1,
    min_trust: float = 0.2,
) -> Dict[str, Any]:
    """
    Phase 2: Remove entities that have zero meaningful relations.
    An entity is an orphan if:
    - It has no outgoing edges AND no incoming edges, OR
    - All its edges have trust below min_trust
    """
    all_subjects = set(graph.keys())
    all_objects: Set[str] = set()
    for edges in graph.values():
        for edge in edges:
            all_objects.add(edge.get("object", ""))

    connected_entities = all_subjects | all_objects
    entity_names = set(entities.keys())

    true_orphans = entity_names - connected_entities

    low_quality: Set[str] = set()
    for entity in entity_names & connected_entities:
        outgoing = graph.get(entity, [])
        incoming_count = sum(
            1 for edges in graph.values()
            for e in edges
            if e.get("object") == entity
        )

        if len(outgoing) + incoming_count <= min_relations:
            max_trust = max(
                (e.get("trust", 0) for e in outgoing),
                default=0,
            )
            if max_trust < min_trust:
                low_quality.add(entity)

    pruned = true_orphans | low_quality
    for entity in pruned:
        entities.pop(entity, None)
        graph.pop(entity, None)

    if pruned:
        for subj in list(graph):
            edges = graph[subj]
            graph[subj] = [e for e in edges if e.get("object") not in pruned]

    return {
        "true_orphans_removed": len(true_orphans),
        "low_quality_removed": len(low_quality),
        "total_pruned": len(pruned),
    }


# ------------------------------------------------------------------
# Phase 3: Fragment Bridging
# ------------------------------------------------------------------

def _find_components(graph: Dict[str, list]) -> List[Set[str]]:
    """Find connected components using undirected traversal."""
    adjacency: Dict[str, Set[str]] = defaultdict(set)
    for subj, edges in graph.items():
        for edge in edges:
            obj = edge.get("object", "")
            adjacency[subj].add(obj)
            adjacency[obj].add(subj)

    visited: Set[str] = set()
    components: List[Set[str]] = []

    for node in adjacency:
        if node in visited:
            continue
        component: Set[str] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adjacency.get(current, set()):
                if neighbor not in visited:
                    stack.append(neighbor)
        if component:
            components.append(component)

    return sorted(components, key=len, reverse=True)


def bridge_fragments(
    graph: Dict[str, list],
    entities: Dict[str, Dict[str, Any]],
    max_bridges: int = 30,
) -> Dict[str, Any]:
    """
    Phase 3: Bridge small disconnected components to the main cluster.

    Strategy: for each small component, find the entity most similar
    (by name) to any entity in the largest component, and add a
    synthetic "related_to" bridge edge.
    """
    components = _find_components(graph)
    if len(components) <= 1:
        return {"bridges_created": 0, "components_before": len(components)}

    main_component = components[0]
    small_components = components[1:]

    bridges_created = 0
    components_bridged = 0

    for small_comp in small_components:
        if bridges_created >= max_bridges:
            break

        best_sim = 0.0
        best_pair = (None, None)

        for small_entity in small_comp:
            for main_entity in main_component:
                sim = _string_similarity(small_entity, main_entity)
                if sim > best_sim:
                    best_sim = sim
                    best_pair = (small_entity, main_entity)

        if best_sim >= 0.3 and best_pair[0] and best_pair[1]:
            small_entity, main_entity = best_pair
            graph.setdefault(small_entity, []).append({
                "relation": "related_to",
                "object": main_entity,
                "source_item": "graph_compactor_bridge",
                "trust": 0.5,
                "timestamp": time.time(),
                "synthetic": True,
            })
            main_component.update(small_comp)
            bridges_created += 1
            components_bridged += 1

    return {
        "bridges_created": bridges_created,
        "components_bridged": components_bridged,
        "components_before": len(components),
        "components_after": len(components) - components_bridged,
    }


# ------------------------------------------------------------------
# Phase 4: Edge Quality Pruning
# ------------------------------------------------------------------

def prune_low_quality_edges(
    graph: Dict[str, list],
    min_trust: float = 0.1,
    dedup_edges: bool = True,
) -> Dict[str, Any]:
    """
    Phase 4: Remove duplicate and very-low-trust edges.
    """
    removed_low_trust = 0
    removed_duplicates = 0

    for subj in list(graph.keys()):
        edges = graph[subj]
        if not edges:
            continue

        filtered = [e for e in edges if e.get("trust", 0.5) >= min_trust]
        removed_low_trust += len(edges) - len(filtered)

        if dedup_edges and filtered:
            seen_keys: set = set()
            deduped = []
            for edge in filtered:
                key = (edge.get("relation", ""), edge.get("object", ""))
                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped.append(edge)
                else:
                    removed_duplicates += 1
            graph[subj] = deduped
        else:
            graph[subj] = filtered

    return {
        "removed_low_trust": removed_low_trust,
        "removed_duplicates": removed_duplicates,
        "total_removed": removed_low_trust + removed_duplicates,
    }


# ------------------------------------------------------------------
# ORCHESTRATOR
# ------------------------------------------------------------------

def run_compaction(
    merge_limit: int = 50,
    bridge_limit: int = 30,
    min_orphan_trust: float = 0.2,
    min_edge_trust: float = 0.1,
) -> Dict[str, Any]:
    """
    Execute the full 4-phase graph compaction.
    This is the primary coherence fix — called at epoch boundaries.
    """
    from knowledge.knowledge_graph import (
        _load_graph,
        _save_graph,
        _load_entities,
        _save_entities,
        _graph_lock,
    )

    start_time = time.time()
    with _graph_lock:
        graph = _load_graph()
        entities = _load_entities()

        pre_entities = len(entities)
        pre_edges = sum(len(edges) for edges in graph.values())
        pre_components = len(_find_components(graph))

        phase1 = dedup_entities(graph, entities, merge_limit=merge_limit)
        phase2 = prune_orphans(graph, entities, min_trust=min_orphan_trust)
        phase3 = bridge_fragments(graph, entities, max_bridges=bridge_limit)
        phase4 = prune_low_quality_edges(graph, min_trust=min_edge_trust)

        _save_graph(graph)
        _save_entities(entities)

        post_entities = len(entities)
        post_edges = sum(len(edges) for edges in graph.values())
        post_components = len(_find_components(graph))

    elapsed = time.time() - start_time

    return {
        "timestamp": time.time(),
        "elapsed_seconds": round(elapsed, 2),
        "pre": {
            "entities": pre_entities,
            "edges": pre_edges,
            "components": pre_components,
        },
        "post": {
            "entities": post_entities,
            "edges": post_edges,
            "components": post_components,
        },
        "delta": {
            "entities": post_entities - pre_entities,
            "edges": post_edges - pre_edges,
            "components": post_components - pre_components,
        },
        "phase1_dedup": phase1,
        "phase2_orphans": phase2,
        "phase3_bridges": phase3,
        "phase4_edge_quality": phase4,
        "coherence_impact": _estimate_coherence_impact(
            pre_entities, pre_components,
            post_entities, post_components,
        ),
    }


def _estimate_coherence_impact(
    pre_entities: int,
    pre_components: int,
    post_entities: int,
    post_components: int,
) -> Dict[str, Any]:
    """Estimate how much the compaction improved the coherence signal."""
    if pre_entities == 0 or pre_components == 0:
        return {"estimated_improvement": 0.0}

    pre_avg = pre_entities / pre_components
    post_avg = post_entities / max(post_components, 1)

    pre_coherence_factor = min(1.0, pre_avg / max(pre_entities * 0.1, 1))
    post_coherence_factor = min(1.0, post_avg / max(post_entities * 0.1, 1))

    return {
        "pre_avg_component_size": round(pre_avg, 2),
        "post_avg_component_size": round(post_avg, 2),
        "pre_coherence_factor": round(pre_coherence_factor, 4),
        "post_coherence_factor": round(post_coherence_factor, 4),
        "estimated_improvement": round(post_coherence_factor - pre_coherence_factor, 4),
    }
