# knowledge/hypothesis_tester.py

"""
Hypothesis Testing / LLM Contradiction Resolution

When contradictions are detected, uses the LLM to reason about which
side is more likely correct, generate disambiguation queries, and
resolve with higher confidence than structural heuristics alone.

Architecture fit:
- Called by consistency_checker when LLM is available
- Falls back to existing detect_contradiction heuristic when no LLM
- All resolutions are suggestions — the consistency checker decides
  whether to act on them
- Governed through integration_layer

This module never auto-deletes knowledge. It recommends which side
of a contradiction to keep, supersede, or flag for operator review.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional


# ------------------------------------------------------------
# HYPOTHESIS GENERATION
# ------------------------------------------------------------

def generate_hypotheses(
    text_a: str,
    text_b: str,
    context: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Given two contradicting texts, generate hypotheses for why
    they contradict. Uses LLM when available, falls back to
    structural analysis.
    """
    hypotheses = []

    hypotheses.extend(_structural_hypotheses(text_a, text_b))

    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            llm_hyps = _llm_hypotheses(text_a, text_b, context, llm_adapter)
            hypotheses.extend(llm_hyps)
    except ImportError:
        pass

    return hypotheses


def _structural_hypotheses(text_a: str, text_b: str) -> List[Dict[str, Any]]:
    """Generate hypotheses from structural analysis."""
    hyps = []

    a_lower = text_a.lower()
    b_lower = text_b.lower()
    a_words = set(a_lower.split())
    b_words = set(b_lower.split())
    overlap = a_words & b_words
    overlap_ratio = len(overlap) / max(1, len(a_words | b_words))

    if overlap_ratio > 0.7:
        hyps.append({
            "type": "near_duplicate",
            "confidence": 0.6,
            "explanation": "High word overlap suggests these are versions of the same fact",
            "recommendation": "keep_newer",
        })
    elif overlap_ratio < 0.2:
        hyps.append({
            "type": "different_domains",
            "confidence": 0.5,
            "explanation": "Low overlap suggests these may not actually contradict",
            "recommendation": "review",
        })

    len_ratio = len(text_a) / max(1, len(text_b))
    if len_ratio > 3 or len_ratio < 0.33:
        hyps.append({
            "type": "detail_disparity",
            "confidence": 0.4,
            "explanation": "Large length difference — the longer text may contain nuance the shorter misses",
            "recommendation": "keep_longer",
        })

    return hyps


def _llm_hypotheses(
    text_a: str,
    text_b: str,
    context: Optional[List[Dict[str, Any]]],
    adapter: Any,
) -> List[Dict[str, Any]]:
    """Use LLM to generate richer hypotheses."""
    context_str = ""
    if context:
        context_str = "\n".join(
            f"- {c.get('text', '')[:200]}" for c in context[:5]
        )

    prompt = (
        f"Two knowledge items appear to contradict each other.\n\n"
        f"Item A: {text_a[:500]}\n\n"
        f"Item B: {text_b[:500]}\n\n"
    )
    if context_str:
        prompt += f"Related context:\n{context_str}\n\n"

    prompt += (
        f"Analyze this contradiction. For each hypothesis, provide:\n"
        f"1. Which item is more likely correct and why\n"
        f"2. Whether this is a true contradiction or a misunderstanding\n"
        f"3. Recommendation: keep_a, keep_b, keep_both, review\n"
        f"Be concise."
    )

    try:
        response = adapter.complete(prompt, max_tokens=300, temperature=0.2)
        if response.strip():
            recommendation = "review"
            resp_lower = response.lower()
            if "keep_a" in resp_lower or "item a" in resp_lower:
                recommendation = "keep_a"
            elif "keep_b" in resp_lower or "item b" in resp_lower:
                recommendation = "keep_b"
            elif "keep both" in resp_lower or "not a contradiction" in resp_lower:
                recommendation = "keep_both"

            return [{
                "type": "llm_analysis",
                "confidence": 0.75,
                "explanation": response.strip()[:500],
                "recommendation": recommendation,
            }]
    except Exception:
        pass

    return []


