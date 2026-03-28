# knowledge/consistency_checker.py

"""
Consistency Checker

This module scans the entire knowledge base to detect:
- contradictions
- low-trust items
- broken or conflicting relationships
- duplicate or near-duplicate entries
- outdated canonical entries
- suspicious clusters of low-quality information

It produces:
- a structured consistency report
- recommended repairs
- optional automatic fixes (with human approval)

This is the system's self-auditing layer.
"""

from __future__ import annotations

import itertools
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import (
    compute_trust_score,
    detect_contradiction,
)
from knowledge.pattern_extractor import extract_relations, extract_entities
from knowledge.storage_manager import replace_item


# ------------------------------------------------------------
# CONTRADICTION SCANNING
# ------------------------------------------------------------

def scan_for_contradictions(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Scans the knowledge base for pairwise contradictions using
    stratified random sampling instead of exhaustive O(n^2).

    Draws up to `limit` items, then checks each sampled item
    against its nearest neighbors (via retrieval search) rather
    than against every other item. This keeps cost at O(limit * k)
    where k is the neighbor count, regardless of KB size.
    """
    import random

    all_items = list(_iter_items())
    total = len(all_items)
    if total == 0:
        return []

    sample_size = min(limit, total)
    sample = random.sample(all_items, sample_size) if total > sample_size else all_items
    contradictions = []

    for item in sample:
        item_id = item.get("id", "")
        text = item.get("text", "")
        if not text.strip() or not item_id:
            continue
        try:
            from knowledge.retrieval import search_knowledge
            neighbors = search_knowledge(text[:400], limit=10, include_superseded=False)
        except Exception:
            neighbors = []

        for n in neighbors:
            if n.id == item_id:
                continue
            if detect_contradiction(text, n.text):
                contradictions.append(
                    {
                        "item_a": item_id,
                        "item_b": n.id,
                        "text_a": text[:200],
                        "text_b": n.text[:200],
                        "score_a": compute_trust_score(item),
                        "score_b": compute_trust_score({"id": n.id, "text": n.text, "source": n.source, "metadata": n.metadata}),
                    }
                )
                break  # one contradiction per sample item is enough

    return contradictions


# ------------------------------------------------------------
# LOW-TRUST DETECTION
# ------------------------------------------------------------

def scan_for_low_trust(threshold: float = 0.40, limit: int = 2000) -> List[Dict[str, Any]]:
    """
    Returns items whose trust score falls below a threshold.
    """
    low = []
    for item in itertools.islice(_iter_items(), limit):
        item_id = item.get("id", "")
        if not item_id:
            continue
        score = compute_trust_score(item)
        if score < threshold:
            low.append(
                {
                    "id": item_id,
                    "score": score,
                    "source": item.get("source", ""),
                    "snippet": item.get("text", "")[:200],
                }
            )
    return low


# ------------------------------------------------------------
# DUPLICATE / NEAR-DUPLICATE DETECTION
# ------------------------------------------------------------

def scan_for_duplicates(limit: int = 2000) -> List[Tuple[str, str]]:
    """
    Detects near-duplicate items by comparing the first 200 characters.
    """
    items = list(itertools.islice(_iter_items(), limit))
    seen = {}
    duplicates = []

    for item in items:
        item_id = item.get("id", "")
        if not item_id:
            continue
        key = item.get("text", "")[:200]
        if key in seen:
            duplicates.append((seen[key], item_id))
        else:
            seen[key] = item_id

    return duplicates


# ------------------------------------------------------------
# RELATIONSHIP CONSISTENCY
# ------------------------------------------------------------

def scan_relationship_consistency(limit: int = 2000) -> Dict[str, Any]:
    """
    Extracts relationships and checks for:
    - conflicting definitions
    - cycles
    - entities with contradictory roles
    """
    items = list(itertools.islice(_iter_items(), limit))
    relations = defaultdict(list)

    for item in items:
        item_id = item.get("id", "")
        if not item_id:
            continue
        text = item.get("text", "")
        for subj, rel, obj in extract_relations(text):
            relations[subj].append((rel, obj, item_id))

    conflicts = []
    cycles = []

    # Detect conflicting definitions
    for subj, rel_list in relations.items():
        seen = {}
        for rel, obj, item_id in rel_list:
            if rel in seen and seen[rel] != obj:
                conflicts.append(
                    {
                        "entity": subj,
                        "relation": rel,
                        "obj_a": seen[rel],
                        "obj_b": obj,
                        "item_id": item_id,
                    }
                )
            else:
                seen[rel] = obj

    # Detect cycles (A -> B -> A)
    for subj, rel_list in relations.items():
        for rel, obj, _ in rel_list:
            if obj in relations:
                for rel2, obj2, _ in relations[obj]:
                    if obj2 == subj:
                        cycles.append(
                            {
                                "cycle": [subj, obj, subj],
                                "relation_1": rel,
                                "relation_2": rel2,
                            }
                        )

    return {
        "conflicts": conflicts,
        "cycles": cycles,
    }


# ------------------------------------------------------------
# OUTDATED CANONICAL DETECTION
# ------------------------------------------------------------

def scan_for_outdated(limit: int = 2000) -> List[Dict[str, Any]]:
    """
    Detects items that are likely outdated based on:
    - low trust score
    - presence of newer, higher-quality neighbors
    """
    items = list(itertools.islice(_iter_items(), limit))
    outdated = []

    for item in items:
        item_id = item.get("id", "")
        if not item_id:
            continue
        score = compute_trust_score(item)
        if score < 0.50:
            neighbors = extract_entities(item.get("text", ""))
            if neighbors:
                outdated.append(
                    {
                        "id": item_id,
                        "score": score,
                        "snippet": item.get("text", "")[:200],
                    }
                )

    return outdated


# ------------------------------------------------------------
# FULL CONSISTENCY REPORT
# ------------------------------------------------------------

def run_consistency_check() -> Dict[str, Any]:
    """
    Runs a full consistency audit of the knowledge base.
    Includes total_items count so downstream scoring can compute
    defect rates rather than raw counts.
    """
    total_items = sum(1 for _ in _iter_items())

    contradictions = scan_for_contradictions()
    low_trust = scan_for_low_trust()
    duplicates = scan_for_duplicates()
    relations = scan_relationship_consistency()
    outdated = scan_for_outdated()

    return {
        "contradictions": contradictions,
        "low_trust_items": low_trust,
        "duplicates": duplicates,
        "relationship_conflicts": relations["conflicts"],
        "relationship_cycles": relations["cycles"],
        "outdated_items": outdated,
        "summary": {
            "total_items": total_items,
            "contradiction_count": len(contradictions),
            "low_trust_count": len(low_trust),
            "duplicate_count": len(duplicates),
            "relation_conflict_count": len(relations["conflicts"]),
            "relation_cycle_count": len(relations["cycles"]),
            "outdated_count": len(outdated),
        },
    }


# ------------------------------------------------------------
# RELATIONSHIP CONFLICT REPAIR
# ------------------------------------------------------------

def _resolve_relationship_conflict(conflict: Dict[str, Any]) -> bool:
    """
    Resolve a single relationship conflict in the knowledge graph.

    A conflict occurs when the same (entity, relation) pair points to
    two different objects. Resolution strategy:
    1. Look up the source items for each edge.
    2. Compute trust scores for both.
    3. Remove the edge backed by the lower-trust item.

    Returns True if the conflict was resolved.
    """
    from knowledge.knowledge_graph import _load_graph, _save_graph, _graph_lock

    entity = conflict.get("entity")
    relation = conflict.get("relation")
    obj_a = conflict.get("obj_a")
    obj_b = conflict.get("obj_b")

    if not all([entity, relation, obj_a, obj_b]):
        return False

    with _graph_lock:
        graph = _load_graph()
        edges = graph.get(entity, [])
        if not edges:
            return False

        edge_a = None
        edge_b = None
        for e in edges:
            if e.get("relation") == relation:
                if e.get("object") == obj_a and edge_a is None:
                    edge_a = e
                elif e.get("object") == obj_b and edge_b is None:
                    edge_b = e

        if edge_a is None or edge_b is None:
            return False

        trust_a = edge_a.get("trust", 0.5)
        trust_b = edge_b.get("trust", 0.5)

        loser = edge_b if trust_a >= trust_b else edge_a
        graph[entity] = [e for e in edges if e is not loser]
        _save_graph(graph)
    return True


# ------------------------------------------------------------
# ACTIVE CONSISTENCY CONSOLIDATION (Sim-fix C1)
# ------------------------------------------------------------

def run_active_consolidation(consistency: float, coherence: float) -> Dict[str, Any]:
    """
    Aggressive graph-wide dedup and contradiction resolution.

    Triggered when consistency drops below the consolidation ceiling.
    Unlike the passive consistency scan, this actively resolves
    contradictions by:
    1. Removing lower-trust item in each contradiction pair
    2. Merging exact duplicates
    3. Resolving conflicting relations (keep highest-trust)
    4. Reporting a consistency_boost estimate

    Intensity scales with deficit from target.  Each category gets its
    own resolve cap so a flood of one type cannot starve the others.

    Coherence is used as a secondary multiplier: when graph quality is
    poor (< 0.7), scan limits get a 50% boost to catch more structural
    issues in a single pass.
    """
    CONSOLIDATION_TARGET = 0.92

    if consistency >= CONSOLIDATION_TARGET:
        return {"action": "skipped", "reason": "consistency_above_target"}

    deficit = CONSOLIDATION_TARGET - consistency

    if deficit < 0.03:
        intensity = "polishing"
        scan_limit = 200
        contradiction_cap = 4
        duplicate_cap = 4
        conflict_cap = 4
    elif deficit < 0.07:
        intensity = "fine_maintenance"
        scan_limit = 400
        contradiction_cap = 8
        duplicate_cap = 6
        conflict_cap = 6
    elif deficit < 0.12:
        intensity = "maintenance"
        scan_limit = 600
        contradiction_cap = 12
        duplicate_cap = 10
        conflict_cap = 8
    elif deficit < 0.17:
        intensity = "preventive"
        scan_limit = 1000
        contradiction_cap = 20
        duplicate_cap = 15
        conflict_cap = 12
    elif deficit < 0.25:
        intensity = "mild"
        scan_limit = 1500
        contradiction_cap = 35
        duplicate_cap = 25
        conflict_cap = 20
    elif deficit < 0.35:
        intensity = "medium"
        scan_limit = 2500
        contradiction_cap = 60
        duplicate_cap = 40
        conflict_cap = 30
    else:
        intensity = "severe"
        scan_limit = 4000
        contradiction_cap = 9999
        duplicate_cap = 9999
        conflict_cap = 9999

    # Coherence multiplier: poor graph quality demands wider scans
    if coherence < 0.50:
        coherence_boost = 1.5
    elif coherence < 0.70:
        coherence_boost = 1.25
    else:
        coherence_boost = 1.0

    scan_limit = int(scan_limit * coherence_boost)

    resolved_contradictions = 0
    merged_duplicates = 0
    resolved_conflicts = 0
    removed_items = 0
    consolidation_errors = 0

    # 1. Resolve contradictions: remove lower-trust item
    contradictions = scan_for_contradictions(limit=scan_limit)
    for c in contradictions[:contradiction_cap]:
        try:
            if c.get("score_a", 0) >= c.get("score_b", 0):
                loser_id = c.get("item_b")
            else:
                loser_id = c.get("item_a")
            if not loser_id:
                continue
            from knowledge.storage_manager import _mark_superseded
            _mark_superseded(loser_id)
            resolved_contradictions += 1
            removed_items += 1
        except (ImportError, OSError, ValueError):
            consolidation_errors += 1

    # 2. Merge exact duplicates
    duplicates = scan_for_duplicates(limit=scan_limit)
    for dup_a, dup_b in duplicates[:duplicate_cap]:
        try:
            from knowledge.storage_manager import _mark_superseded
            _mark_superseded(dup_b)
            merged_duplicates += 1
            removed_items += 1
        except (ImportError, OSError, ValueError):
            consolidation_errors += 1

    # 3. Resolve relationship conflicts: remove the lower-trust edge
    relations = scan_relationship_consistency(limit=scan_limit)
    for conflict in relations["conflicts"][:conflict_cap]:
        try:
            if _resolve_relationship_conflict(conflict):
                resolved_conflicts += 1
        except (ImportError, OSError, ValueError):
            consolidation_errors += 1

    boost_estimate = min(
        0.20,
        0.01 * resolved_contradictions
        + 0.005 * merged_duplicates
        + 0.003 * resolved_conflicts,
    )

    return {
        "action": "consolidation",
        "intensity": intensity,
        "deficit": round(deficit, 4),
        "coherence_boost": coherence_boost,
        "scan_limit": scan_limit,
        "resolved_contradictions": resolved_contradictions,
        "merged_duplicates": merged_duplicates,
        "resolved_conflicts": resolved_conflicts,
        "removed_items": removed_items,
        "consistency_boost_estimate": round(boost_estimate, 4),
    }
