# knowledge/goal_planner.py

"""
Goal Decomposition and Planning

Breaks complex learning objectives into dependency graphs of sub-goals.
"Learn climate science" becomes a DAG: atmospheric physics -> ocean
circulation -> radiative transfer -> climate modeling.

Architecture fit:
- Called by curiosity_engine during approve_and_plan for complex goals
- Extends KnowledgeGoal with parent/dependency linkage
- Uses LLM adapter for intelligent decomposition; falls back to
  graph-topology-based splitting
- Sub-goals are independent KnowledgeGoals with dependency tracking
- Respects the existing governance pipeline — sub-goals go through
  the same approval flow as top-level goals

Simple goals (single topic) skip decomposition entirely.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional

from knowledge.knowledge_goal import (
    KnowledgeGoal,
    generate_goal_id,
    save_goal,
    load_goal,
    has_active_goal_for_topic,
)


# ------------------------------------------------------------
# COMPLEXITY ASSESSMENT
# ------------------------------------------------------------

COMPLEXITY_THRESHOLD = 0.6


def is_complex_goal(goal: KnowledgeGoal) -> bool:
    """
    Determine whether a goal should be decomposed.
    Complex goals have broad topics, many related entities,
    or high-tier requirements suggesting depth.
    """
    score = 0.0

    if len(goal.related_entities) > 5:
        score += 0.3
    if goal.tier_required >= 3:
        score += 0.2
    if goal.priority > 0.7:
        score += 0.1

    topic_words = goal.topic.split()
    if len(topic_words) > 3:
        score += 0.2

    if goal.gap_type == "frontier":
        score += 0.2

    return score >= COMPLEXITY_THRESHOLD


# ------------------------------------------------------------
# PREREQUISITE IDENTIFICATION
# ------------------------------------------------------------

def identify_prerequisites(topic: str) -> List[str]:
    """
    Determine what topics must be learned before this one.
    Uses LLM when available; falls back to graph neighborhood.
    """
    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            return _llm_prerequisites(topic, llm_adapter)
    except ImportError:
        pass

    return _graph_prerequisites(topic)


def _llm_prerequisites(topic: str, adapter: Any) -> List[str]:
    """Use LLM to identify prerequisite topics."""
    prompt = (
        f"What are the 3-5 prerequisite topics someone must understand "
        f"before they can learn about '{topic}'? "
        f"List them in learning order, one per line. "
        f"Just the topic names, nothing else."
    )
    try:
        result = adapter.complete(prompt, max_tokens=128, temperature=0.3)
        prereqs = [line.strip().strip("- ").strip("0123456789. ")
                   for line in result.strip().split("\n")
                   if line.strip()]
        return prereqs[:5]
    except Exception:
        return _graph_prerequisites(topic)


def _graph_prerequisites(topic: str) -> List[str]:
    """Identify prerequisites from graph topology."""
    try:
        from knowledge.knowledge_graph import get_neighbors
        neighbors = get_neighbors(topic)
        if not neighbors:
            return []
        prereqs = []
        for neighbor in neighbors[:5]:
            name = neighbor.get("object", "")
            if name and name.lower() != topic.lower():
                prereqs.append(name)
        return prereqs
    except ImportError:
        return []


# ------------------------------------------------------------
# GOAL DECOMPOSITION
# ------------------------------------------------------------

def decompose_goal(goal: KnowledgeGoal) -> List[KnowledgeGoal]:
    """
    Break a complex goal into sub-goals with dependency ordering.
    Returns a list of KnowledgeGoal objects linked to the parent
    via parent_goal_id and dependency_ids.
    """
    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            return _llm_decompose(goal, llm_adapter)
    except ImportError:
        pass

    return _symbolic_decompose(goal)


def _llm_decompose(goal: KnowledgeGoal, adapter: Any) -> List[KnowledgeGoal]:
    """Use LLM for intelligent goal decomposition."""
    prompt = (
        f"Break down the learning goal '{goal.topic}' into 3-5 ordered sub-topics. "
        f"Each sub-topic should be a focused learning objective. "
        f"List them in dependency order (learn first at top). "
        f"Format: one topic per line, just the topic name.\n"
        f"Context: {goal.rationale}"
    )

    try:
        result = adapter.complete(prompt, max_tokens=200, temperature=0.3)
        sub_topics = [line.strip().strip("- ").strip("0123456789. ")
                      for line in result.strip().split("\n")
                      if line.strip()]
        sub_topics = sub_topics[:5]
    except Exception:
        return _symbolic_decompose(goal)

    if len(sub_topics) < 2:
        return _symbolic_decompose(goal)

    return _build_sub_goals(goal, sub_topics)


def _symbolic_decompose(goal: KnowledgeGoal) -> List[KnowledgeGoal]:
    """
    Fallback decomposition using graph topology.
    Splits by related entities into foundation → context → depth.
    """
    entities = goal.related_entities[:9]
    if len(entities) < 3:
        entities = [goal.topic, f"{goal.topic} fundamentals",
                    f"{goal.topic} applications"]

    chunk_size = max(1, len(entities) // 3)
    sub_topics = [
        f"Foundations of {goal.topic}",
        f"Core concepts in {goal.topic}",
        f"Advanced {goal.topic}",
    ]

    return _build_sub_goals(goal, sub_topics)


def _build_sub_goals(
    parent: KnowledgeGoal,
    sub_topics: List[str],
) -> List[KnowledgeGoal]:
    """Create linked sub-goal objects from topic list."""
    sub_goals = []
    prev_id = None

    for i, topic in enumerate(sub_topics):
        if has_active_goal_for_topic(topic):
            continue

        sub_id = generate_goal_id(topic, "goal_planner")
        dep_ids = [prev_id] if prev_id else []

        sub_goal = KnowledgeGoal(
            id=sub_id,
            topic=topic,
            rationale=f"Sub-goal of '{parent.topic}': {topic}",
            source="goal_planner",
            priority=parent.priority * (1.0 - i * 0.05),
            status="proposed",
            tier_required=parent.tier_required,
            related_entities=parent.related_entities[:3],
            gap_type=parent.gap_type,
            metadata={
                "parent_goal_id": parent.id,
                "dependency_ids": dep_ids,
                "sub_goal_index": i,
                "total_sub_goals": len(sub_topics),
            },
        )

        sub_goals.append(sub_goal)
        prev_id = sub_id

    return sub_goals


# ------------------------------------------------------------
# EXECUTION DAG
# ------------------------------------------------------------

def build_execution_dag(goal: KnowledgeGoal) -> Dict[str, Any]:
    """
    Build an ordered execution plan showing which sub-goals
    can run in parallel vs. must be sequential.
    """
    sub_goal_ids = goal.metadata.get("sub_goal_ids", [])
    if not sub_goal_ids:
        return {
            "goal_id": goal.id,
            "type": "simple",
            "execution_order": [goal.id],
        }

    nodes = []
    for sg_id in sub_goal_ids:
        sg = load_goal(sg_id)
        if sg:
            deps = sg.metadata.get("dependency_ids", [])
            nodes.append({
                "id": sg.id,
                "topic": sg.topic,
                "status": sg.status,
                "dependencies": deps,
            })

    return {
        "goal_id": goal.id,
        "type": "complex",
        "nodes": nodes,
        "total_sub_goals": len(nodes),
    }


def get_next_executable(goal: KnowledgeGoal) -> Optional[KnowledgeGoal]:
    """
    Which sub-goal should execute next? Returns the highest-priority
    sub-goal whose dependencies are all completed.
    """
    sub_goal_ids = goal.metadata.get("sub_goal_ids", [])
    if not sub_goal_ids:
        return None

    completed_ids = set()
    candidates = []

    for sg_id in sub_goal_ids:
        sg = load_goal(sg_id)
        if sg is None:
            continue
        if sg.status == "completed":
            completed_ids.add(sg.id)
        elif sg.status in ("proposed", "approved"):
            deps = sg.metadata.get("dependency_ids", [])
            if all(d in completed_ids for d in deps):
                candidates.append(sg)

    if not candidates:
        return None

    candidates.sort(key=lambda g: g.priority, reverse=True)
    return candidates[0]


# ------------------------------------------------------------
# ADAPTIVE REPLANNING
# ------------------------------------------------------------

def replan_on_failure(
    goal: KnowledgeGoal,
    failed_sub_id: str,
) -> Dict[str, Any]:
    """
    When a sub-goal fails (paused by quality gate or rejected),
    attempt to replan around it.
    """
    failed = load_goal(failed_sub_id)
    if failed is None:
        return {"action": "replan", "status": "failed_goal_not_found"}

    dependents = []
    sub_goal_ids = goal.metadata.get("sub_goal_ids", [])
    for sg_id in sub_goal_ids:
        sg = load_goal(sg_id)
        if sg and failed_sub_id in sg.metadata.get("dependency_ids", []):
            dependents.append(sg)

    for dep in dependents:
        new_deps = [d for d in dep.metadata.get("dependency_ids", [])
                    if d != failed_sub_id]
        dep.metadata["dependency_ids"] = new_deps
        dep.metadata["replanned"] = True
        save_goal(dep)

    return {
        "action": "replan",
        "status": "success",
        "failed_goal": failed_sub_id,
        "dependents_freed": len(dependents),
    }
