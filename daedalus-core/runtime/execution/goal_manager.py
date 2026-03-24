from typing import Any, Dict, List, Optional


class GoalManager:
    """
    Deterministic, ID‑based Goal Manager with a clean public API.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------
    def _ensure_state(self, state: Dict[str, Any]) -> None:
        state.setdefault("goals_tree", [])
        state.setdefault("active_goal_id", None)
        state.setdefault("next_goal_id", 1)
        state.setdefault("next_step_id", 1)

    def _find_goal(self, goal_id: int, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for g in state.get("goals_tree", []):
            if g.get("id") == goal_id:
                return g
        return None

    def _get_active_goal_internal(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gid = state.get("active_goal_id")
        if gid is None:
            return None
        return self._find_goal(gid, state)

    def _renumber_steps(self, goal: Dict[str, Any]) -> None:
        for i, step in enumerate(goal.get("steps", []), start=1):
            step["number"] = i

    # ------------------------------------------------------------
    # GOALS
    # ------------------------------------------------------------
    def create_goal(self, title: str, state: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_state(state)

        gid = state["next_goal_id"]
        state["next_goal_id"] += 1

        goal = {
            "id": gid,
            "name": title,
            "steps": [],
        }

        state["goals_tree"].append(goal)
        state["active_goal_id"] = gid

        return goal

    def set_goal(self, title: str, state: Dict[str, Any]) -> int:
        return self.create_goal(title, state)["id"]

    def switch_goal(self, goal_id: int, state: Dict[str, Any]) -> bool:
        self._ensure_state(state)
        if self._find_goal(goal_id, state) is None:
            return False
        state["active_goal_id"] = goal_id
        return True

    def get_goal(self, goal_id: int, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_goal(goal_id, state)

    def get_active_goal(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._ensure_state(state)
        return self._get_active_goal_internal(state)

    def list_goals(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._ensure_state(state)
        return state.get("goals_tree", [])

    # ------------------------------------------------------------
    # STEPS
    # ------------------------------------------------------------
    def add_step(self, title: str, state: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_state(state)
        goal = self._get_active_goal_internal(state)
        if goal is None:
            return {}

        sid = state["next_step_id"]
        state["next_step_id"] += 1

        step = {
            "id": sid,
            "goal_id": goal["id"],
            "number": 0,
            "description": title,
            "done": False,
        }

        goal["steps"].append(step)
        self._renumber_steps(goal)
        return step

    def get_step(self, step_id: int, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        goal = self._get_active_goal_internal(state)
        if goal is None:
            return None
        for step in goal.get("steps", []):
            if step["id"] == step_id:
                return step
        return None

    def get_active_steps(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._ensure_state(state)
        goal = self._get_active_goal_internal(state)
        return goal.get("steps", []) if goal else []

    def complete_step(self, step_id: int, state: Dict[str, Any]) -> bool:
        step = self.get_step(step_id, state)
        if step is None:
            return False
        step["done"] = True
        return True

    def complete_step_by_id(self, step_id: int, state: Dict[str, Any]) -> bool:
        return self.complete_step(step_id, state)

    def delete_step(self, step_id: int, state: Dict[str, Any]) -> bool:
        goal = self._get_active_goal_internal(state)
        if goal is None:
            return False

        steps = goal.get("steps", [])
        new_steps = [s for s in steps if s["id"] != step_id]

        if len(new_steps) == len(steps):
            return False

        goal["steps"] = new_steps
        self._renumber_steps(goal)
        return True

    def delete_step_by_id(self, step_id: int, state: Dict[str, Any]) -> bool:
        return self.delete_step(step_id, state)

    def rename_step(self, step_id: int, new_title: str, state: Dict[str, Any]) -> bool:
        step = self.get_step(step_id, state)
        if step is None:
            return False
        step["description"] = new_title
        return True

    def rename_step_by_id(self, step_id: int, new_title: str, state: Dict[str, Any]) -> bool:
        return self.rename_step(step_id, new_title, state)

    def move_step(self, step_id: int, new_position: int, state: Dict[str, Any]) -> bool:
        goal = self._get_active_goal_internal(state)
        if goal is None:
            return False

        steps = goal.get("steps", [])
        if not steps:
            return False

        # Find current index
        current_index = None
        for i, s in enumerate(steps):
            if s["id"] == step_id:
                current_index = i
                break

        if current_index is None:
            return False

        # Clamp new_position
        new_index = max(0, min(len(steps) - 1, new_position - 1))

        step = steps.pop(current_index)
        steps.insert(new_index, step)

        self._renumber_steps(goal)
        return True

    def move_step_by_id(self, step_id: int, new_position: int, state: Dict[str, Any]) -> bool:
        return self.move_step(step_id, new_position, state)
