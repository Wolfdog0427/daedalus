"""
NLU Normalizer

Takes the output from matcher.match_nlu() and rewrites the user’s
language into a canonical, engine-friendly structure.

Responsibilities:
- normalize multi-word verbs ("wrap up" → "finish")
- collapse synonyms into canonical verbs
- incorporate fuzzy-repaired text
- detect vague references
- map detected verbs → canonical intent
- produce a clean semantic structure for downstream components

Pipeline:
    matcher → normalizer → resolver_adapter → context_resolver → engine
"""

from typing import Dict, Any, Optional

from .keywords import (
    STEP_REFERENCE_PHRASES,
    GOAL_REFERENCE_PHRASES,
    CANONICAL_ACTIONS,
)


# ------------------------------------------------------------
# MULTI-WORD VERB NORMALIZATION
# ------------------------------------------------------------

MULTIWORD_VERBS = {
    "wrap up": "finish",
    "close out": "finish",
    "mark done": "finish",
    "get rid of": "delete",
    "change name": "rename",
    "edit name": "rename",
    "update title": "rename",
    "modify title": "rename",
    "go to": "switch",
    "jump to": "switch",
    "focus on": "switch",
    "move to": "switch",
    "wipe out": "reset",
    "clear out": "reset",

    # fuzzy-repair compatibility
    "call ": "called ",
}


def normalize_multiword_verbs(text: str) -> str:
    """
    Replace multi-word verb phrases with canonical equivalents.
    """
    lowered = text.lower()
    for phrase, replacement in MULTIWORD_VERBS.items():
        if phrase in lowered:
            lowered = lowered.replace(phrase, replacement)
    return lowered


# ------------------------------------------------------------
# CANONICAL VERB NORMALIZATION
# ------------------------------------------------------------

def canonicalize_verb(verb: Optional[str]) -> Optional[str]:
    """
    Convert a detected verb into its canonical form.
    """
    if verb is None:
        return None
    return CANONICAL_ACTIONS.get(verb)


# ------------------------------------------------------------
# VAGUE REFERENCE NORMALIZATION
# ------------------------------------------------------------

def normalize_vague_references(text: str) -> Dict[str, bool]:
    """
    Identify vague references to steps or goals.
    """
    t = text.lower()

    vague_step = any(p in t for p in STEP_REFERENCE_PHRASES)
    vague_goal = any(p in t for p in GOAL_REFERENCE_PHRASES)

    return {
        "vague_step": vague_step,
        "vague_goal": vague_goal,
    }


# ------------------------------------------------------------
# MAIN NORMALIZER ENTRYPOINT
# ------------------------------------------------------------

def normalize_nlu(nlu: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take the raw NLU match output and produce a canonical semantic structure.
    """

    raw            = nlu["raw"]
    repaired       = nlu["repaired"]
    repair_conf    = nlu["repair_confidence"]
    repair_notes   = nlu["repair_notes"]

    tokens         = nlu["tokens"]
    verb           = nlu["verb"]
    obj            = nlu["object"]
    modifier       = nlu["modifier"]

    # Normalize multi-word verbs on the repaired text
    normalized_text = normalize_multiword_verbs(repaired)

    # Canonical verb → canonical intent
    canonical_intent = canonicalize_verb(verb)

    # Vague references
    vague_refs = normalize_vague_references(normalized_text)

    # Final normalized structure
    return {
        # Original + fuzzy repair metadata
        "raw": raw,
        "repaired": repaired,
        "repair_confidence": repair_conf,
        "repair_notes": repair_notes,

        # Normalized text
        "normalized_text": normalized_text,

        # Semantic features
        "tokens": tokens,
        "verb": verb,
        "canonical_intent": canonical_intent,
        "object": obj,
        "modifier": modifier,

        # Vague reference flags
        "vague_step": vague_refs["vague_step"],
        "vague_goal": vague_refs["vague_goal"],
    }
