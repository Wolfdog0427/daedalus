"""
Resolver Adapter

Takes the output of the intent classifier and converts it into the
final command dict expected by:

    → context_resolver
    → execution engine
"""

import re
from typing import Dict, Any, Optional, Tuple
from .intent_classifier import classify_intent
from .argument_extractor import extract_arguments


def _extract_description(text: str, object_words: Tuple[str, ...]) -> Optional[str]:
    """Extract the free-text description after a verb + object word."""
    lower = text.lower().strip()
    for word in object_words:
        patterns = [
            rf"(?:add|create|start|begin|insert|make)\s+{word}\s+(.+)",
            rf"{word}\s+add\s+(.+)",
        ]
        for pat in patterns:
            m = re.match(pat, lower)
            if m:
                raw_desc = text[m.start(1):m.end(1)].strip()
                return raw_desc if raw_desc else None
    return None


# ------------------------------------------------------------
# MAIN ADAPTER
# ------------------------------------------------------------

def adapt_to_command(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert natural language into the structured command dict.

    Returns a dict with:
        {
            "intent": str,
            "args": dict,
            "raw": original_text,
            "repaired": fuzzy_repaired_text,
            "repair_confidence": float,
            "repair_notes": list[str]
        }
    """

    # Full NLU + semantic pipeline output
    nlu = classify_intent(text)

    # Core fields
    intent          = nlu.get("canonical_intent")
    if intent == "list_goals":
        intent = "show_goals"
    step_number     = nlu.get("step_number")
    goal_number     = nlu.get("goal_number")
    vague_step      = nlu.get("vague_step")
    vague_goal      = nlu.get("vague_goal")

    # Semantic fields
    verb_family     = nlu.get("verb_family")
    object_family   = nlu.get("object_family")
    modifiers       = nlu.get("modifiers", [])

    # Phase‑2 argument extraction
    args2           = extract_arguments(nlu)
    ordinal         = args2.get("ordinal")
    position        = args2.get("position")
    movement        = args2.get("movement")

    # Fuzzy repair metadata
    repaired        = nlu.get("repaired", text)
    repair_conf     = nlu.get("repair_confidence", 1.0)
    repair_notes    = nlu.get("repair_notes", [])

    # Base command structure
    base = {
        "intent": intent if intent is not None else "unknown",
        "args": {},
        "raw": text,
        "repaired": repaired,
        "repair_confidence": repair_conf,
        "repair_notes": repair_notes,

        # Pass semantic features downstream
        "semantic": {
            "verb_family": verb_family,
            "object_family": object_family,
            "modifiers": modifiers,
            "ordinal": ordinal,
            "position": position,
            "movement": movement,
        }
    }

    # --------------------------------------------------------
    # Unknown intent → return minimal command
    # --------------------------------------------------------
    if intent is None:
        base["args"] = {"raw": text}
        return base

    # --------------------------------------------------------
    # CREATE GOAL
    # --------------------------------------------------------
    if intent == "create_goal":
        name = _extract_description(text, ("goal", "project", "mission", "objective"))
        base["args"] = {"name": name} if name else {}
        return base

    # --------------------------------------------------------
    # MOVE STEP (Phase‑2 enhanced)
    # --------------------------------------------------------
    if intent == "move_step":
        args = {}

        # explicit step number
        if step_number is not None:
            args["step_number"] = step_number

        # ordinal reference ("first", "second", "third")
        elif ordinal is not None:
            args["ordinal"] = ordinal

        # vague reference ("move that", "move it")
        elif vague_step:
            args["step_number"] = None

        # movement ("up", "down")
        if movement is not None:
            args["movement"] = movement

        # absolute position ("top", "bottom")
        if position is not None:
            args["new_position"] = position

        base["args"] = args
        return base

    # --------------------------------------------------------
    # SWITCH GOAL (Phase‑2 enhanced)
    # --------------------------------------------------------
    if intent == "switch_goal":
        args = {}

        # explicit number
        if goal_number is not None:
            args["goal_id"] = goal_number

        # ordinal reference ("second goal", "third project")
        elif ordinal is not None:
            args["ordinal"] = ordinal

        # vague reference ("switch to that goal")
        elif vague_goal:
            args["goal_id"] = None

        base["args"] = args
        return base

    # --------------------------------------------------------
    # SHOW GOALS (list_goals normalized here)
    # --------------------------------------------------------
    if intent == "show_goals":
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # PLAN MODE (REPL parity)
    # --------------------------------------------------------
    if intent == "set_plan_mode":
        ll = text.strip().lower()
        rest = ""
        if ll.startswith("plan mode "):
            rest = ll[len("plan mode ") :].strip()
        elif ll.startswith("plan move "):
            rest = ll[len("plan move ") :].strip()
        if rest in ("pretty", "tree", "compact"):
            base["args"] = {"mode": rest}
        else:
            base["args"] = {}
        return base

    if intent == "show_plan_mode":
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # SYSTEM HEALTH / DOCTOR (introspection)
    # --------------------------------------------------------
    if intent in (
        "system_health",
        "health_report",
        "run_doctor",
        "diagnostics",
        "doctor",
    ):
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # GOVERNOR (introspection)
    # --------------------------------------------------------
    if intent in (
        "show_governor",
        "governor_status",
        "show_tier",
        "show_thresholds",
        "governor_report",
    ):
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # SHO CYCLE (introspection / cycle)
    # --------------------------------------------------------
    if intent in (
        "run_sho",
        "sho_cycle",
        "sho_status",
        "show_sho",
        "sho_report",
    ):
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # CHECKPOINTS / WATCHPOINTS
    # --------------------------------------------------------
    if intent == "save_checkpoint":
        ll = text.strip().lower()
        if ll.startswith("save checkpoint"):
            rest = ll[len("save checkpoint") :].strip()
            base["args"] = {"name": rest} if rest else {"name": "default"}
        else:
            base["args"] = {"name": "default"}
        return base

    if intent == "restore_checkpoint":
        ll = text.strip().lower()
        if ll.startswith("restore checkpoint"):
            rest = ll[len("restore checkpoint") :].strip()
            base["args"] = {"name": rest} if rest else {}
        else:
            base["args"] = {}
        return base

    if intent == "add_watchpoint":
        m = re.match(r"(?i)^(?:add watchpoint|watch)\s+(.+)$", text.strip())
        base["args"] = {"path": m.group(1).strip()} if m else {}
        return base

    if intent == "remove_watchpoint":
        m = re.match(r"(?i)^(?:remove watchpoint|unwatch)\s+(.+)$", text.strip())
        base["args"] = {"path": m.group(1).strip()} if m else {}
        return base

    # --------------------------------------------------------
    # SHOW PLAN / UNDO / REDO / NEXT STEP (no stray numbers)
    # --------------------------------------------------------
    if intent == "show_plan":
        base["args"] = {}
        return base

    if intent in ("undo", "redo", "next_step"):
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # DEBUG COCKPIT (no extra args)
    # --------------------------------------------------------
    if intent in (
        "debug_state",
        "debug_diff",
        "debug_context",
        "debug_timing",
        "debug_history",
        "debug_context_trace",
        "debug_watch_alerts",
        "debug_goals",
        "debug_steps",
        "debug_raw",
        "debug_last",
        "debug_semantic_contextual",
    ):
        base["args"] = {}
        return base

    if intent in ("list_checkpoints", "list_watchpoints"):
        base["args"] = {}
        return base

    # --------------------------------------------------------
    # HELP (topic optional; aligns with ExecutionEngine / firewall)
    # --------------------------------------------------------
    if intent == "help":
        tl = text.strip()
        ll = tl.lower()
        if ll.startswith("help ") and len(ll) > 5:
            base["args"] = {"topic": tl[len("help ") :].strip()}
        else:
            base["args"] = {}
        return base

    # --------------------------------------------------------
    # COMPLETE STEP (Phase‑2 enhanced)
    # --------------------------------------------------------
    if intent == "complete_step":
        args = {}

        if step_number is not None:
            args["step_number"] = step_number
        elif ordinal is not None:
            args["ordinal"] = ordinal
        elif vague_step:
            args["step_number"] = None

        base["args"] = args
        return base

    # --------------------------------------------------------
    # ADD STEP (modifier‑aware)
    # --------------------------------------------------------
    if intent == "add_step":
        args = {}

        if "another" in modifiers:
            args["mode"] = "another"

        desc = _extract_description(text, ("step", "task", "item", "todo"))
        if desc:
            args["description"] = desc

        base["args"] = args
        return base

    # --------------------------------------------------------
    # Explicit step number
    # --------------------------------------------------------
    if step_number is not None:
        base["args"] = {"step_number": step_number}
        return base

    # --------------------------------------------------------
    # Explicit goal number
    # --------------------------------------------------------
    if goal_number is not None:
        base["args"] = {"goal_id": goal_number}
        return base

    # --------------------------------------------------------
    # Vague step reference (no intent-specific block matched)
    # --------------------------------------------------------
    if vague_step:
        base["args"] = {"step_number": None}
        return base

    # --------------------------------------------------------
    # Vague goal reference (no intent-specific block matched)
    # --------------------------------------------------------
    if vague_goal:
        base["args"] = {"goal_id": None}
        return base

    # --------------------------------------------------------
    # No numbers, no vague references → simple intent
    # --------------------------------------------------------
    base["args"] = {}
    return base
