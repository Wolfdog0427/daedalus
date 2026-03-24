# nlu/semantic_detector.py

from typing import Dict, Any

from nlu.keywords import (
    INTENT_CLUSTERS,
    STEP_WORDS,
    GOAL_WORDS,
    STEP_REFERENCE_PHRASES,
    GOAL_REFERENCE_PHRASES,
    MODIFIERS,
    ADD_VERBS,
)


class SemanticDetector:
    """
    Modern semantic detector matching the new keyword architecture.
    """

    def detect(self, norm: Dict[str, Any]) -> Dict[str, Any]:
        tokens = norm.get("tokens", [])

        verb_family = None
        object_family = None
        modifiers = []
        vague_step = norm.get("vague_step", False)
        vague_goal = norm.get("vague_goal", False)

        # ------------------------------------------------------------
        # 1. Verb family detection
        # ------------------------------------------------------------

        # SPECIAL CASE: "add" is ambiguous → treat as neutral
        if any(t in tokens for t in ADD_VERBS):
            verb_family = "add"

        else:
            # All other verbs use intent clusters
            for family, verbs in INTENT_CLUSTERS.items():
                if any(t in tokens for t in verbs):
                    verb_family = family
                    break

        # ------------------------------------------------------------
        # 2. Object detection (step / goal)
        # ------------------------------------------------------------
        if any(t in tokens for t in STEP_WORDS):
            object_family = "step"
        elif any(t in tokens for t in GOAL_WORDS):
            object_family = "goal"

        # ------------------------------------------------------------
        # 3. Modifier detection
        # ------------------------------------------------------------
        for name, words in MODIFIERS.items():
            if any(t in tokens for t in words):
                modifiers.append(name)

        # ------------------------------------------------------------
        # 4. Vague reference detection
        # ------------------------------------------------------------
        raw_lower = norm["raw"].lower()

        if any(phrase in raw_lower for phrase in STEP_REFERENCE_PHRASES):
            vague_step = True
        if any(phrase in raw_lower for phrase in GOAL_REFERENCE_PHRASES):
            vague_goal = True

        # ------------------------------------------------------------
        # 5. Return enriched semantic structure
        # ------------------------------------------------------------
        return {
            **norm,
            "verb_family": verb_family,
            "object_family": object_family,
            "modifiers": modifiers,
            "vague_step": vague_step,
            "vague_goal": vague_goal,
        }
