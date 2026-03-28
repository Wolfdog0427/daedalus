# knowledge/explanation_engine.py

"""
Explanation / Provenance Surfacing Engine

When an operator asks "why do you believe X?", Daedalus traces back
through the knowledge graph, shows the source chain, trust scores,
verification history, and confidence intervals.

Architecture fit:
- Uses source_integrity.py for provenance chains
- Uses trust_scoring.py for trust decomposition
- Uses rar_engine.py for reasoning trace annotation
- Read-only analysis — no mutations
- Governed through integration_layer
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional


# ------------------------------------------------------------
# BELIEF EXPLANATION
# ------------------------------------------------------------

def explain_belief(item_id: str) -> Dict[str, Any]:
    """
    Full provenance chain for a single knowledge item.
    Shows how the item entered the system, what validation it
    passed through, and its current trust score.
    """
    result: Dict[str, Any] = {
        "item_id": item_id,
        "timestamp": time.time(),
        "provenance": None,
        "trust": None,
        "verification": None,
        "temporal": None,
    }

    try:
        from knowledge.retrieval import get_item_by_id
        item = get_item_by_id(item_id)
        if item is None:
            result["error"] = "item_not_found"
            return result
        result["text_preview"] = item.get("text", "")[:200]
        result["source"] = item.get("source", "unknown")
    except ImportError:
        result["error"] = "retrieval_unavailable"
        return result

    try:
        from knowledge.source_integrity import get_provenance
        prov = get_provenance(item_id)
        if prov:
            result["provenance"] = {
                "source": prov.get("source", ""),
                "verification_path": prov.get("verification_path", ""),
                "url_integrity": prov.get("url_integrity", "not_checked"),
                "content_integrity": prov.get("content_integrity", "not_checked"),
                "ingested_at": prov.get("timestamp", 0),
                "blocked": prov.get("blocked", False),
                "flags": [k for k in prov if k.endswith("_flagged") and prov[k]],
            }
    except ImportError:
        pass

    try:
        from knowledge.trust_scoring import compute_trust_score, compute_epistemic_confidence
        trust = compute_trust_score(item)
        confidence = compute_epistemic_confidence(item)
        result["trust"] = {
            "score": trust,
            "epistemic_confidence": confidence,
        }
    except ImportError:
        pass

    meta = item.get("metadata", {}) if item else {}
    if isinstance(meta, dict):
        result["verification"] = {
            "status": meta.get("verification_status", "unknown"),
            "intensity": meta.get("verification_intensity", "unknown"),
        }

        if meta.get("temporal_type"):
            result["temporal"] = {
                "type": meta.get("temporal_type", "unknown"),
                "valid_from": meta.get("valid_from"),
                "valid_until": meta.get("valid_until"),
                "confidence": meta.get("temporal_confidence", 0),
            }

    return result


# ------------------------------------------------------------
# REASONING EXPLANATION
# ------------------------------------------------------------

def explain_reasoning(rar_result: Any) -> Dict[str, Any]:
    """
    Annotate a RAR ReasoningResult with source attribution.
    Makes the reasoning process transparent to operators.
    """
    explanation: Dict[str, Any] = {
        "query": getattr(rar_result, "query", ""),
        "confidence": getattr(rar_result, "confidence", 0),
        "reasoning_steps": getattr(rar_result, "reasoning_steps", []),
        "evidence_summary": [],
        "sources": [],
        "gaps": getattr(rar_result, "gaps_detected", []),
    }

    for chain in getattr(rar_result, "evidence_chains", []):
        summary = {
            "path": chain.path if hasattr(chain, "path") else [],
            "trust": chain.trust_score if hasattr(chain, "trust_score") else 0,
            "backing_items": len(chain.source_items) if hasattr(chain, "source_items") else 0,
        }
        explanation["evidence_summary"].append(summary)

    for source_id in getattr(rar_result, "sources_cited", []):
        belief = explain_belief(source_id)
        if belief.get("error") is None:
            explanation["sources"].append({
                "item_id": source_id,
                "source": belief.get("source", ""),
                "trust": belief.get("trust", {}).get("score", 0),
                "verification": belief.get("verification", {}).get("status", ""),
            })

    return explanation


# ------------------------------------------------------------
# TRUST BREAKDOWN
# ------------------------------------------------------------

def trust_breakdown(item_id: str) -> Dict[str, Any]:
    """
    Decompose a trust score into its contributing factors.
    Shows the operator exactly why an item has its trust level.
    """
    try:
        from knowledge.retrieval import get_item_by_id
        from knowledge.trust_scoring import (
            score_content_quality,
            score_source,
            compute_trust_score,
        )
    except ImportError:
        return {"item_id": item_id, "error": "modules_unavailable"}

    item = get_item_by_id(item_id)
    if item is None:
        return {"item_id": item_id, "error": "item_not_found"}

    text = item.get("text", "")
    source = item.get("source", "")

    content_quality = score_content_quality(text)
    source_score = score_source(source)
    total_trust = compute_trust_score(item)

    meta = item.get("metadata", {})
    verification_bonus = 0.10 if (isinstance(meta, dict) and meta.get("verified", False)) else 0.0

    return {
        "item_id": item_id,
        "total_trust": total_trust,
        "factors": {
            "content_quality": content_quality,
            "source_reputation": source_score,
            "verification_bonus": verification_bonus,
        },
        "text_length": len(text),
        "source": source,
    }


# ------------------------------------------------------------
# CONTRADICTION EXPLANATION
# ------------------------------------------------------------

def explain_contradiction(text_a: str, text_b: str) -> Dict[str, Any]:
    """
    Explain why two items contradict, with reasoning from the
    hypothesis tester when available.
    """
    result: Dict[str, Any] = {
        "text_a_preview": text_a[:200],
        "text_b_preview": text_b[:200],
    }

    try:
        from knowledge.hypothesis_tester import resolve_contradiction
        resolution = resolve_contradiction(text_a, text_b)
        result["hypothesis_analysis"] = resolution
    except ImportError:
        result["hypothesis_analysis"] = None

    try:
        from knowledge.temporal_reasoning import annotate_temporal
        result["temporal_a"] = annotate_temporal(text_a, "analysis")
        result["temporal_b"] = annotate_temporal(text_b, "analysis")

        type_a = result["temporal_a"].get("temporal_type", "unknown")
        type_b = result["temporal_b"].get("temporal_type", "unknown")
        if type_a != "unknown" and type_b != "unknown":
            result["temporal_note"] = (
                f"Item A is {type_a}, Item B is {type_b}. "
                f"This may be a temporal difference, not a true contradiction."
            )
    except ImportError:
        pass

    return result


# ------------------------------------------------------------
# GOAL EXPLANATION
# ------------------------------------------------------------

def explain_goal(goal_id: str) -> Dict[str, Any]:
    """Explain why a learning goal was proposed."""
    try:
        from knowledge.knowledge_goal import load_goal
    except ImportError:
        return {"goal_id": goal_id, "error": "modules_unavailable"}

    goal = load_goal(goal_id)
    if goal is None:
        return {"goal_id": goal_id, "error": "goal_not_found"}

    explanation = {
        "goal_id": goal_id,
        "topic": goal.topic,
        "rationale": goal.rationale,
        "source": goal.source,
        "gap_type": goal.gap_type,
        "priority": goal.priority,
        "tier_required": goal.tier_required,
        "status": goal.status,
    }

    if goal.quality_before:
        explanation["quality_context"] = {
            "coherence_at_proposal": goal.quality_before.get("graph_coherence", 0),
            "consistency_at_proposal": goal.quality_before.get("consistency", 0),
        }

    parent_id = goal.metadata.get("parent_goal_id")
    if parent_id:
        parent = load_goal(parent_id)
        if parent:
            explanation["parent_goal"] = {
                "id": parent.id,
                "topic": parent.topic,
            }

    return explanation


# ------------------------------------------------------------
# OPERATOR-FRIENDLY FORMATTING
# ------------------------------------------------------------

def format_for_operator(explanation: Dict[str, Any]) -> str:
    """Convert an explanation dict into a human-readable narrative."""
    parts = []

    if "query" in explanation:
        parts.append(f"Query: {explanation['query']}")
        conf = explanation.get("confidence", 0)
        parts.append(f"Confidence: {conf:.0%}")

        for i, ev in enumerate(explanation.get("evidence_summary", [])):
            path = " -> ".join(ev.get("path", [])) or "direct retrieval"
            trust = ev.get("trust", 0)
            parts.append(f"  Evidence {i+1}: {path} (trust: {trust:.0%})")

        gaps = explanation.get("gaps", [])
        if gaps:
            parts.append("Knowledge gaps:")
            for gap in gaps:
                parts.append(f"  - {gap}")

    elif "item_id" in explanation:
        parts.append(f"Item: {explanation.get('item_id', '')}")
        parts.append(f"Source: {explanation.get('source', 'unknown')}")

        trust_info = explanation.get("trust", {})
        if trust_info:
            parts.append(f"Trust: {trust_info.get('score', 0):.0%}")

        prov = explanation.get("provenance", {})
        if prov:
            parts.append(f"Ingested via: {prov.get('verification_path', 'unknown')}")
            flags = prov.get("flags", [])
            if flags:
                parts.append(f"Flags: {', '.join(flags)}")

    elif "topic" in explanation:
        parts.append(f"Goal: {explanation.get('topic', '')}")
        parts.append(f"Rationale: {explanation.get('rationale', '')}")
        parts.append(f"Status: {explanation.get('status', '')}")

    return "\n".join(parts) if parts else "No explanation available."
