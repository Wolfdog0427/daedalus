# knowledge/curiosity_engine.py

"""
Curiosity Engine

Enables Daedalus to autonomously identify knowledge gaps and propose
learning goals. This is the module that turns "I don't know about
astrophysics" into "I should learn about astrophysics because my
knowledge graph references stellar phenomena with no backing structure."

Architecture fit:
- Reads the self-model (blind spots, coverage, coherence)
- Reads the knowledge graph (topology, missing links, shallow clusters)
- Formulates structured KnowledgeGoals with rationale and priority
- Routes goals through the existing tier/governance system
- Executes acquisition through batch_ingestion with quality gates
- Uses the LLM adapter when available; falls back to symbolic analysis

Governance boundary:
- Knowledge acquisition does NOT expand autonomy, modify behavior,
  change governance, or alter safety invariants.
- Tier 2+: auto-approved for domains adjacent to existing knowledge
- Tier 3: auto-approved for novel/frontier domains
- Operator is always notified and can reject/pause any goal
- Quality gates pause acquisition if coherence or consistency degrades
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

from knowledge.knowledge_goal import (
    KnowledgeGoal,
    generate_goal_id,
    save_goal,
    has_active_goal_for_topic,
    count_active_goals,
    list_goals,
    update_goal_status,
)
from knowledge.self_model import get_self_model, update_self_model
from knowledge.knowledge_graph import (
    get_connected_components,
    compute_entity_centrality,
    get_entity_info,
)
from knowledge.graph_reasoner import predict_missing_links, cluster_summary
from knowledge.llm_adapter import llm_adapter


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

MAX_ACTIVE_GOALS = 8
MIN_CLUSTER_DEPTH = 3  # entities below this count = shallow
BLIND_SPOT_THRESHOLD = 0.3  # coverage below this triggers curiosity
FRONTIER_LINK_THRESHOLD = 0.4  # missing-link score above this = frontier
MAX_PROPOSALS_PER_CYCLE = 5
GOAL_EXPIRY_SECONDS = 86400 * 365  # approved goals older than 1 year expire
BACKPRESSURE_THRESHOLD = MAX_ACTIVE_GOALS * 2  # defer proposals when queue too deep


# ------------------------------------------------------------
# GAP DETECTION
# ------------------------------------------------------------

def detect_blind_spot_gaps(self_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Identify gaps from self-model blind spots.
    These are topics with minimal representation in the knowledge base.
    """
    blind_spots = self_model.get("blind_spots", [])
    if not blind_spots:
        return []

    gaps = []
    for spot in blind_spots[:20]:
        info = get_entity_info(spot)
        occurrences = info.get("occurrences", 0) if info else 0
        gaps.append({
            "type": "blind_spot",
            "topic": spot,
            "occurrences": occurrences,
            "severity": 1.0 if occurrences == 0 else max(0.1, 1.0 - occurrences / 10),
        })

    return gaps


def detect_shallow_cluster_gaps() -> List[Dict[str, Any]]:
    """
    Identify knowledge clusters that are too shallow to reason over.
    A cluster with fewer than MIN_CLUSTER_DEPTH entities suggests
    surface-level knowledge that would benefit from deepening.
    """
    components = get_connected_components()
    gaps = []

    for comp in components:
        if 1 < len(comp) < MIN_CLUSTER_DEPTH:
            representative = comp[0]
            summary = cluster_summary(representative)
            domain_hint = representative

            gaps.append({
                "type": "shallow_cluster",
                "topic": domain_hint,
                "entities": comp,
                "size": len(comp),
                "severity": max(0.2, 1.0 - len(comp) / MIN_CLUSTER_DEPTH),
            })

    return gaps[:10]


def detect_frontier_gaps() -> List[Dict[str, Any]]:
    """
    Identify frontier domains: areas where missing-link predictions
    cluster around unknown entities. These represent domains the
    knowledge graph "points toward" but doesn't yet cover.
    """
    central = compute_entity_centrality()[:80]
    frontier_domains: Dict[str, float] = defaultdict(float)

    for entity, _ in central:
        missing = predict_missing_links(entity, limit=5)
        for candidate, score in missing:
            if score >= FRONTIER_LINK_THRESHOLD:
                info = get_entity_info(candidate)
                if info is None or info.get("occurrences", 0) < 2:
                    frontier_domains[candidate] += score

    gaps = []
    ranked = sorted(frontier_domains.items(), key=lambda x: x[1], reverse=True)
    for topic, score in ranked[:10]:
        gaps.append({
            "type": "frontier",
            "topic": topic,
            "link_score": score,
            "severity": min(1.0, score),
        })

    return gaps


