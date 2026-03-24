# runtime/reasoning_engine.py

from typing import Any, Dict, List

from .online_reasoner import OnlineReasoner
from .offline_reasoner import OfflineReasoner


class ReasoningEngine:
    """
    Unified reasoning interface.

    - Uses OnlineReasoner when available (remote LLM, full C3/M3/S3).
    - Falls back to OfflineReasoner when offline or on error.
    - Returns a list of structured actions for the ExecutionEngine.
    """

    def __init__(
        self,
        online_reasoner: OnlineReasoner | None = None,
        offline_reasoner: OfflineReasoner | None = None,
        online_enabled: bool = True,
    ) -> None:
        self.online_reasoner = online_reasoner or OnlineReasoner()
        self.offline_reasoner = offline_reasoner or OfflineReasoner()
        self.online_enabled = online_enabled

    def interpret(
        self,
        user_input: str,
        history: List[Dict[str, Any]] | None,
        state: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:
        """
        Main entry point.

        Returns a list of actions, each like:
        {
            "type": "set_goal" | "complete_step" | "add_note" | ...,
            "payload": {...}
        }
        """
        history = history or []
        state = state or {}

        if self._can_use_online():
            try:
                actions = self.online_reasoner.interpret(user_input, history, state)
                if self._valid_actions(actions):
                    return actions
            except Exception:
                # Silent fallback to offline for robustness.
                pass

        return self.offline_reasoner.interpret(user_input, history, state)

    def _can_use_online(self) -> bool:
        # Later: connectivity checks, feature flags, etc.
        return self.online_enabled

    def _valid_actions(self, actions: Any) -> bool:
        if not isinstance(actions, list):
            return False
        for item in actions:
            if not isinstance(item, dict):
                return False
            if "type" not in item or "payload" not in item:
                return False
        return True
