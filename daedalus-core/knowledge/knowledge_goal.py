# knowledge/knowledge_goal.py

"""
Knowledge Goal

Data structures and persistence for knowledge acquisition goals.

A KnowledgeGoal represents a self-identified or operator-directed
intention to learn about a topic, domain, or technique. Goals are:
- proposed by the CuriosityEngine or the operator
- prioritized by relevance, quality impact, and risk
- governed by the existing tier system (Tier 2+ for auto-approve,
  operator notified; structural/behavioral changes still require
  operator approval)
- executed through the batch ingestion pipeline
- quality-gated after each acquisition batch

This module only defines data structures and persistence.
The CuriosityEngine owns the lifecycle logic.
"""

from __future__ import annotations

import json
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from knowledge._atomic_io import atomic_write_json


# ------------------------------------------------------------
# STORAGE
# ------------------------------------------------------------

GOALS_DIR = Path("data/knowledge_goals")
GOALS_FILE = GOALS_DIR / "goals.json"


def _ensure_storage():
    GOALS_DIR.mkdir(parents=True, exist_ok=True)
    if not GOALS_FILE.exists():
        atomic_write_json(GOALS_FILE, [])


# ------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------

@dataclass
class AcquisitionPhase:
    """A single phase within a knowledge acquisition plan."""
    name: str
    concepts: List[str]
    builds_on: str = ""
    verification_intensity: str = "standard"  # "light" | "standard" | "deep"
    status: str = "pending"  # "pending" | "in_progress" | "completed" | "failed"
    items_ingested: int = 0
    quality_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class KnowledgeGoal:
    """
    A structured intention to acquire knowledge about a topic.

    Lifecycle: proposed -> approved -> in_progress -> completed
                                   \-> rejected
                                   \-> paused (quality gate tripped)
    """
    id: str
    topic: str
    rationale: str
    source: str  # "curiosity_engine" | "operator" | "meta_reasoner"
    priority: float  # 0.0 - 1.0
    status: str  # "proposed" | "approved" | "in_progress" | "completed" | "rejected" | "paused"
    tier_required: int  # minimum autonomy tier to execute (2 or 3)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # What triggered this goal
    related_entities: List[str] = field(default_factory=list)
    related_blind_spots: List[str] = field(default_factory=list)
    gap_type: str = ""  # "blind_spot" | "shallow_cluster" | "missing_link" | "frontier" | "operator_directed"

    # Acquisition plan (populated after approval)
    phases: List[Dict[str, Any]] = field(default_factory=list)

    # Quality tracking
    quality_before: Optional[Dict[str, Any]] = None
    quality_after: Optional[Dict[str, Any]] = None
    coherence_delta: float = 0.0
    consistency_delta: float = 0.0

    # Execution tracking
    total_items_ingested: int = 0
    total_items_verified: int = 0
    total_items_rejected: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


def generate_goal_id(topic: str, source: str) -> str:
    raw = f"{topic}:{source}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ------------------------------------------------------------
# PERSISTENCE
# ------------------------------------------------------------

def _load_goals() -> List[Dict[str, Any]]:
    _ensure_storage()
    try:
        return json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_goals(goals: List[Dict[str, Any]]) -> None:
    _ensure_storage()
    atomic_write_json(GOALS_FILE, goals)


def save_goal(goal: KnowledgeGoal) -> None:
    goals = _load_goals()
    goal.updated_at = time.time()

    existing_idx = None
    for i, g in enumerate(goals):
        if g.get("id") == goal.id:
            existing_idx = i
            break

    data = asdict(goal)
    if existing_idx is not None:
        goals[existing_idx] = data
    else:
        goals.append(data)

    _save_goals(goals)


def load_goal(goal_id: str) -> Optional[KnowledgeGoal]:
    for g in _load_goals():
        if g.get("id") == goal_id:
            return _dict_to_goal(g)
    return None


def list_goals(
    status: Optional[str] = None,
    limit: int = 50,
) -> List[KnowledgeGoal]:
    goals = _load_goals()
    if status:
        goals = [g for g in goals if g.get("status") == status]
    goals = goals[:limit]
    return [_dict_to_goal(g) for g in goals]


def update_goal_status(goal_id: str, status: str) -> bool:
    goals = _load_goals()
    for g in goals:
        if g.get("id") == goal_id:
            g["status"] = status
            g["updated_at"] = time.time()
            _save_goals(goals)
            return True
    return False


def _dict_to_goal(data: Dict[str, Any]) -> KnowledgeGoal:
    phases_raw = data.pop("phases", [])
    goal = KnowledgeGoal(**{
        k: v for k, v in data.items()
        if k in KnowledgeGoal.__dataclass_fields__
    })
    goal.phases = phases_raw
    return goal


# ------------------------------------------------------------
# QUERIES
# ------------------------------------------------------------

def has_active_goal_for_topic(topic: str) -> bool:
    """Check if there's already an active goal for this topic."""
    active_statuses = {"proposed", "approved", "in_progress"}
    for g in _load_goals():
        if g.get("topic", "").lower() == topic.lower():
            if g.get("status") in active_statuses:
                return True
    return False


def get_completed_topics() -> List[str]:
    """Return list of topics that have been successfully learned."""
    return [
        g["topic"]
        for g in _load_goals()
        if g.get("status") == "completed"
    ]


def count_active_goals() -> int:
    active_statuses = {"proposed", "approved", "in_progress"}
    return sum(
        1 for g in _load_goals()
        if g.get("status") in active_statuses
    )