def detect_all_gaps(self_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aggregate all gap types into a single ranked list."""
    gaps = []
    gaps.extend(detect_blind_spot_gaps(self_model))
    gaps.extend(detect_shallow_cluster_gaps())
    gaps.extend(detect_frontier_gaps())

    gaps.sort(key=lambda g: g["severity"], reverse=True)
    return gaps


# ------------------------------------------------------------
# GOAL FORMULATION
# ------------------------------------------------------------

def _compute_priority(gap: Dict[str, Any], self_model: Dict[str, Any]) -> float:
    """
    Score a gap for goal priority based on:
    - Gap severity (how thin the knowledge is)
    - Graph coherence impact (will learning this improve coherence?)
    - Coverage breadth (how many existing entities connect to this domain?)
    """
    severity = gap.get("severity", 0.5)
    coherence = self_model.get("confidence", {}).get("graph_coherence", 0.5)

    coherence_boost = max(0.0, 0.5 - coherence)

    coverage = self_model.get("coverage", {})
    entity_count = coverage.get("entity_count", 0)
    breadth_factor = min(0.3, entity_count / 1000 * 0.3) if entity_count > 0 else 0.0

    return min(1.0, severity * 0.5 + coherence_boost * 0.3 + breadth_factor * 0.2)


def _determine_tier(gap: Dict[str, Any]) -> int:
    """
    Determine the minimum tier required for this goal.
    - Tier 2: adjacent domains (shallow clusters, blind spots with some coverage)
    - Tier 3: novel/frontier domains (no existing coverage)
    """
    gap_type = gap.get("type", "")
    if gap_type == "frontier":
        return 3
    if gap_type == "blind_spot" and gap.get("occurrences", 0) == 0:
        return 3
    return 2


def _build_rationale(gap: Dict[str, Any]) -> str:
    """Generate a human-readable rationale for why this goal was proposed."""
    gap_type = gap.get("type", "unknown")
    topic = gap.get("topic", "unknown")

    if gap_type == "blind_spot":
        occ = gap.get("occurrences", 0)
        if occ == 0:
            return (
                f"The topic '{topic}' appears in knowledge graph references "
                f"but has no backing knowledge items."
            )
        return (
            f"The topic '{topic}' has minimal coverage ({occ} occurrences) "
            f"relative to its graph connectivity."
        )

    if gap_type == "shallow_cluster":
        size = gap.get("size", 0)
        return (
            f"The knowledge cluster around '{topic}' contains only "
            f"{size} entities, too shallow for reliable reasoning."
        )

    if gap_type == "frontier":
        score = gap.get("link_score", 0)
        return (
            f"Missing-link predictions converge on '{topic}' "
            f"(score {score:.2f}), suggesting an adjacent domain "
            f"the knowledge graph is approaching but hasn't mapped."
        )

    return f"Knowledge gap detected for topic '{topic}'."


def formulate_goals(
    gaps: List[Dict[str, Any]],
    self_model: Dict[str, Any],
) -> List[KnowledgeGoal]:
    """
    Convert detected gaps into structured KnowledgeGoal objects.
    Filters out topics that already have active goals.
    """
    goals = []

    for gap in gaps[:MAX_PROPOSALS_PER_CYCLE]:
        topic = gap.get("topic", "")
        if not topic:
            continue

        if has_active_goal_for_topic(topic):
            continue

        if count_active_goals() >= MAX_ACTIVE_GOALS:
            break

        priority = _compute_priority(gap, self_model)
        tier = _determine_tier(gap)

        goal = KnowledgeGoal(
            id=generate_goal_id(topic, "curiosity_engine"),
            topic=topic,
            rationale=_build_rationale(gap),
            source="curiosity_engine",
            priority=priority,
            status="proposed",
            tier_required=tier,
            related_entities=gap.get("entities", []),
            related_blind_spots=[topic] if gap["type"] == "blind_spot" else [],
            gap_type=gap.get("type", ""),
        )

        goals.append(goal)

    return goals


# ------------------------------------------------------------
# ACQUISITION PLANNING
# ------------------------------------------------------------

def create_acquisition_plan(goal: KnowledgeGoal) -> List[Dict[str, Any]]:
    """
    Generate a phased acquisition plan for a knowledge goal.
    Uses the LLM adapter if available; falls back to a structured
    symbolic plan based on graph topology.
    """
    if llm_adapter.is_available():
        return _llm_assisted_plan(goal)
    return _symbolic_plan(goal)


def _llm_assisted_plan(goal: KnowledgeGoal) -> List[Dict[str, Any]]:
    """Use the LLM to generate a richer acquisition plan."""
    existing_entities = [e for e, _ in compute_entity_centrality()[:30]]
    existing_summary = ", ".join(existing_entities)

    result = llm_adapter.generate_acquisition_plan(
        topic=goal.topic,
        existing_knowledge_summary=existing_summary,
        gap_description=goal.rationale,
    )

    if result.get("available") and result.get("phases"):
        phases = []
        for i, phase in enumerate(result.get("phases", [])):
            verification = "deep" if i == 0 else "standard"
            phases.append({
                "name": phase.get("name", f"Phase {i+1}"),
                "concepts": phase.get("concepts", []),
                "builds_on": phase.get("builds_on", ""),
                "verification_intensity": verification,
                "status": "pending",
                "items_ingested": 0,
            })
        return phases

    return _symbolic_plan(goal)


def _symbolic_plan(goal: KnowledgeGoal) -> List[Dict[str, Any]]:
    """
    Fallback: generate a structured plan from graph topology alone.
    Phase 1: foundational concepts (entities directly named)
    Phase 2: relationships (connect to existing graph)
    Phase 3: depth (second-hop entities, nuances)
    """
    related = goal.related_entities[:10]

    return [
        {
            "name": f"Foundations of {goal.topic}",
            "concepts": [goal.topic] + related[:3],
            "builds_on": "",
            "verification_intensity": "deep",
            "status": "pending",
            "items_ingested": 0,
        },
        {
            "name": f"Relationships and context for {goal.topic}",
            "concepts": related[3:7] if len(related) > 3 else [goal.topic],
            "builds_on": f"Foundations of {goal.topic}",
            "verification_intensity": "standard",
            "status": "pending",
            "items_ingested": 0,
        },
        {
            "name": f"Depth and nuance for {goal.topic}",
            "concepts": related[7:] if len(related) > 7 else [goal.topic],
            "builds_on": f"Relationships and context for {goal.topic}",
            "verification_intensity": "standard",
            "status": "pending",
            "items_ingested": 0,
        },
    ]


# ------------------------------------------------------------
# QUALITY GATE
# ------------------------------------------------------------

def run_quality_gate(goal: KnowledgeGoal) -> Dict[str, Any]:
    """
    After an acquisition batch, check whether knowledge quality
    improved or degraded. If degraded, recommend pausing.
    """
    current_model = update_self_model()

    _conf = current_model.get("confidence", {})
    coherence_now = _conf.get("graph_coherence", 0.0)
    consistency_now = _conf.get("consistency", 0.0)
    quality_now = _conf.get("knowledge_quality", 0.0)

    before = goal.quality_before or {}
    coherence_before = before.get("graph_coherence", coherence_now)
    consistency_before = before.get("consistency", consistency_now)

    coherence_delta = coherence_now - coherence_before
    consistency_delta = consistency_now - consistency_before

    gate_result = {
        "passed": True,
        "coherence_before": coherence_before,
        "coherence_after": coherence_now,
        "coherence_delta": coherence_delta,
        "consistency_before": consistency_before,
        "consistency_after": consistency_now,
        "consistency_delta": consistency_delta,
        "quality": quality_now,
        "recommendation": "continue",
    }

    if coherence_delta < -0.15:
        gate_result["passed"] = False
        gate_result["recommendation"] = "pause_coherence_degraded"

    if consistency_delta < -0.20:
        gate_result["passed"] = False
        gate_result["recommendation"] = "pause_consistency_degraded"

    if coherence_delta < -0.10 and consistency_delta < -0.10:
        gate_result["passed"] = False
        gate_result["recommendation"] = "pause_dual_degradation"

    return gate_result


# ------------------------------------------------------------
# GOAL HYGIENE (G1 + G3)
# ------------------------------------------------------------

def expire_stale_goals() -> int:
    """
    Expire approved goals that have been waiting too long for execution.
    The knowledge landscape evolves — a gap detected a year ago may no
    longer exist. Expired goals will be re-detected and re-proposed by
    gap detection if they are still relevant.
    """
    now = time.time()
    expired = 0
    for goal in list_goals(status="approved", limit=200):
        age = now - goal.updated_at
        if age > GOAL_EXPIRY_SECONDS:
            update_goal_status(goal.id, "expired")
            expired += 1
    return expired


# ------------------------------------------------------------
# MAIN CYCLE
# ------------------------------------------------------------

def run_curiosity_cycle(
    self_model: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a full curiosity cycle:
    1. Detect knowledge gaps from self-model + graph topology
    2. Formulate structured goals with rationale and priority
    3. Save proposed goals for governance review
    4. Return a cycle report

    This function proposes goals but does NOT execute them.
    Execution happens through the integration layer after
    tier-appropriate governance approval.
    """
    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "gaps_detected": [],
        "goals_proposed": [],
        "goals_expired": 0,
        "skipped_reasons": [],
    }

    if self_model is None:
        self_model = get_self_model()

    # G1: Expire stale approved goals before counting active
    report["goals_expired"] = expire_stale_goals()

    if count_active_goals() >= MAX_ACTIVE_GOALS:
        report["skipped_reasons"].append("max_active_goals_reached")
        return report

    # G3: Backpressure — defer new proposals when approved queue is deep
    approved_backlog = len(list_goals(status="approved", limit=200))
    if approved_backlog >= BACKPRESSURE_THRESHOLD:
        report["skipped_reasons"].append("backpressure_approved_queue")
        return report

    # 1. Detect gaps
    gaps = detect_all_gaps(self_model)
    report["gaps_detected"] = [
        {"topic": g["topic"], "type": g["type"], "severity": g["severity"]}
        for g in gaps
    ]

    if not gaps:
        report["skipped_reasons"].append("no_gaps_detected")
        return report

    # 2. Formulate goals
    goals = formulate_goals(gaps, self_model)

    # 3. Enhance with LLM relevance assessment if available
    if llm_adapter.is_available():
        central_entities = [e for e, _ in compute_entity_centrality()[:30]]
        blind_spots = self_model.get("blind_spots", [])

        for goal in goals:
            assessment = llm_adapter.assess_domain_relevance(
                domain=goal.topic,
                existing_entities=central_entities,
                blind_spots=blind_spots,
            )
            if assessment.get("available"):
                llm_relevance = assessment.get("relevance", 0.5)
                goal.priority = goal.priority * 0.6 + llm_relevance * 0.4
                goal.metadata["llm_relevance"] = llm_relevance
                goal.metadata["llm_rationale"] = assessment.get("rationale", "")

    # 4. Save proposed goals
    for goal in goals:
        save_goal(goal)
        report["goals_proposed"].append({
            "id": goal.id,
            "topic": goal.topic,
            "priority": goal.priority,
            "tier_required": goal.tier_required,
            "gap_type": goal.gap_type,
            "rationale": goal.rationale,
        })

    return report


