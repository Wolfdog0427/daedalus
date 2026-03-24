# knowledge/verification_pipeline.py

"""
Verification Pipeline

Coordinates multi-source verification, trust aggregation, and replacement decisions.

Goals:
- verify individual knowledge items
- cross-check claims against existing knowledge
- optionally consult the web (when wired)
- decide whether new information should:
  - be accepted as-is
  - replace existing knowledge
  - be flagged for human review

This module does NOT mutate storage directly except via storage_manager.replace_item.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

from knowledge.retrieval import get_item_by_id, search_knowledge
from knowledge.trust_scoring import (
    compute_trust_score,
    detect_contradiction,
    should_replace,
)
from knowledge.storage_manager import replace_item
from knowledge.ingestion import ingest_text

try:
    from web.tools import search_web as web_search
    WEB_SEARCH_AVAILABLE = True
except Exception:
    WEB_SEARCH_AVAILABLE = False


# ------------------------------------------------------------
# CORE VERIFICATION PRIMITIVES
# ------------------------------------------------------------

def verify_item_by_id(item_id: str) -> Dict[str, Any]:
    """
    Verifies a single knowledge item using:
    - its own trust score
    - nearby items in the knowledge base (same query window)

    Returns a verification report.
    """
    item = get_item_by_id(item_id)
    if not item:
        return {
            "item_id": item_id,
            "status": "not_found",
        }

    text = item.get("text", "")
    source = item.get("source", "")
    base_score = compute_trust_score(item)

    # Look for related items in the local store
    neighbors = search_knowledge(text[:200], limit=5, include_superseded=True)

    contradictions: List[Dict[str, Any]] = []
    supports: List[Dict[str, Any]] = []

    for n in neighbors:
        if n.id == item_id:
            continue
        if detect_contradiction(text, n.text):
            contradictions.append(
                {
                    "id": n.id,
                    "source": n.source,
                    "score": compute_trust_score(
                        {
                            "source": n.source,
                            "text": n.text,
                            "metadata": n.metadata,
                        }
                    ),
                }
            )
        else:
            supports.append(
                {
                    "id": n.id,
                    "source": n.source,
                    "score": compute_trust_score(
                        {
                            "source": n.source,
                            "text": n.text,
                            "metadata": n.metadata,
                        }
                    ),
                }
            )

    report: Dict[str, Any] = {
        "item_id": item_id,
        "source": source,
        "base_trust_score": base_score,
        "supports": supports,
        "contradictions": contradictions,
    }

    # Simple aggregation heuristic
    support_boost = sum(s["score"] for s in supports) * 0.05
    contradiction_penalty = sum(c["score"] for c in contradictions) * 0.10

    final_score = max(0.0, min(1.0, base_score + support_boost - contradiction_penalty))
    report["final_trust_score"] = final_score

    if final_score >= 0.85:
        report["status"] = "high_confidence"
    elif final_score >= 0.60:
        report["status"] = "medium_confidence"
    else:
        report["status"] = "low_confidence"

    return report


# ------------------------------------------------------------
# WEB-ASSISTED VERIFICATION (OPTIONAL)
# ------------------------------------------------------------

def web_assisted_verification(text: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Optionally verifies a claim against the web (if search is available).

    Returns:
        {
            "web_available": bool,
            "results": [...],
        }
    """
    if not WEB_SEARCH_AVAILABLE:
        return {
            "web_available": False,
            "results": [],
        }

    try:
        results = web_search(text)[:max_results]
    except Exception as e:
        return {
            "web_available": False,
            "error": str(e),
            "results": [],
        }

    return {
        "web_available": True,
        "results": results,
    }


# ------------------------------------------------------------
# NEW INFORMATION VERIFICATION + REPLACEMENT
# ------------------------------------------------------------

def verify_new_information(
    new_text: str,
    source: str = "manual",
    use_web: bool = False,
) -> Dict[str, Any]:
    """
    Verifies new information against:
    - existing knowledge
    - (optionally) the web

    Decides whether to:
    - accept as new
    - replace an existing item
    - flag for human review

    Returns a decision report.
    """
    # 1. Check against local knowledge
    neighbors = search_knowledge(new_text[:200], limit=10, include_superseded=True)

    best_candidate = None
    best_candidate_item = None
    best_candidate_score_delta = 0.0

    for n in neighbors:
        candidate_item = {
            "source": n.source,
            "text": n.text,
            "metadata": n.metadata,
        }
        if should_replace(candidate_item, new_text):
            old_score = compute_trust_score(candidate_item)
            # approximate new score using content quality
            # (full trust score will be computed after ingestion)
            new_score_estimate = old_score + 0.2
            delta = new_score_estimate - old_score
            if delta > best_candidate_score_delta:
                best_candidate = n
                best_candidate_item = candidate_item
                best_candidate_score_delta = delta

    decision: Dict[str, Any] = {
        "action": "accept_new",
        "reason": "no_stronger_replacement_candidate_found",
        "replaced_item_id": None,
        "new_item_id": None,
        "web_verification": None,
    }

    # 2. Optionally consult the web
    web_report = None
    if use_web:
        web_report = web_assisted_verification(new_text)
        decision["web_verification"] = web_report

    # 3. Decide action
    if best_candidate and best_candidate_item:
        # We have a plausible replacement target
        decision["action"] = "replace_existing"
        decision["reason"] = "new_information_scores_as_better_candidate"
        decision["replaced_item_id"] = best_candidate.id

        new_id = replace_item(
            old_id=best_candidate.id,
            new_text=new_text,
            reason="verification_pipeline_replacement",
            source=source,
        )
        decision["new_item_id"] = new_id
    else:
        # Just ingest as new
        new_id = ingest_text(new_text, source=source)
        decision["new_item_id"] = new_id

    return decision
