from .validation import (
    step_exists,
    is_step_completed,
    all_steps_completed,
    mark_goal_completed,
)
from .navigation import get_current_step_index, get_next_step_index


def complete_step(goals, step_num=None):
    """
    Core step completion logic:
    - If step_num is None → complete current step
    - Marks step as completed
    - Auto-advances to next step
    - Detects goal completion
    """

    steps = goals.get("active_steps", [])
    if not steps:
        return goals, "There is no active goal."

    # Determine target step
    if step_num is None:
        step_num = get_current_step_index(goals)

    if not step_exists(goals, step_num):
        return goals, f"Step {step_num} does not exist."

    if is_step_completed(goals, step_num):
        return goals, f"Step {step_num} is already complete."

    # Mark step complete
    steps[step_num - 1]["completed"] = True
    goals["last_step_completed"] = step_num

    # Check if goal is now complete
    if all_steps_completed(goals):
        goals = mark_goal_completed(goals)
        return goals, "All steps complete. Goal finished."

    # Auto-advance
    next_index = get_next_step_index(goals, step_num)
    goals["current_step_index"] = next_index

    next_step_text = steps[next_index - 1]["text"]
    return goals, f"Step {step_num} complete. Next step: {next_step_text}"
