# knowledge/reasoning_engine.py

"""
Reasoning Engine

This module performs governed, auditable reasoning over the knowledge base.
It integrates:
- retrieval
- trust scoring
- verification pipeline
- replacement logic
- contradiction detection

The goal is NOT to be an LLM.
The goal is to provide structured, deterministic reasoning steps
that the LLM can call into safely.

This is the cognitive "glue" between knowledge and action.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from knowledge.retrieval import search_knowledge, get_item_by_id
from knowledge.trust_scoring import (
    compute_trust_score,
    detect_contradiction,
    should_replace,
)
from knowledge.verification_pipeline import verify_new_information

from knowledge.ingestion import ingest_text


# ------------------------------------------------------------
# REASONING STEP STRUCTURE
# ------------------------------------------------------------

def _make_step(action: str, detail: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "action": action,
        "detail": detail,
        "data": data or {},
    }


# ------------------------------------------------------------
# CORE REASONING
# ------------------------------------------------------------

def reason_about_claim(claim: str, use_web: bool = False) -> Dict[str, Any]:
    """
    Performs a structured reasoning process over a claim.

    Steps:
    1. Retrieve relevant knowledge
    2. Score trust of retrieved items
    3. Detect contradictions
    4. Decide whether the claim is:
       - supported
       - contradicted
       - uncertain
    5. Optionally escalate to verification pipeline
    """

    steps: List[Dict[str, Any]] = []
    steps.append(_make_step("start", "Beginning reasoning process", {"claim": claim}))

    # --------------------------------------------------------
    # 1. Retrieve relevant knowledge
    # --------------------------------------------------------
    neighbors = search_knowledge(claim, limit=10, include_superseded=True)
    steps.append(
        _make_step(
            "retrieval",
            f"Retrieved {len(neighbors)} related items",
            {"neighbors": [n.id for n in neighbors]},
        )
    )

    if not neighbors:
        steps.append(_make_step("no_data", "No relevant knowledge found"))
        return {
            "claim": claim,
            "status": "unknown",
            "reasoning": steps,
        }

    # --------------------------------------------------------
    # 2. Score trust of retrieved items
    # --------------------------------------------------------
    scored = []
    for n in neighbors:
        score = compute_trust_score(
            {
                "source": n.source,
                "text": n.text,
                "metadata": n.metadata,
            }
        )
        scored.append((n, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    steps.append(
        _make_step(
            "trust_scoring",
            "Computed trust scores for retrieved items",
            {
                "scores": [
                    {"id": n.id, "score": s, "source": n.source}
                    for n, s in scored
                ]
            },
        )
    )

    # --------------------------------------------------------
    # 3. Detect contradictions
    # --------------------------------------------------------
    contradictions = []
    supports = []

    for n, score in scored:
        if detect_contradiction(claim, n.text):
            contradictions.append((n, score))
        else:
            supports.append((n, score))

    steps.append(
        _make_step(
            "contradiction_analysis",
            "Analyzed contradictions and supports",
            {
                "supports": [n.id for n, _ in supports],
                "contradictions": [n.id for n, _ in contradictions],
            },
        )
    )

    # --------------------------------------------------------
    # 4. Decide claim status
    # --------------------------------------------------------
    if supports and not contradictions:
        status = "supported"
    elif contradictions and not supports:
        status = "contradicted"
    else:
        status = "uncertain"

    steps.append(
        _make_step(
            "decision",
            f"Claim classified as {status}",
        )
    )

    # --------------------------------------------------------
    # 5. Optional: escalate to verification pipeline
    # --------------------------------------------------------
    verification = None
    if status == "uncertain" or use_web:
        verification = verify_new_information(claim, source="reasoning_engine", use_web=use_web)
        steps.append(
            _make_step(
                "verification",
                "Escalated to verification pipeline",
                {"verification": verification},
            )
        )

    return {
        "claim": claim,
        "status": status,
        "supports": [n.id for n, _ in supports],
        "contradictions": [n.id for n, _ in contradictions],
        "verification": verification,
        "reasoning": steps,
    }


# ------------------------------------------------------------
# REASONING ABOUT NEW INFORMATION
# ------------------------------------------------------------

def reason_and_ingest(claim: str, source: str = "manual", use_web: bool = False) -> Dict[str, Any]:
    """
    Full pipeline:
    - reason about the claim
    - verify it
    - decide whether to ingest or replace existing knowledge
    """

    reasoning = reason_about_claim(claim, use_web=use_web)

    if reasoning["status"] == "supported":
        # Ingest as reinforcement
        new_id = ingest_text(claim, source=source)
        return {
            "action": "ingested_as_support",
            "new_item_id": new_id,
            "reasoning": reasoning,
        }

    if reasoning["status"] == "contradicted":
        # Let verification pipeline decide replacement
        verification = verify_new_information(claim, source=source, use_web=use_web)
        return {
            "action": verification["action"],
            "details": verification,
            "reasoning": reasoning,
        }

    # Uncertain → escalate to verification
    verification = verify_new_information(claim, source=source, use_web=use_web)
    return {
        "action": verification["action"],
        "details": verification,
        "reasoning": reasoning,
    }
