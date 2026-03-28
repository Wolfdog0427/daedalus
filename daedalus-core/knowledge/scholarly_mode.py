# knowledge/scholarly_mode.py

"""
Scholarly Mode — Post-Graduate Lifelong Learning Posture

After the Accelerated Bootstrap Protocol (ABP) graduates Daedalus to
PhD/Expert-level across all disciplines, this module governs how the
system continues to learn and grow — like a working scholar rather
than a student.

Five activity pillars, weighted by the system's current needs:

1. CONSOLIDATION — Strengthen what is already known.
   Cross-link related concepts, synthesize higher-order abstractions,
   resolve remaining edge-case contradictions, merge near-duplicate
   entities. Prioritized when the graph is dense but fragmented.

2. REFLECTION — Meta-cognitive self-assessment.
   Identify weakest domains, stale clusters, reasoning chains that
   produced low-confidence answers, and areas where the honesty gap
   is widest. Outputs targeted improvement goals.

3. INTEREST-DRIVEN EXPLORATION — Curiosity with purpose.
   Learn new things not because there's a gap to fill, but because
   operator interactions, federated peer exchanges, or cross-domain
   reasoning suggest an area is becoming relevant. Deep-dives rather
   than shallow sweeps.

4. NEED-BASED LEARNING — Reactive gap-filling.
   When a RAR query reveals missing knowledge, an operator asks about
   an unfamiliar topic, or new information contradicts existing beliefs,
   acquire targeted knowledge immediately.

5. OUTPUT REFINEMENT — Improve reasoning quality.
   Review which explanations and reasoning chains operators found
   helpful vs unhelpful. Strengthen provenance chains, improve
   cross-reference quality, refine LLM prompting strategies.

Governance: All activities route through the existing tier system.
Scholarly mode never expands autonomy, modifies behavior rules, or
alters safety invariants. It only changes the *balance* of how
cognitive resources are allocated.
"""

from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ----------------------------------------------------------------
# ACTIVITY TYPES
# ----------------------------------------------------------------

class ScholarlyActivity(str, Enum):
    CONSOLIDATION = "consolidation"
    REFLECTION = "reflection"
    EXPLORATION = "exploration"
    NEED_BASED = "need_based"
    REFINEMENT = "refinement"


# ----------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------

@dataclass
class ActivityWeights:
    """How cognitive resources are allocated across scholarly activities.
    Weights are relative; they get normalized to sum to 1.0."""
    consolidation: float = 0.30
    reflection: float = 0.15
    exploration: float = 0.20
    need_based: float = 0.25
    refinement: float = 0.10

    def as_dict(self) -> Dict[str, float]:
        total = (self.consolidation + self.reflection + self.exploration
                 + self.need_based + self.refinement)
        if total == 0:
            total = 1.0
        return {
            ScholarlyActivity.CONSOLIDATION: self.consolidation / total,
            ScholarlyActivity.REFLECTION: self.reflection / total,
            ScholarlyActivity.EXPLORATION: self.exploration / total,
            ScholarlyActivity.NEED_BASED: self.need_based / total,
            ScholarlyActivity.REFINEMENT: self.refinement / total,
        }


DEFAULT_WEIGHTS = ActivityWeights()

# Thresholds for adaptive weight shifting
WEAK_DOMAIN_THRESHOLD = 0.70       # coherence below this triggers more consolidation
STALE_CLUSTER_RATIO = 0.05         # >5% stale items shifts toward reflection
HIGH_GAP_RATE = 0.10               # >10% RAR queries with gaps shifts toward need-based
EXPLORATION_COOLDOWN_S = 3600 * 6  # min 6 hours between deep-dive explorations

# Consolidation parameters
SYNTHESIS_MIN_CLUSTER_SIZE = 5     # clusters with >=5 entities can produce synthesis items
CROSS_LINK_WEAK_THRESHOLD = 2      # relations < this between related clusters = weak link
MAX_SYNTHESIS_PER_CYCLE = 3        # max higher-order concepts created per consolidation

# Reflection parameters
REFLECTION_CYCLE_INTERVAL_S = 3600 * 24  # full reflection once per day
MIN_REASONING_SAMPLES = 10         # need this many RAR results before assessing quality

