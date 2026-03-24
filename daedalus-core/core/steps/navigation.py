def get_current_step_index(goals):
    return goals.get("current_step_index", 1)


def get_next_step_index(goals, current_index):
    steps = goals.get("active_steps", [])
    if current_index >= len(steps):
        return None
    return current_index + 1
