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
        try:
            from nlu.resolver_adapter import adapt_to_command

            cmd = adapt_to_command(user_input, self.state)
            result_text = self.execution.execute(cmd, self.state)
            text = result_text if isinstance(result_text, str) else str(result_text)
        except Exception as e:
            text = f"An error occurred while processing your input: {e}"

        try:
            self.history.append({"user": user_input, "assistant": text})
            self.storage.append_history(user_input, text)
            self.goals_tree = self.state.get("goals_tree", [])
            self.storage.save_goals_tree(self.goals_tree)
            self.storage.save_state(self.state)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "session state persistence failed: %s", exc,
            )

        return {"text": text}
