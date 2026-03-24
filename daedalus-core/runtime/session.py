from typing import Dict, Any, List
from runtime.execution.execution import ExecutionEngine
from runtime.storage import Storage


class Session:
    """
    Session manager with SQLite persistence.
    """

    def __init__(self, execution: ExecutionEngine, storage: Storage):
        self.execution = execution
        self.storage = storage

        # Load persisted data
        self.state: Dict[str, Any] = storage.load_state()
        self.history: List[Dict[str, Any]] = storage.load_history()
        self.goals_tree: List[Dict[str, Any]] = storage.load_goals_tree()

        # Public view of current goal
        self.goals: Dict[str, Any] = {}

        # Ensure state has goals_tree
        if "goals_tree" not in self.state:
            self.state["goals_tree"] = self.goals_tree

    def handle_input(self, user_input: str) -> Dict[str, Any]:
        result = self.execution.handle(
            user_input=user_input,
            history=self.history,
            state=self.state,
            goals=self.goals,
        )

        text = result.get("text", "")

        # Update history
        self.history.append(
            {
                "user": user_input,
                "assistant": text,
            }
        )
        self.storage.append_history(user_input, text)

        # Update goals tree if changed
        if "goal_update" in result:
            # ExecutionEngine already updated state["goals_tree"]
            self.goals_tree = self.state.get("goals_tree", [])
            self.storage.save_goals_tree(self.goals_tree)

        # Update public goal view
        if "goals" in result and result["goals"] is not None:
            self.goals = result["goals"]

        # Persist state
        self.storage.save_state(self.state)

        return result
