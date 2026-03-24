"""
Fuzzy Repair Layer for Natural Language Understanding (NLU)

Responsibilities:
- Typo correction (Levenshtein-like similarity)
- Verb repair (canonical verb families)
- Phrase repair (malformed naming patterns)
- Confidence scoring
- Ambiguity detection
- Repair notes for cockpit debugging
"""

import re
from difflib import SequenceMatcher

from nlu.keywords import (
    COMPLETE_VERBS, DELETE_VERBS, RENAME_VERBS,
    ADD_VERBS,                     # semantic-only add verbs
    SWITCH_VERBS, MOVE_VERBS, RESET_VERBS,
)

# Explicit goal‑creation verbs (replaces old CREATE_GOAL_VERBS)
CREATE_GOAL_VERBS = ["create", "start", "begin"]


# ------------------------------------------------------------
# Utility: Levenshtein-like similarity
# ------------------------------------------------------------

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def best_match(word: str, candidates: list[str], threshold: float = 0.75):
    best = None
    best_score = 0.0

    for c in candidates:
        score = similarity(word.lower(), c.lower())
        if score > best_score:
            best = c
            best_score = score

    if best_score >= threshold:
        return best, best_score

    return None, best_score


# ------------------------------------------------------------
# Verb repair (typos + malformed forms)
# ------------------------------------------------------------

ALL_VERBS = (
    COMPLETE_VERBS +
    DELETE_VERBS +
    RENAME_VERBS +
    ADD_VERBS +              # semantic-only add verbs
    CREATE_GOAL_VERBS +      # explicit goal-creation verbs
    SWITCH_VERBS +
    MOVE_VERBS +
    RESET_VERBS
)

def repair_verbs(text: str):
    """
    Repair verbs using fuzzy matching, but preserve semantic distinctions:
    - Never rewrite 'add' → 'create'
    - Never rewrite 'create' → 'add'
    """
    words = text.split()
    repaired_words = []
    confidence = 1.0
    notes = []

    for w in words:
        match, score = best_match(w, ALL_VERBS, threshold=0.72)

        # Semantic protection rules
        if w.lower() == "add" and match in CREATE_GOAL_VERBS:
            repaired_words.append("add")
            continue

        if w.lower() == "create" and match in ADD_VERBS:
            repaired_words.append("create")
            continue

        if match:
            repaired_words.append(match)
            if score < 1.0:
                notes.append(f"Verb '{w}' → '{match}' (score {score:.2f})")
            confidence = min(confidence, score)
        else:
            repaired_words.append(w)

    return " ".join(repaired_words), confidence, notes


# ------------------------------------------------------------
# Repair goal/step naming patterns
# ------------------------------------------------------------

NAME_PATTERNS = [
    r"call (?P<name>.+)$",
    r"call it (?P<name>.+)$",
    r"call this (?P<name>.+)$",
    r"call the goal (?P<name>.+)$",
    r"call the step (?P<name>.+)$",
]

def repair_name_patterns(text: str):
    for pattern in NAME_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group("name").strip()
            repaired = re.sub(pattern, f"called {name}", text, flags=re.IGNORECASE)
            return repaired, 0.85, [f"Name pattern normalized → 'called {name}'"]

    return text, 1.0, []


# ------------------------------------------------------------
# Main fuzzy repair pipeline
# ------------------------------------------------------------

def fuzzy_repair(text: str):
    notes = []

    # 1. Verb repair
    text, verb_conf, verb_notes = repair_verbs(text)
    notes.extend(verb_notes)

    # 2. Name pattern repair
    text, name_conf, name_notes = repair_name_patterns(text)
    notes.extend(name_notes)

    # Final confidence
    confidence = min(verb_conf, name_conf)

    return text, confidence, notes
