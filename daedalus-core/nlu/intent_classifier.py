"""
Intent Classifier (Hybrid Model with Semantic Override)

This version aligns with the actual intents supported by the REPL,
ExecutionEngine, and resolver adapter.

Canonical intents supported by the system:

    create_goal
    add_step
    complete_step
    switch_goal
    delete_step
    delete_goal
    list_goals / show_goals
    show_plan
    next_step
    undo
    redo

    REPL meta / introspection (see _match_repl_meta_intent; must match SAFE_INTENTS):
    help, system_health, run_doctor, plan mode, governor / SHO introspection, debug_*, checkpoints, watchpoints, etc.
"""

import re
import difflib
from typing import Dict, Any, Optional

from .matcher import match_nlu
from .normalizer import normalize_nlu

# Semantic modules
from .semantic_normalizer import SemanticNormalizer
from .semantic_detector import SemanticDetector

_sem_norm = SemanticNormalizer()
_sem_det  = SemanticDetector()

# ------------------------------------------------------------
# Fuzzy verb/object family support
# ------------------------------------------------------------

KNOWN_VERB_FAMILIES = {
    "add",
    "create",
    "insert",
    "make",
    "finish",
    "complete",
    "switch",
    "delete",
    "show",
    "list",
    "display",
    "next",
    "continue",
}

KNOWN_OBJECT_FAMILIES = {
    "goal",
    "step",
    "plan",
}


def _fuzzy_family(value: Optional[str], known: set) -> tuple:
    """
    Returns (repaired_value, original_value_if_repaired_else_None)
    so the cockpit can see semantic repairs explicitly.
    """
    if not value:
        return value, None
    matches = difflib.get_close_matches(value, list(known), n=1, cutoff=0.85)
    if not matches:
        return value, None
    repaired = matches[0]
    if repaired == value:
        return value, None
    return repaired, value


# ------------------------------------------------------------
# STEP NUMBER EXTRACTION
# ------------------------------------------------------------

def extract_step_number(text: str) -> Optional[int]:
    matches = re.findall(r"\b(\d+)\b", text)
    if not matches:
        return None
    return int(matches[0])


# ------------------------------------------------------------
# GOAL NUMBER EXTRACTION
# ------------------------------------------------------------

def extract_goal_number(text: str) -> Optional[int]:
    t = text.lower()

    m = re.search(r"goal\s+(\d+)", t)
    if m:
        return int(m.group(1))

    m = re.search(r"project\s+(\d+)", t)
    if m:
        return int(m.group(1))

    generic = re.findall(r"\b(\d+)\b", t)
    if generic:
        return int(generic[0])

    return None


# ------------------------------------------------------------
# REPL meta-command phrases (bootstrap; aligns with SAFE_INTENTS)
# ------------------------------------------------------------

def _match_repl_meta_intent(nt: str) -> Optional[str]:
    """
    Map benign REPL / introspection phrases to canonical intents.

    Runs before semantic fallback so matcher mistakes (e.g. 'show goals' → show_plan)
    are overridden. Does not replace full NLU; only explicit phrase coverage.
    """
    if not nt:
        return None

    if nt == "help" or nt.startswith("help "):
        return "help"

    if nt in (
        "show goals",
        "list goals",
        "what are my goals",
        "show my goals",
        "goals list",
    ):
        return "show_goals"

    if nt in (
        "show plan",
        "show steps",
        "plan show",
        "what's left",
        "whats left",
        "what do i have left",
    ):
        return "show_plan"

    if nt.startswith("plan mode "):
        return "set_plan_mode"
    if nt.startswith("plan move ") and len(nt) > len("plan move "):
        return "set_plan_mode"
    if nt in (
        "plan mode",
        "plan move",
        "show plan mode",
        "what is plan mode",
        "current plan mode",
    ):
        return "show_plan_mode"

    if nt in ("system health", "show health", "health status"):
        return "system_health"
    if nt in ("health report", "health_report"):
        return "health_report"
    if nt in ("run doctor", "system doctor", "run diagnostics"):
        return "run_doctor"
    if nt == "diagnostics":
        return "diagnostics"
    if nt == "doctor":
        return "doctor"

    if nt in ("show governor", "show_governor"):
        return "show_governor"
    if nt in ("governor status", "governor_status"):
        return "governor_status"
    if nt in ("show tier", "current tier"):
        return "show_tier"
    if nt in ("show thresholds", "show_thresholds", "thresholds"):
        return "show_thresholds"
    if nt in ("governor report", "governor_report"):
        return "governor_report"

    if nt in ("run sho", "run_sho"):
        return "run_sho"
    if nt in ("sho cycle", "sho_cycle"):
        return "sho_cycle"
    if nt in ("sho status", "sho_status"):
        return "sho_status"
    if nt in ("show sho", "show_sho"):
        return "show_sho"
    if nt in ("sho report", "sho_report"):
        return "sho_report"

    if nt == "undo":
        return "undo"
    if nt == "redo":
        return "redo"

    if nt == "next step":
        return "next_step"

    _debug_exact = {
        "debug timing": "debug_timing",
        "debug goals": "debug_goals",
        "debug steps": "debug_steps",
        "debug raw": "debug_raw",
        "debug last": "debug_last",
        "debug context trace": "debug_context_trace",
        "debug watch alerts": "debug_watch_alerts",
        "debug semantic contextual": "debug_semantic_contextual",
        "debug state": "debug_state",
        "debug diff": "debug_diff",
        "debug context": "debug_context",
        "debug history": "debug_history",
    }
    if nt in _debug_exact:
        return _debug_exact[nt]

    if nt == "list checkpoints":
        return "list_checkpoints"
    if nt == "list watchpoints":
        return "list_watchpoints"
    if nt.startswith("save checkpoint"):
        return "save_checkpoint"
    if nt.startswith("restore checkpoint"):
        return "restore_checkpoint"

    if re.match(r"^(?:add watchpoint|watch)\s+\S", nt):
        return "add_watchpoint"
    if re.match(r"^(?:remove watchpoint|unwatch)\s+\S", nt):
        return "remove_watchpoint"

    if nt == "debug semantic":
        return "debug_semantic_contextual"

    return None


