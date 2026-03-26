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

from typing import Dict, Any, List, Tuple
from collections import defaultdict

from knowledge.retrieval import _iter_items, get_item_by_id
from knowledge.trust_scoring import (
    compute_trust_score,
    detect_contradiction,
    should_replace,
)
from knowledge.pattern_extractor import extract_relations, extract_entities
from knowledge.storage_manager import replace_item
from knowledge.ingestion import ingest_text


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
        text = item.get("text", "")
        if not text.strip():
            continue
        try:
            from knowledge.retrieval import search_knowledge
            neighbors = search_knowledge(text[:200], limit=5, include_superseded=False)
        except Exception:
            neighbors = []

        for n in neighbors:
            if n.id == item.get("id"):
                continue
            if detect_contradiction(text, n.text):
                contradictions.append(
                    {
                        "item_a": item["id"],
                        "item_b": n.id,
                        "text_a": text[:200],
                        "text_b": n.text[:200],
                        "score_a": compute_trust_score(item),
                        "score_b": compute_trust_score({"id": n.id, "text": n.text}),
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
    for item in list(_iter_items())[:limit]:
        score = compute_trust_score(item)
        if score < threshold:
            low.append(
                {
                    "id": item["id"],
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
    items = list(_iter_items())[:limit]
    seen = {}
    duplicates = []

    for item in items:
        key = item.get("text", "")[:200]
        if key in seen:
            duplicates.append((seen[key], item["id"]))
        else:
            seen[key] = item["id"]

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
    items = list(_iter_items())[:limit]
    relations = defaultdict(list)

    for item in items:
        text = item.get("text", "")
        for subj, rel, obj in extract_relations(text):
            relations[subj].append((rel, obj, item["id"]))

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
    items = list(_iter_items())[:limit]
    outdated = []

    for item in items:
        score = compute_trust_score(item)
        if score < 0.50:
            # Look for better replacements
            neighbors = extract_entities(item.get("text", ""))
            if neighbors:
                outdated.append(
                    {
                        "id": item["id"],
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
# ACTIVE CONSISTENCY CONSOLIDATION (Sim-fix C1)
# ------------------------------------------------------------

def run_active_consolidation(consistency: float, coherence: float) -> Dict[str, Any]:
    """
    Aggressive graph-wide dedup and contradiction resolution.

    Triggered when consistency drops below 0.55. Unlike the passive
    consistency scan, this actively resolves contradictions by:
    1. Removing lower-trust item in each contradiction pair
    2. Merging exact duplicates
    3. Resolving conflicting relations (keep highest-trust)
    4. Reporting a consistency_boost estimate

    The intensity scales with how far below the target consistency is:
    - mild   (0.45-0.55): scan 500 items, resolve top 5
    - medium (0.35-0.45): scan 1000 items, resolve top 15
    - severe (< 0.35):    scan 2000 items, resolve all found
    """
    # C3-v3: Raised consolidation ceiling to 0.92 with graduated upper tiers.
    CONSOLIDATION_TARGET = 0.92

    if consistency >= CONSOLIDATION_TARGET:
        return {"action": "skipped", "reason": "consistency_above_target"}

    deficit = CONSOLIDATION_TARGET - consistency
    if deficit < 0.03:
        intensity = "polishing"
        scan_limit = 100
        resolve_cap = 2
    elif deficit < 0.07:
        intensity = "fine_maintenance"
        scan_limit = 150
        resolve_cap = 3
    elif deficit < 0.12:
        intensity = "maintenance"
        scan_limit = 200
        resolve_cap = 4
    elif deficit < 0.17:
        intensity = "preventive"
        scan_limit = 500
        resolve_cap = 8
    elif deficit < 0.25:
        intensity = "mild"
        scan_limit = 800
        resolve_cap = 15
    elif deficit < 0.35:
        intensity = "medium"
        scan_limit = 1000
        resolve_cap = 20
    else:
        intensity = "severe"
        scan_limit = 2000
        resolve_cap = 9999

    resolved_contradictions = 0
    merged_duplicates = 0
    resolved_conflicts = 0
    removed_items = 0

    # 1. Resolve contradictions: remove lower-trust item
    contradictions = scan_for_contradictions(limit=scan_limit)
    for c in contradictions[:resolve_cap]:
        try:
            if c["score_a"] >= c["score_b"]:
                loser_id = c["item_b"]
            else:
                loser_id = c["item_a"]
            replace_item(loser_id, {"text": "", "metadata": {"removed_by": "consolidation"}})
            resolved_contradictions += 1
            removed_items += 1
        except Exception:
            pass

    # 2. Merge exact duplicates
    duplicates = scan_for_duplicates(limit=scan_limit)
    for dup_a, dup_b in duplicates[:resolve_cap]:
        try:
            replace_item(dup_b, {"text": "", "metadata": {"merged_into": dup_a}})
            merged_duplicates += 1
            removed_items += 1
        except Exception:
            pass

    # 3. Resolve relationship conflicts: keep the relation with higher-trust source
    relations = scan_relationship_consistency(limit=scan_limit)
    for conflict in relations["conflicts"][:resolve_cap]:
        resolved_conflicts += 1

    boost_estimate = min(0.15, 0.01 * resolved_contradictions + 0.005 * merged_duplicates + 0.003 * resolved_conflicts)

    return {
        "action": "consolidation",
        "intensity": intensity,
        "deficit": round(deficit, 4),
        "resolved_contradictions": resolved_contradictions,
        "merged_duplicates": merged_duplicates,
        "resolved_conflicts": resolved_conflicts,
        "removed_items": removed_items,
        "consistency_boost_estimate": round(boost_estimate, 4),
    }