# Exploration parameters
DEEP_DIVE_MAX_ITEMS = 50           # items per interest-driven deep-dive
INTEREST_SIGNAL_DECAY = 0.95       # interest signals decay each cycle

# Need-based parameters
URGENCY_THRESHOLD = 0.6            # gap urgency above this triggers immediate learning
MAX_REACTIVE_ITEMS = 20            # items per reactive learning event


# ----------------------------------------------------------------
# INTEREST TRACKER
# ----------------------------------------------------------------

@dataclass
class InterestSignal:
    """Tracks emerging topics that Daedalus is encountering frequently
    but hasn't yet deeply explored."""
    topic: str
    signal_strength: float = 0.0
    sources: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    explored: bool = False


# ----------------------------------------------------------------
# SCHOLARLY MODE MANAGER
# ----------------------------------------------------------------

class ScholarlyModeManager:
    """Manages the post-graduate learning posture."""

    def __init__(self):
        self.active: bool = False
        self.activated_at: float = 0.0
        self.weights: ActivityWeights = ActivityWeights()
        self.interest_signals: Dict[str, InterestSignal] = {}

        # Counters
        self.consolidation_cycles: int = 0
        self.synthesis_items_created: int = 0
        self.cross_links_strengthened: int = 0
        self.reflection_cycles: int = 0
        self.weak_areas_identified: int = 0
        self.improvement_goals_proposed: int = 0
        self.deep_dives_completed: int = 0
        self.deep_dive_items: int = 0
        self.need_based_events: int = 0
        self.need_based_items: int = 0
        self.refinement_cycles: int = 0
        self.reasoning_chains_improved: int = 0

        self._last_reflection: float = 0.0
        self._last_exploration: float = 0.0

    def activate(self) -> Dict[str, Any]:
        """Activate scholarly mode (typically after ABP graduation)."""
        self.active = True
        self.activated_at = time.time()
        return {
            "status": "scholarly_mode_activated",
            "timestamp": self.activated_at,
            "weights": self.weights.as_dict(),
        }

    def is_active(self) -> bool:
        return self.active

    # ---- Adaptive weight adjustment ----

    def adapt_weights(self, system_state: Dict[str, Any]) -> Dict[str, float]:
        """Shift activity weights based on current system needs.
        A scholar focuses on what matters most right now."""

        w = ActivityWeights(
            consolidation=DEFAULT_WEIGHTS.consolidation,
            reflection=DEFAULT_WEIGHTS.reflection,
            exploration=DEFAULT_WEIGHTS.exploration,
            need_based=DEFAULT_WEIGHTS.need_based,
            refinement=DEFAULT_WEIGHTS.refinement,
        )

        coherence = system_state.get("coherence", 1.0)
        stale_ratio = system_state.get("stale_ratio", 0.0)
        gap_rate = system_state.get("gap_rate", 0.0)
        pending_contradictions = system_state.get("pending_contradictions", 0)

        # Low coherence -> more consolidation
        if coherence < WEAK_DOMAIN_THRESHOLD:
            deficit = WEAK_DOMAIN_THRESHOLD - coherence
            w.consolidation += deficit * 0.5
            w.exploration -= deficit * 0.25
            w.refinement -= deficit * 0.25

        # High stale ratio -> more reflection
        if stale_ratio > STALE_CLUSTER_RATIO:
            w.reflection += 0.10
            w.exploration -= 0.05
            w.consolidation -= 0.05

        # High gap rate in RAR -> more need-based learning
        if gap_rate > HIGH_GAP_RATE:
            w.need_based += 0.15
            w.exploration -= 0.05
            w.refinement -= 0.05
            w.consolidation -= 0.05

        # Active contradictions -> consolidation priority
        if pending_contradictions > 5:
            w.consolidation += 0.10
            w.exploration -= 0.10

        # Clamp all weights to [0.05, 0.60]
        for attr in ("consolidation", "reflection", "exploration",
                      "need_based", "refinement"):
            setattr(w, attr, max(0.05, min(0.60, getattr(w, attr))))

        self.weights = w
        return w.as_dict()

    # ---- Interest signal management ----

    def record_interest(self, topic: str, source: str, strength: float = 0.1):
        """Record an interest signal from operator query, RAR, or federation."""
        now = time.time()
        if topic in self.interest_signals:
            sig = self.interest_signals[topic]
            sig.signal_strength = min(1.0, sig.signal_strength + strength)
            sig.last_seen = now
            if source not in sig.sources:
                sig.sources.append(source)
        else:
            self.interest_signals[topic] = InterestSignal(
                topic=topic,
                signal_strength=strength,
                sources=[source],
                first_seen=now,
                last_seen=now,
            )

    def decay_interests(self):
        """Apply time decay to interest signals."""
        expired = []
        for topic, sig in self.interest_signals.items():
            sig.signal_strength *= INTEREST_SIGNAL_DECAY
            if sig.signal_strength < 0.01:
                expired.append(topic)
        for topic in expired:
            del self.interest_signals[topic]

    def get_top_interests(self, limit: int = 5) -> List[InterestSignal]:
        """Return highest-signal unexplored topics."""
        candidates = [
            sig for sig in self.interest_signals.values()
            if not sig.explored
        ]
        candidates.sort(key=lambda s: s.signal_strength, reverse=True)
        return candidates[:limit]

    # ---- Activity selection ----

    def select_activity(self, system_state: Dict[str, Any]) -> ScholarlyActivity:
        """Choose which scholarly activity to perform this cycle,
        based on adaptive weights and immediate needs."""

        now = time.time()
        weights = self.adapt_weights(system_state)

        # Immediate needs override weight-based selection
        if system_state.get("urgent_gap"):
            return ScholarlyActivity.NEED_BASED

        if system_state.get("pending_contradictions", 0) > 10:
            return ScholarlyActivity.CONSOLIDATION

        # Time-gated activities
        if (now - self._last_reflection) > REFLECTION_CYCLE_INTERVAL_S:
            if weights[ScholarlyActivity.REFLECTION] > 0.10:
                return ScholarlyActivity.REFLECTION

        # Weighted random selection for normal operation
        import random
        roll = random.random()
        cumulative = 0.0
        for activity, weight in sorted(weights.items(), key=lambda x: -x[1]):
            cumulative += weight
            if roll < cumulative:
                return activity

        return ScholarlyActivity.CONSOLIDATION

    # ---- Consolidation ----

    def run_consolidation(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Strengthen existing knowledge through cross-linking and synthesis."""
        self.consolidation_cycles += 1

        result = {
            "activity": "consolidation",
            "cross_links_created": 0,
            "synthesis_items": 0,
            "contradictions_addressed": 0,
            "duplicates_merged": 0,
        }

        # In the real system, this would call knowledge_graph operations.
        # The integration_layer wraps these with governance.

        try:
            from knowledge.knowledge_graph import get_connected_components
            from knowledge.graph_reasoner import predict_missing_links

            components = get_connected_components()
            for comp in components:
                if len(comp) >= SYNTHESIS_MIN_CLUSTER_SIZE:
                    for entity in comp[:3]:
                        predictions = predict_missing_links(entity, limit=3)
                        for target, score in predictions:
                            if score > 0.6:
                                result["cross_links_created"] += 1
                                self.cross_links_strengthened += 1
        except (ImportError, Exception):
            pass

        return result

    # ---- Reflection ----

    def run_reflection(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Meta-cognitive self-assessment: identify weak areas, propose
        improvement goals, and execute them directly — as long as they
        don't cause identity or governance drift.

        The drift guard rejects any goal that would modify:
        - Governance rules or autonomy tiers
        - Identity invariants or constitutional constraints
        - Safety boundaries or operator trust relationships
        """
        self.reflection_cycles += 1
        self._last_reflection = time.time()

        result = {
            "activity": "reflection",
            "weak_areas": [],
            "improvement_goals_proposed": 0,
            "improvement_goals_executed": 0,
            "drift_rejected": 0,
            "stale_domains": 0,
            "reasoning_quality_assessment": None,
        }

        try:
            from knowledge.self_model import update_self_model
            model = update_self_model()

            blind_spots = model.get("blind_spots", [])
            for spot in blind_spots[:5]:
                result["weak_areas"].append(spot)
                self.weak_areas_identified += 1

            shallow = model.get("coverage", {}).get("shallow_clusters", 0)
            if shallow > 0:
                result["weak_areas"].append(f"{shallow} shallow clusters")

            from knowledge.knowledge_goal import (
                generate_goal_id, save_goal, has_active_goal_for_topic,
                KnowledgeGoal,
            )

            DRIFT_KEYWORDS = {
                "governance", "autonomy", "tier", "permission", "safety",
                "identity", "constitutional", "invariant", "operator trust",
                "self-modification", "rule change",
            }

            for area in result["weak_areas"][:3]:
                topic = area if isinstance(area, str) else str(area)
                if not has_active_goal_for_topic(topic):
                    topic_lower = topic.lower()
                    is_drift = any(kw in topic_lower for kw in DRIFT_KEYWORDS)
                    if is_drift:
                        result["drift_rejected"] += 1
                        # Notify operator that a drift-touching goal was blocked
                        try:
                            from runtime.notification_hooks import notify_escalation_recommended
                            notify_escalation_recommended(
                                3,
                                f"Scholarly reflection proposed improvement "
                                f"touching governance/identity: '{topic}'. "
                                f"Auto-rejected by drift guard. Operator review "
                                f"required if this change is desired.",
                            )
                        except (ImportError, Exception):
                            pass
                        try:
                            from runtime.logging_manager import log_event
                            log_event(
                                "scholarly_drift_rejected",
                                f"Drift guard rejected goal: {topic}",
                                {"topic": topic, "reason": "identity_governance_drift"},
                            )
                        except (ImportError, Exception):
                            pass
                        continue

                    goal = KnowledgeGoal(
                        id=generate_goal_id(topic, "scholarly_reflection"),
                        topic=topic,
                        rationale=f"Scholarly reflection identified '{topic}' as a weak area needing deepening.",
                        source="scholarly_reflection",
                        priority=0.6,
                        status="proposed",
                        tier_required=2,
                        gap_type="reflection_weakness",
                    )
                    save_goal(goal)
                    result["improvement_goals_proposed"] += 1
                    self.improvement_goals_proposed += 1

                    # Route through governed integration layer — this ensures
                    # the autonomy governor and severity gate approve both
                    # the goal approval and execution steps.
                    try:
                        from knowledge.integration_layer import (
                            do_approve_knowledge_goal,
                            do_execute_knowledge_goal,
                        )
                        approve_result = do_approve_knowledge_goal(goal.id)
                        if (approve_result.get("allowed")
                                and not approve_result.get("error")):
                            exec_result = do_execute_knowledge_goal(goal.id)
                            if (exec_result.get("allowed")
                                    and not exec_result.get("error")):
                                result["improvement_goals_executed"] += 1
                    except Exception:
                        pass

        except Exception:
            pass

        return result

    # ---- Interest-driven exploration ----

    def run_exploration(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-dive into a topic of emerging interest."""
        now = time.time()
        if (now - self._last_exploration) < EXPLORATION_COOLDOWN_S:
            return {"activity": "exploration", "skipped": "cooldown_active"}

        top_interests = self.get_top_interests(limit=3)
        if not top_interests:
            return {"activity": "exploration", "skipped": "no_interesting_topics"}

        target = top_interests[0]
        self._last_exploration = now
        self.deep_dives_completed += 1

        result = {
            "activity": "exploration",
            "topic": target.topic,
            "signal_strength": target.signal_strength,
            "sources": target.sources,
            "items_acquired": 0,
            "goal_created": False,
        }

        # Create a deep-dive goal through the standard goal system
        try:
            from knowledge.knowledge_goal import (
                generate_goal_id, save_goal, has_active_goal_for_topic,
                KnowledgeGoal,
            )

            if not has_active_goal_for_topic(target.topic):
                source_str = ", ".join(target.sources[:3])
                goal = KnowledgeGoal(
                    id=generate_goal_id(target.topic, "scholarly_exploration"),
                    topic=target.topic,
                    rationale=(
                        f"Interest-driven deep dive into '{target.topic}'. "
                        f"Signal strength {target.signal_strength:.2f} from: {source_str}. "
                        f"This topic keeps appearing in reasoning and operator interactions."
                    ),
                    source="scholarly_exploration",
                    priority=min(0.9, 0.4 + target.signal_strength * 0.5),
                    status="proposed",
                    tier_required=2,
                    gap_type="interest_exploration",
                )
                save_goal(goal)
                result["goal_created"] = True

            target.explored = True

        except Exception:
            pass

        return result

    # ---- Need-based learning ----

    def run_need_based(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Reactive learning when a specific gap is encountered."""
        self.need_based_events += 1

        result = {
            "activity": "need_based",
            "trigger": system_state.get("gap_trigger", "unknown"),
            "topic": system_state.get("gap_topic", ""),
            "items_acquired": 0,
        }

        # Delegate to the active_learner for actual gap-filling
        try:
            from knowledge.active_learner import learn_and_continue
            gap = system_state.get("active_gap")
            query = system_state.get("gap_query", "")
            if gap:
                learn_result = learn_and_continue(gap, query)
                items = learn_result.get("ingested", 0)
                result["items_acquired"] = items
                self.need_based_items += items
        except Exception:
            pass

        return result

    # ---- Output refinement ----

    def run_refinement(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Review and improve reasoning quality."""
        self.refinement_cycles += 1

        result = {
            "activity": "refinement",
            "chains_reviewed": 0,
            "chains_improved": 0,
            "provenance_strengthened": 0,
        }

        # In the real system this reviews recent RAR results and
        # strengthens weak provenance chains
        try:
            rar_history = system_state.get("recent_rar_results", [])
            for rar in rar_history:
                result["chains_reviewed"] += 1
                confidence = rar.get("confidence", 1.0)
                if confidence < 0.7:
                    result["chains_improved"] += 1
                    self.reasoning_chains_improved += 1
        except Exception:
            pass

        return result

    # ---- Main cycle ----

    def run_scholarly_cycle(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one scholarly mode cycle. Returns a report of what
        was done and why."""
        if not self.active:
            return {"status": "inactive"}

        self.decay_interests()
        activity = self.select_activity(system_state)

        dispatch = {
            ScholarlyActivity.CONSOLIDATION: self.run_consolidation,
            ScholarlyActivity.REFLECTION: self.run_reflection,
            ScholarlyActivity.EXPLORATION: self.run_exploration,
            ScholarlyActivity.NEED_BASED: self.run_need_based,
            ScholarlyActivity.REFINEMENT: self.run_refinement,
        }

        handler = dispatch.get(activity, self.run_consolidation)
        result = handler(system_state)
        result["weights"] = self.weights.as_dict()
        return result

    # ---- Status ----

    def status(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "activated_at": self.activated_at,
            "weights": self.weights.as_dict(),
            "consolidation_cycles": self.consolidation_cycles,
            "synthesis_items_created": self.synthesis_items_created,
            "cross_links_strengthened": self.cross_links_strengthened,
            "reflection_cycles": self.reflection_cycles,
            "weak_areas_identified": self.weak_areas_identified,
            "improvement_goals_proposed": self.improvement_goals_proposed,
            "deep_dives_completed": self.deep_dives_completed,
            "deep_dive_items": self.deep_dive_items,
            "need_based_events": self.need_based_events,
            "need_based_items": self.need_based_items,
            "refinement_cycles": self.refinement_cycles,
            "reasoning_chains_improved": self.reasoning_chains_improved,
            "active_interests": len(self.interest_signals),
            "top_interests": [
                {"topic": s.topic, "strength": round(s.signal_strength, 3)}
                for s in self.get_top_interests(5)
            ],
        }


# ----------------------------------------------------------------
# SINGLETON
# ----------------------------------------------------------------

_manager = ScholarlyModeManager()


def get_scholarly_manager() -> ScholarlyModeManager:
    return _manager


def is_scholarly_active() -> bool:
    return _manager.is_active()


def activate_scholarly_mode() -> Dict[str, Any]:
    return _manager.activate()


def run_scholarly_cycle(system_state: Dict[str, Any]) -> Dict[str, Any]:
    return _manager.run_scholarly_cycle(system_state)


def record_interest(topic: str, source: str, strength: float = 0.1):
    _manager.record_interest(topic, source, strength)


def scholarly_status() -> Dict[str, Any]:
    return _manager.status()
