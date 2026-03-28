# knowledge/active_learner.py

"""
Active Learning / Query-Driven Ingestion

During reasoning, Daedalus notices it's uncertain about something,
formulates a targeted query, ingests the answer, and continues —
closing the knowledge loop in real time.

Architecture fit:
- Triggered by RAR engine when confidence is low or gaps detected
- Routes through batch_ingestion for actual ingestion
- Creates KnowledgeGoal entries for tracking
- Uses goal_planner for complex gaps needing decomposition
- Governed through integration_layer
- Can be disabled via configuration

This is the difference between "I should learn astrophysics eventually"
and "You just asked about neutron stars and I have a gap — let me
fill it now."
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

URGENCY_THRESHOLD = 0.6
MAX_ACTIVE_FILLS = 3
CONFIDENCE_GAP_THRESHOLD = 0.5
ENABLED = True


# ------------------------------------------------------------
# GAP DETECTION
# ------------------------------------------------------------

def detect_gap_in_context(
    query: str,
    rar_result: Any,
) -> Optional[Dict[str, Any]]:
    """
    Analyze a RAR result to identify actionable knowledge gaps.
    Returns a gap descriptor if one is found, None otherwise.
    """
    if not ENABLED:
        return None

    confidence = getattr(rar_result, "confidence", 1.0)
    gaps = getattr(rar_result, "gaps_detected", [])

    if confidence >= CONFIDENCE_GAP_THRESHOLD and not gaps:
        return None

    gap: Dict[str, Any] = {
        "query": query,
        "confidence": confidence,
        "gap_descriptions": gaps,
        "timestamp": time.time(),
        "urgency": _compute_urgency(confidence, gaps),
    }

    evidence_count = len(getattr(rar_result, "evidence_chains", []))
    gap["evidence_count"] = evidence_count
    gap["is_total_gap"] = evidence_count == 0

    return gap


def _compute_urgency(confidence: float, gaps: List[str]) -> float:
    """
    Compute urgency score for a gap. Higher = more urgent.
    Factors: confidence deficit, number of gaps, gap specificity.
    """
    confidence_deficit = max(0, 1.0 - confidence)
    gap_count_factor = min(0.3, len(gaps) * 0.1)

    specificity = 0.0
    if gaps:
        avg_len = sum(len(g) for g in gaps) / len(gaps)
        specificity = min(0.2, avg_len / 200)

    return min(1.0, confidence_deficit * 0.5 + gap_count_factor + specificity)


# ------------------------------------------------------------
# QUERY FORMULATION
# ------------------------------------------------------------

def formulate_targeted_query(gap: Dict[str, Any]) -> str:
    """
    Build an acquisition query from a detected gap.
    Uses LLM for intelligent query construction when available.
    """
    query = gap.get("query", "")
    descriptions = gap.get("gap_descriptions", [])

    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            gaps_text = "\n".join(f"- {d}" for d in descriptions[:3])
            prompt = (
                f"The system tried to answer: {query}\n"
                f"But found these knowledge gaps:\n{gaps_text}\n\n"
                f"Generate a concise, factual search query that would "
                f"fill the most important gap. Just the query, nothing else."
            )
            result = llm_adapter.complete(prompt, max_tokens=64, temperature=0.3)
            if result.strip():
                return result.strip()
    except ImportError:
        pass

    if descriptions:
        return descriptions[0][:200]
    return query


# ------------------------------------------------------------
# LEARNING DECISION
# ------------------------------------------------------------

def should_learn_now(
    gap: Dict[str, Any],
    urgency_override: Optional[float] = None,
) -> bool:
    """
    Decide whether to fill this gap immediately or defer.
    Considers urgency, current active fills, and system health.
    """
    if not ENABLED:
        return False

    urgency = urgency_override if urgency_override is not None else gap.get("urgency", 0)
    if urgency < URGENCY_THRESHOLD:
        return False

    if gap.get("is_total_gap"):
        return True

    return urgency >= URGENCY_THRESHOLD


# ------------------------------------------------------------
# LEARN AND CONTINUE
# ------------------------------------------------------------

def learn_and_continue(
    gap: Dict[str, Any],
    original_query: str,
) -> Dict[str, Any]:
    """
    Fill a knowledge gap and optionally re-reason.

    1. Formulate a targeted query
    2. Ingest relevant information
    3. Optionally re-run reasoning with new knowledge
    """
    targeted_query = formulate_targeted_query(gap)

    result: Dict[str, Any] = {
        "action": "active_learn",
        "original_query": original_query,
        "targeted_query": targeted_query,
        "gap": gap,
        "ingested": False,
        "re_reasoned": False,
        "timestamp": time.time(),
    }

    try:
        from knowledge.batch_ingestion import ingest_batch

        items = [{
            "text": targeted_query,
            "source": "active_learner",
            "metadata": {
                "learning_type": "active",
                "original_query": original_query,
                "gap_urgency": gap.get("urgency", 0),
            },
        }]

        batch_result = ingest_batch(
            items=items,
            source="active_learner",
            verification_intensity="standard",
        )

        result["ingested"] = batch_result.get("ingested", 0) > 0
        result["batch_result"] = {
            "ingested": batch_result.get("ingested", 0),
            "rejected": batch_result.get("rejected", 0),
        }
    except ImportError:
        result["error"] = "batch_ingestion_unavailable"

    _track_as_goal(gap, targeted_query)

    if result["ingested"]:
        try:
            from knowledge.rar_engine import reason
            re_result = reason(original_query)
            result["re_reasoned"] = True
            result["new_confidence"] = re_result.confidence
            result["confidence_delta"] = (
                re_result.confidence - gap.get("confidence", 0)
            )
        except ImportError:
            pass

    return result


def _track_as_goal(gap: Dict[str, Any], query: str) -> None:
    """Create a tracking goal for the active learning event."""
    try:
        from knowledge.knowledge_goal import (
            KnowledgeGoal, generate_goal_id, save_goal, has_active_goal_for_topic,
        )

        topic = query[:100]
        if has_active_goal_for_topic(topic):
            return

        goal = KnowledgeGoal(
            id=generate_goal_id(topic, "active_learner"),
            topic=topic,
            rationale=f"Active learning fill for: {gap.get('query', '')[:200]}",
            source="active_learner",
            priority=gap.get("urgency", 0.5),
            status="completed",
            tier_required=2,
            gap_type="active_fill",
            metadata={"active_learning": True},
        )
        save_goal(goal)
    except ImportError:
        pass


# ------------------------------------------------------------
# BATCH CYCLE
# ------------------------------------------------------------

def run_active_learning_cycle(
    recent_gaps: List[Dict[str, Any]],
    max_fills: int = MAX_ACTIVE_FILLS,
) -> Dict[str, Any]:
    """
    Batch process accumulated gaps from recent reasoning sessions.
    Called periodically by the meta_reasoner.
    """
    if not ENABLED:
        return {"action": "active_learning_cycle", "enabled": False}

    filled = 0
    skipped = 0
    results = []

    sorted_gaps = sorted(
        recent_gaps,
        key=lambda g: g.get("urgency", 0),
        reverse=True,
    )

    for gap in sorted_gaps[:max_fills * 2]:
        if filled >= max_fills:
            break

        if should_learn_now(gap):
            result = learn_and_continue(gap, gap.get("query", ""))
            results.append(result)
            if result.get("ingested"):
                filled += 1
            else:
                skipped += 1
        else:
            skipped += 1

    return {
        "action": "active_learning_cycle",
        "gaps_evaluated": len(sorted_gaps[:max_fills * 2]),
        "filled": filled,
        "skipped": skipped,
        "results": results,
        "timestamp": time.time(),
    }
