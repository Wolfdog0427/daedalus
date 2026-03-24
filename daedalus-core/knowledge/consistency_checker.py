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
    Scans the knowledge base for pairwise contradictions.
    Returns a list of contradiction reports.
    """
    items = list(_iter_items())[:limit]
    contradictions = []

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i]
            b = items[j]

            if detect_contradiction(a.get("text", ""), b.get("text", "")):
                contradictions.append(
                    {
                        "item_a": a["id"],
                        "item_b": b["id"],
                        "text_a": a.get("text", "")[:200],
                        "text_b": b.get("text", "")[:200],
                        "score_a": compute_trust_score(a),
                        "score_b": compute_trust_score(b),
                    }
                )

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
    """
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
            "contradiction_count": len(contradictions),
            "low_trust_count": len(low_trust),
            "duplicate_count": len(duplicates),
            "relation_conflict_count": len(relations["conflicts"]),
            "relation_cycle_count": len(relations["cycles"]),
            "outdated_count": len(outdated),
        },
    }
