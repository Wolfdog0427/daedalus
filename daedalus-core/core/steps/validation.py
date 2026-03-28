def step_exists(goals, step_num):
    steps = goals.get("active_steps", [])
    return 1 <= step_num <= len(steps)


def is_step_completed(goals, step_num):
    steps = goals.get("active_steps", [])
    if not (1 <= step_num <= len(steps)):
        return False
    step = steps[step_num - 1]
    return step.get("completed", False)


def mark_goal_completed(goals):
    goals["completed"] = True
    goals["current_step_index"] = None
    return goals


def all_steps_completed(goals):
    steps = goals.get("active_steps", [])
    return all(s.get("completed") for s in steps)
