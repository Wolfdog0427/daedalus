# runtime/pretty.py

import json
from typing import Any, Dict, List

# We import the diff + context printers from debug_tools
from runtime.debug_tools import (
    debug_state_diff,
    debug_context,
)


# ------------------------------------------------------------
# HELP SYSTEM
# ------------------------------------------------------------

def pretty_help(topic: str | None = None) -> str:
    """
    Render help text.
    If topic is provided, show detailed help for that command.
    """
    if topic:
        return (
            f"📘 Help for '{topic}':\n"
            "(Detailed help not implemented yet — command recognized.)"
        )

    return (
        "📘 Available Commands\n"
        "\n"
        "General:\n"
        "  help                     Show this help message\n"
        "  help <topic>             Show help for a specific command\n"
        "\n"
        "Goals & Steps:\n"
        "  show plan                Display the current plan\n"
        "  show goals               Display all goals\n"
        "  add step <desc>          Add a step to the active goal\n"
        "  complete step <n>        Mark a step as complete\n"
        "  delete step <n>          Delete a step\n"
        "  rename step <n> to <x>   Rename a step\n"
        "\n"
        "State Management:\n"
        "  reset state              Clear all goals and steps\n"
        "  undo / redo              Undo or redo last action\n"
        "  save checkpoint <name>   Save a named checkpoint\n"
        "  restore checkpoint <name> Restore a checkpoint\n"
        "  list checkpoints         List all checkpoints\n"
        "\n"
        "Watchpoints:\n"
        "  watch <path>             Watch a field for changes\n"
        "  unwatch <path>           Remove a watchpoint\n"
        "  show watchpoints         List active watchpoints\n"
        "\n"
        "Debugging:\n"
        "  debug state              Show raw state\n"
        "  debug goals              Show raw goals\n"
        "  debug steps              Show raw steps\n"
        "  debug raw                Dump entire state\n"
        "  debug last               Show last command summary\n"
        "  debug diff               Show last state diff\n"
        "  debug context            Show context resolution\n"
        "  debug context trace      Show multi-step context trace\n"
        "  debug timing             Show NLU timing summary\n"
        "  debug history            Show full command history\n"
        "  debug watch alerts       Show triggered watchpoints\n"
        "  debug nlu <text>         Show full NLU pipeline output\n"
    )


# ------------------------------------------------------------
# DEBUG OUTPUT — STATE
# ------------------------------------------------------------

def pretty_debug_state(state: Dict[str, Any]) -> str:
    return "📦 STATE:\n" + json.dumps(state, indent=2, ensure_ascii=False)


def pretty_debug_goals(state: Dict[str, Any]) -> str:
    goals = state.get("goals_tree", [])
    return "🎯 GOALS:\n" + json.dumps(goals, indent=2, ensure_ascii=False)


def pretty_debug_steps(state: Dict[str, Any]) -> str:
    goals = state.get("goals_tree", [])
    active = state.get("active_goal_id")

    if active is None:
        return "⚠ No active goal."

    goal = next((g for g in goals if g["id"] == active), None)
    if not goal:
        return f"⚠ Active goal {active} not found."

    return "🪜 STEPS:\n" + json.dumps(goal.get("steps", []), indent=2, ensure_ascii=False)


def pretty_debug_raw(state: Dict[str, Any]) -> str:
    return "🧩 RAW STATE DUMP:\n" + json.dumps(state, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# ⭐ NEW: DEBUG OUTPUT — DIFF + CONTEXT (REQUIRED BY REPL)
# ------------------------------------------------------------

def pretty_debug_diff(state: Dict[str, Any]) -> str:
    """
    Wrapper around debug_state_diff from debug_tools.
    The REPL expects this function to exist.
    """
    before = state.get("_before_last", {})
    after = state
    return debug_state_diff(before, after)


def pretty_debug_context(state: Dict[str, Any]) -> str:
    """
    Wrapper around debug_context from debug_tools.
    The REPL expects this function to exist.
    """
    before = state.get("_before_last_cmd", {})
    after = state.get("_after_last_cmd", {})
    return debug_context(before, after)


# ------------------------------------------------------------
# DEBUG OUTPUT — FULL NLU PIPELINE
# ------------------------------------------------------------

def pretty_debug_nlu(nlu: Dict[str, Any]) -> str:
    """
    Pretty-print the full NLU pipeline output.
    """
    lines: List[str] = []
    lines.append("🔍 NLU PIPELINE DEBUG\n")

    def add(label: str, value: Any):
        if isinstance(value, (dict, list)):
            lines.append(f"{label}:\n{json.dumps(value, indent=2, ensure_ascii=False)}")
        else:
            lines.append(f"{label}: {value}")

    add("raw", nlu.get("raw"))
    add("repaired", nlu.get("repaired"))
    add("repair_confidence", nlu.get("repair_confidence"))
    add("repair_notes", nlu.get("repair_notes"))
    add("normalized_text", nlu.get("normalized_text"))
    add("tokens", nlu.get("tokens"))
    add("canonical_intent", nlu.get("canonical_intent"))
    add("object", nlu.get("object"))
    add("modifier", nlu.get("modifier"))
    add("vague_step", nlu.get("vague_step"))
    add("vague_goal", nlu.get("vague_goal"))
    add("step_number", nlu.get("step_number"))
    add("goal_number", nlu.get("goal_number"))

    return "\n".join(lines)


# ------------------------------------------------------------
# UNKNOWN COMMAND
# ------------------------------------------------------------

def pretty_unknown(text: str) -> str:
    return (
        "❓ I didn't understand that command.\n"
        f"Raw input: '{text}'\n"
        "Try 'help' to see available commands."
    )
