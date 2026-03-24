"""
Subtask execution engine.

Tracks:
- which step/substep is active
- marking completion
- advancing to next step
"""

from typing import Dict, Any, Optional


class SubtaskEngine:
    def __init__(self):
        pass

    def _ensure_progress_fields(self, goal: Dict[str, Any]):
        if "current_index" not in goal:
            goal["current_index"] = 0
        if "current_subindex" not in goal:
            goal["current_subindex"] = None

    def mark_step_complete(
        self,
        goals: Dict[str, Any],
        goal_index: int = 0,
        step_index: Optional[int] = None,
        substep_index: Optional[int] = None,
    ) -> str:
        queue = goals.get("queue", [])
        if not queue or goal_index >= len(queue):
            return "No such goal to update."

        goal = queue[goal_index]
        self._ensure_progress_fields(goal)

        steps = goal.get("steps", [])
        if not steps:
            return "This goal has no steps to complete."

        if step_index is None:
            step_index = goal.get("current_index", 0)

        if step_index >= len(steps):
            return "No such step to complete."

        step = steps[step_index]

        # Mark substep complete if specified
        if substep_index is not None:
            subs = step.get("substeps", [])
            if substep_index >= len(subs):
                return "No such substep to complete."
            # We don't track per-substep completion yet; placeholder
            return f"Marked substep {substep_index + 1} of step {step_index + 1} as complete."

        # Mark step complete (increment completed_steps)
        goal["completed_steps"] = goal.get("completed_steps", 0) + 1
        return f"Marked step {step_index + 1} as complete."

    def advance_to_next(
        self,
        goals: Dict[str, Any],
        goal_index: int = 0,
    ) -> str:
        queue = goals.get("queue", [])
        if not queue or goal_index >= len(queue):
            return "No such goal to advance."

        goal = queue[goal_index]
        self._ensure_progress_fields(goal)

        steps = goal.get("steps", [])
        if not steps:
            return "This goal has no steps."

        current = goal.get("current_index", 0)
        if current + 1 >= len(steps):
            return "You have reached the end of the steps for this goal."

        goal["current_index"] = current + 1
        label = steps[goal["current_index"]].get("step", f"Step {goal['current_index'] + 1}")
        return f"Moved to next step: {label}"

    def describe_current_step(
        self,
        goals: Dict[str, Any],
        goal_index: int = 0,
    ) -> str:
        queue = goals.get("queue", [])
        if not queue or goal_index >= len(queue):
            return "No such goal."

        goal = queue[goal_index]
        self._ensure_progress_fields(goal)

        steps = goal.get("steps", [])
        if not steps:
            return "This goal has no steps."

        idx = goal.get("current_index", 0)
        if idx >= len(steps):
            return "You have completed all steps for this goal."

        step = steps[idx]
        label = step.get("step", f"Step {idx + 1}")
        subs = step.get("substeps", [])
        if subs:
            subtext = ", ".join(subs)
            return f"Current step: {label}. Substeps: {subtext}."
        return f"Current step: {label}."