def approve_and_plan(goal_id: str) -> Dict[str, Any]:
    """
    Approve a proposed goal and generate its acquisition plan.
    Called by the governance layer or operator.
    """
    from knowledge.knowledge_goal import load_goal as _load

    goal = _load(goal_id)
    if goal is None:
        return {"error": "goal_not_found"}

    if goal.status != "proposed":
        return {"error": f"goal_status_is_{goal.status}_not_proposed"}

    current_model = get_self_model()
    goal.quality_before = {
        "graph_coherence": current_model.get("confidence", {}).get("graph_coherence", 0.0),
        "consistency": current_model.get("confidence", {}).get("consistency", 0.0),
        "knowledge_quality": current_model.get("confidence", {}).get("knowledge_quality", 0.0),
    }

    goal.phases = create_acquisition_plan(goal)
    goal.status = "approved"
    save_goal(goal)

    return {
        "goal_id": goal.id,
        "topic": goal.topic,
        "status": "approved",
        "phases": goal.phases,
    }


# ------------------------------------------------------------
# GOAL EXECUTION (F3)
# ------------------------------------------------------------

def execute_next_phase(goal_id: str) -> Dict[str, Any]:
    """
    Execute the next pending phase of an approved knowledge goal.
    Generates batch items from the phase's concept list and routes
    them through batch_ingestion. Returns a per-phase report.

    This is the missing link: approved goals now actually execute.
    """
    from knowledge.knowledge_goal import load_goal as _load

    goal = _load(goal_id)
    if goal is None:
        return {"error": "goal_not_found"}

    if goal.status not in ("approved", "in_progress"):
        return {"error": f"goal_status_is_{goal.status}", "goal_id": goal_id}

    # Find the first pending phase
    phase_idx = None
    phase_data = None
    for i, phase in enumerate(goal.phases):
        if isinstance(phase, dict) and phase.get("status") == "pending":
            phase_idx = i
            phase_data = phase
            break

    if phase_data is None:
        goal.status = "completed"
        save_goal(goal)
        return {"goal_id": goal_id, "status": "completed", "reason": "all_phases_done"}

    # Mark goal and phase as in-progress
    goal.status = "in_progress"
    phase_data["status"] = "in_progress"
    save_goal(goal)

    # Build batch items from the phase's concepts
    concepts = phase_data.get("concepts", [])
    if not concepts:
        concepts = [goal.topic]

    items = []
    for concept in concepts:
        query_text = _build_acquisition_query(concept, goal.topic, phase_data.get("name", ""))
        items.append({
            "text": query_text,
            "source": f"curiosity:{goal.topic}",
            "metadata": {"goal_id": goal_id, "phase": phase_data.get("name", "")},
        })

    # Route through batch ingestion
    try:
        from knowledge.batch_ingestion import ingest_batch
        intensity = phase_data.get("verification_intensity", "standard")
        result = ingest_batch(
            items=items,
            source=f"curiosity:{goal.topic}",
            verification_intensity=intensity,
            goal_id=goal_id,
        )

        phase_data["items_ingested"] = result.get("ingested", 0)
        phase_data["status"] = "completed"
        goal.total_items_ingested += result.get("ingested", 0)
        goal.total_items_verified += result.get("ingested", 0) - result.get("deferred", 0)
        goal.total_items_rejected += result.get("rejected", 0)
        save_goal(goal)

        return {
            "goal_id": goal_id,
            "phase": phase_data.get("name"),
            "phase_index": phase_idx,
            "ingested": result.get("ingested", 0),
            "rejected": result.get("rejected", 0),
            "status": "phase_completed",
        }
    except Exception as exc:
        phase_data["status"] = "failed"
        save_goal(goal)
        return {"goal_id": goal_id, "error": f"{type(exc).__name__}: {exc}"}


def _build_acquisition_query(concept: str, topic: str, phase_name: str) -> str:
    """Build descriptive text for a concept within a learning goal."""
    if llm_adapter.is_available():
        prompt = (
            f"Provide a comprehensive factual summary about '{concept}' "
            f"in the context of '{topic}'. "
            f"Focus on: {phase_name}. "
            f"Include key definitions, relationships, and notable facts."
        )
        result = llm_adapter.complete(prompt, max_tokens=512)
        if result.strip():
            return result

    return (
        f"Knowledge item about {concept}. "
        f"Domain: {topic}. Phase: {phase_name}. "
        f"This concept is part of a structured learning goal."
    )


def get_executable_goals() -> List[KnowledgeGoal]:
    """Return goals that are approved/in_progress with pending phases,
    sorted by priority (highest first) so the most impactful gaps
    get execution slots first."""
    goals = list_goals(status="approved") + list_goals(status="in_progress")
    executable = []
    for goal in goals:
        for phase in goal.phases:
            if isinstance(phase, dict) and phase.get("status") == "pending":
                executable.append(goal)
                break
    executable.sort(key=lambda g: g.priority, reverse=True)
    return executable
