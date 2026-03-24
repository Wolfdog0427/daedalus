"""
NLU Matcher

First structured interpretation layer of the NLU pipeline.

Responsibilities:
- fuzzy repair (typo correction + phrase repair)
- tokenization
- verb detection
- object detection
- modifier detection
- vague reference detection
- canonical intent mapping

Pipeline:
    raw text
      → fuzzy_repair
      → tokenize
      → semantic feature detection
      → canonical intent mapping
"""

import re
from typing import Dict, Any, List, Optional

from .keywords import (
    STEP_WORDS,
    GOAL_WORDS,
    STEP_REFERENCE_PHRASES,
    GOAL_REFERENCE_PHRASES,
    MODIFIERS,
    INTENT_CLUSTERS,
    CANONICAL_ACTIONS,
)

from .fuzzy_repair import fuzzy_repair


# ------------------------------------------------------------
# TOKENIZATION
# ------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    """
    Simple tokenizer: lowercase, split on alphanumerics.
    """
    text = text.lower()
    return re.findall(r"[a-z0-9']+", text)


# ------------------------------------------------------------
# VERB DETECTION
# ------------------------------------------------------------

def detect_verb(tokens: List[str]) -> Optional[str]:
    """
    Find the first verb that appears in any verb family.
    """
    for t in tokens:
        for intent, verbs in INTENT_CLUSTERS.items():
            if t in verbs:
                return t
    return None


# ------------------------------------------------------------
# OBJECT DETECTION
# ------------------------------------------------------------

def detect_object(tokens: List[str]) -> Optional[str]:
    """
    Detect whether the user is referring to a step or a goal.
    """
    for t in tokens:
        if t in STEP_WORDS:
            return "step"
        if t in GOAL_WORDS:
            return "goal"
    return None


# ------------------------------------------------------------
# MODIFIER DETECTION
# ------------------------------------------------------------

def detect_modifier(tokens: List[str]) -> Optional[str]:
    """
    Detect relative modifiers like 'next', 'previous', etc.
    """
    for key, words in MODIFIERS.items():
        for w in words:
            if w in tokens:
                return key
    return None


# ------------------------------------------------------------
# VAGUE REFERENCE DETECTION
# ------------------------------------------------------------

def detect_vague_step_reference(text: str) -> bool:
    """
    Check if the text contains any vague step reference phrase.
    """
    t = text.lower()
    return any(phrase in t for phrase in STEP_REFERENCE_PHRASES)


def detect_vague_goal_reference(text: str) -> bool:
    """
    Check if the text contains any vague goal reference phrase.
    """
    t = text.lower()
    return any(phrase in t for phrase in GOAL_REFERENCE_PHRASES)


# ------------------------------------------------------------
# CANONICAL ACTION MAPPING
# ------------------------------------------------------------

def canonical_action(verb: Optional[str]) -> Optional[str]:
    """
    Map a detected verb to a canonical intent.
    """
    if verb is None:
        return None
    return CANONICAL_ACTIONS.get(verb)


# ------------------------------------------------------------
# MAIN MATCHER ENTRYPOINT
# ------------------------------------------------------------

def match_nlu(text: str) -> Dict[str, Any]:
    """
    First-pass NLU matcher.
    Produces a structured semantic interpretation of the text.
    """

    # --------------------------------------------------------
    # 1. Fuzzy repair (typos, malformed phrasing, verb fixes)
    # --------------------------------------------------------
    repaired_text, confidence, repair_notes = fuzzy_repair(text)

    # --------------------------------------------------------
    # 2. Tokenize repaired text
    # --------------------------------------------------------
    tokens = tokenize(repaired_text)

    # --------------------------------------------------------
    # 3. Detect semantic features
    # --------------------------------------------------------
    verb     = detect_verb(tokens)
    obj      = detect_object(tokens)
    modifier = detect_modifier(tokens)

    vague_step = detect_vague_step_reference(repaired_text)
    vague_goal = detect_vague_goal_reference(repaired_text)

    intent = canonical_action(verb)

    # --------------------------------------------------------
    # 4. Return structured interpretation
    # --------------------------------------------------------
    return {
        # Original + fuzzy repair metadata
        "raw": text,
        "repaired": repaired_text,
        "repair_confidence": confidence,
        "repair_notes": repair_notes,

        # Token-level features
        "tokens": tokens,
        "verb": verb,
        "object": obj,
        "modifier": modifier,

        # Vague references
        "vague_step": vague_step,
        "vague_goal": vague_goal,

        # Canonical intent
        "canonical_intent": intent,
    }
