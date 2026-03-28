# runtime/system_doctor.py

"""
System doctor

Deep structural validation + auto-repair for:
- goals_tree
- steps
- IDs
- history

Verbose: logs every repair.
"""

from typing import List, Dict, Any, Tuple

from runtime.state_store import StateStore
from runtime.execution.goal_manager import GoalManager
from runtime.health_dashboard import update_last_doctor_report


def _log(lines: List[str], msg: str) -> None:
    print(f"[doctor] {msg}")
    lines.append(msg)


def _ensure_goal_shape(goal: Dict[str, Any], lines: List[str]) -> None:
    if "id" not in goal:
        goal["id"] = (
            GoalManager.generate_goal_id()
            if hasattr(GoalManager, "generate_goal_id")
            else id(goal)
        )
        _log(lines, f"Added missing goal id: {goal['id']}")

    if "name" not in goal:
        goal["name"] = "(untitled goal)"
        _log(lines, f"Added missing goal name for id={goal['id']}")

    if "steps" not in goal or not isinstance(goal["steps"], list):
        goal["steps"] = []
        _log(lines, f"Fixed steps list for goal id={goal['id']}")


def _ensure_step_shape(step: Dict[str, Any], goal_id: Any, lines: List[str]) -> None:
    if "id" not in step:
        step["id"] = id(step)
        _log(lines, f"Added missing step id under goal={goal_id}")

    if "description" not in step:
        step["description"] = "(untitled step)"
        _log(lines, f"Added missing step description for step id={step['id']} under goal={goal_id}")

    if "done" not in step:
        step["done"] = False
        _log(lines, f"Added missing step done flag for step id={step['id']} under goal={goal_id}")


def run_system_doctor(auto: bool = True) -> List[str]:
    """
    Run deep validation + auto-repair.
    Returns a list of human-readable log lines.
    """
    lines: List[str] = []
    store = StateStore()
    state = store.state

    _log(lines, "Starting system doctor.")

    # Goals tree
    goals = state.get("goals_tree")
    if not isinstance(goals, list):
        state["goals_tree"] = []
        _log(lines, "goals_tree was not a list; reset to empty.")
        goals = state["goals_tree"]

    # Fix goals and steps
    for goal in goals:
        if not isinstance(goal, dict):
            _log(lines, "Non-dict goal encountered; skipping.")
            continue

        _ensure_goal_shape(goal, lines)

        for step in goal["steps"]:
            if not isinstance(step, dict):
                _log(lines, f"Non-dict step under goal={goal['id']}; skipping.")
                continue

            _ensure_step_shape(step, goal["id"], lines)

    # History sanity
    history = state.get("history")
    if not isinstance(history, list):
        state["history"] = []
        _log(lines, "history was not a list; reset to empty.")
        history = state["history"]

    new_history = []
    dropped = 0

    for entry in history:
        if isinstance(entry, dict) and "user" in entry and "command" in entry:
            new_history.append(entry)
        else:
            dropped += 1

    if dropped > 0:
        state["history"] = new_history
        _log(lines, f"Dropped {dropped} malformed history entries.")

    store.save(state)
    _log(lines, "System doctor completed and state saved.")

    update_last_doctor_report(lines)
    return lines