# ------------------------------------------------------------
# MAIN INTENT CLASSIFIER
# ------------------------------------------------------------

def classify_intent(text: str) -> Dict[str, Any]:
    """
    Hybrid classifier:
      - matcher + normalizer
      - semantic fallback
      - semantic override
      - canonical intents aligned with system
    """

    # 1. Matcher
    nlu = match_nlu(text)

    # 2. Normalizer
    norm = normalize_nlu(nlu)

    canonical_intent = norm.get("canonical_intent")
    normalized_text  = norm.get("normalized_text", "")

    # 3. Semantic front-end
    _ = _sem_norm.normalize(normalized_text)
    sem_det = _sem_det.detect(norm)

    verb_family_raw   = sem_det.get("verb_family")
    object_family_raw = sem_det.get("object_family")
    modifiers         = sem_det.get("modifiers", [])

    # 3b. Fuzzy repair for verb/object families (with metadata)
    verb_family, verb_repaired_from = _fuzzy_family(verb_family_raw, KNOWN_VERB_FAMILIES)
    object_family, obj_repaired_from = _fuzzy_family(object_family_raw, KNOWN_OBJECT_FAMILIES)

    semantic_repairs: Dict[str, Any] = {}
    if verb_repaired_from is not None:
        semantic_repairs["verb_family"] = {
            "before": verb_repaired_from,
            "after": verb_family,
            "reason": "fuzzy_match",
        }
    if obj_repaired_from is not None:
        semantic_repairs["object_family"] = {
            "before": obj_repaired_from,
            "after": object_family,
            "reason": "fuzzy_match",
        }

    # 4. Extract numbers
    step_number = extract_step_number(normalized_text)
    goal_number = extract_goal_number(normalized_text)

    # 4b. REPL meta-commands (override matcher / fill gaps before §5)
    # Try normalized text first, then raw text — normalizer may rewrite
    # e.g. "plan mode" → "plan move", which would otherwise miss meta phrases.
    nt_meta = normalized_text.strip().lower()
    meta_intent = _match_repl_meta_intent(nt_meta)
    if meta_intent is None:
        meta_intent = _match_repl_meta_intent(text.strip().lower())
    if meta_intent is not None:
        canonical_intent = meta_intent

    # --------------------------------------------------------
    # 5. Semantic fallback when canonical intent is missing
    #    OR explicitly "unknown"
    # --------------------------------------------------------

    if canonical_intent is None or canonical_intent == "unknown":

        # GOALS
        if verb_family == "add" and object_family == "goal":
            canonical_intent = "create_goal"

        # STEPS (all synonyms → add_step)
        elif verb_family in ("add", "create", "insert", "make") and object_family == "step":
            canonical_intent = "add_step"

        # COMPLETE STEP
        elif verb_family in ("finish", "complete") and object_family == "step":
            canonical_intent = "complete_step"

        # SWITCH GOAL
        elif verb_family == "switch" and object_family == "goal":
            canonical_intent = "switch_goal"

        # DELETE
        elif verb_family == "delete":
            if object_family == "goal":
                canonical_intent = "delete_goal"
            elif object_family == "step":
                canonical_intent = "delete_step"

        # LIST GOALS
        elif verb_family in ("show", "list", "display") and object_family == "goal":
            canonical_intent = "list_goals"

        # SHOW PLAN
        elif verb_family in ("show", "display") and object_family == "plan":
            canonical_intent = "show_plan"

        # NEXT STEP
        elif verb_family in ("next", "continue") and object_family == "step":
            canonical_intent = "next_step"

        # UNDO / REDO
        elif normalized_text.strip() == "undo":
            canonical_intent = "undo"
        elif normalized_text.strip() == "redo":
            canonical_intent = "redo"

    # --------------------------------------------------------
    # 6. Semantic override (canonical contradicts semantics)
    # --------------------------------------------------------

    else:
        if canonical_intent == "add_step" and object_family == "goal":
            canonical_intent = "create_goal"

        if canonical_intent == "create_goal" and object_family == "step":
            canonical_intent = "add_step"

        if canonical_intent == "complete_step" and object_family == "goal":
            canonical_intent = "complete_goal"

        if canonical_intent == "delete_step" and object_family == "goal":
            canonical_intent = "delete_goal"

    # --------------------------------------------------------
    # 7. Return structured interpretation
    # --------------------------------------------------------

    return {
        "raw": text,
        "repaired": norm.get("repaired", text),
        "repair_confidence": norm.get("repair_confidence", 1.0),
        "repair_notes": norm.get("repair_notes", []),

        "normalized_text": normalized_text,

        "tokens": norm.get("tokens", []),
        "canonical_intent": canonical_intent,
        "step_number": step_number,
        "goal_number": goal_number,
        "vague_step": norm.get("vague_step", False),
        "vague_goal": norm.get("vague_goal", False),
        "object": norm.get("object"),
        "modifier": norm.get("modifier"),

        "verb_family": verb_family,
        "object_family": object_family,
        "modifiers": modifiers,

        "semantic_repairs": semantic_repairs,
    }