# ------------------------------------------------------------
# HYPOTHESIS TESTING
# ------------------------------------------------------------

def test_hypothesis(
    hypothesis: Dict[str, Any],
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a hypothesis against available evidence from the
    knowledge graph. Returns a confidence-adjusted result.
    """
    base_confidence = hypothesis.get("confidence") or 0.5
    evidence_support = 0.0

    if evidence:
        for item in evidence:
            trust = item.get("trust") or 0.5
            evidence_support += trust * 0.1

    adjusted_confidence = min(1.0, base_confidence + evidence_support)

    return {
        "hypothesis": hypothesis,
        "evidence_count": len(evidence) if evidence else 0,
        "original_confidence": base_confidence,
        "adjusted_confidence": adjusted_confidence,
        "supported": adjusted_confidence > 0.5,
    }


# ------------------------------------------------------------
# FULL RESOLUTION PIPELINE
# ------------------------------------------------------------

def resolve_contradiction(
    text_a: str,
    text_b: str,
    context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Full pipeline: generate hypotheses, test them, recommend resolution.
    Returns a structured recommendation that the consistency checker
    can act on.
    """
    hypotheses = generate_hypotheses(text_a, text_b, context)

    if not hypotheses:
        return {
            "resolved": False,
            "recommendation": "review",
            "confidence": 0.0,
            "reason": "no_hypotheses_generated",
        }

    tested = []
    for hyp in hypotheses:
        result = test_hypothesis(hyp, context)
        tested.append(result)

    best = max(tested, key=lambda t: t["adjusted_confidence"])
    recommendation = best["hypothesis"].get("recommendation", "review")

    return {
        "resolved": best["adjusted_confidence"] > 0.6,
        "recommendation": recommendation,
        "confidence": best["adjusted_confidence"],
        "best_hypothesis": best["hypothesis"].get("type", "unknown"),
        "explanation": best["hypothesis"].get("explanation", ""),
        "hypotheses_tested": len(tested),
        "timestamp": time.time(),
    }


# ------------------------------------------------------------
# DISAMBIGUATION
# ------------------------------------------------------------

def formulate_disambiguation_query(text_a: str, text_b: str) -> str:
    """
    Generate a query that would disambiguate the contradiction.
    Useful for active learning — the system can go find the answer.
    """
    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            prompt = (
                f"Two facts contradict each other:\n"
                f"A: {text_a[:300]}\n"
                f"B: {text_b[:300]}\n\n"
                f"Generate a single search query that would help determine "
                f"which is correct. Just the query, nothing else."
            )
            result = llm_adapter.complete(prompt, max_tokens=64, temperature=0.3)
            if result.strip():
                return result.strip()
    except ImportError:
        pass

    a_words = set(text_a.lower().split())
    b_words = set(text_b.lower().split())
    unique_a = a_words - b_words
    unique_b = b_words - a_words
    key_terms = list(unique_a | unique_b)[:5]
    return " ".join(key_terms) if key_terms else text_a[:100]


# ------------------------------------------------------------
# BATCH RESOLUTION
# ------------------------------------------------------------

def batch_resolve(
    contradictions: List[Dict[str, Any]],
    max_resolve: int = 10,
) -> Dict[str, Any]:
    """
    Process multiple contradictions in one pass.
    Each contradiction dict should have 'text_a' and 'text_b' keys.
    """
    results = []
    resolved_count = 0

    for contradiction in contradictions[:max_resolve]:
        text_a = contradiction.get("text_a", "")
        text_b = contradiction.get("text_b", "")
        if not text_a or not text_b:
            continue

        result = resolve_contradiction(text_a, text_b)
        results.append(result)
        if result.get("resolved"):
            resolved_count += 1

    return {
        "action": "batch_hypothesis_resolution",
        "total": len(results),
        "resolved": resolved_count,
        "unresolved": len(results) - resolved_count,
        "results": results,
        "timestamp": time.time(),
    }
