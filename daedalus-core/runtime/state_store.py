# runtime/state_store.py

import copy
from typing import Any, Dict, List


class StateStore:
    """
    Deterministic in-memory state store with the API expected by:
      - REPL
      - CLI
      - crash_recovery
      - ExecutionEngine
      - tests

    Features:
      - .state property (deep copy on load)
      - .history property (deep copy)
      - save() with or without args
      - record_action() for REPL history (now upgraded)
      - internal canonical state
    """

    def __init__(self):
        self._state = self._default_state()
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Default state
    # ------------------------------------------------------------
    def _default_state(self) -> Dict[str, Any]:
        return {
            "goals_tree": [],
            "active_goal_id": None,
            "next_goal_id": 1,
            "next_step_id": 1,
            "history": [],  # REQUIRED for doctor + REPL compatibility
        }

    # ------------------------------------------------------------
    # Public API expected by REPL + CLI
    # ------------------------------------------------------------
    @property
    def state(self) -> Dict[str, Any]:
        """Return a deep copy of the current state."""
        return copy.deepcopy(self._state)

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return a deep copy of the action history (REPL + watch_monitor expect this)."""
        return copy.deepcopy(self._history)

    def save(self, state: Dict[str, Any] = None) -> None:
        """
        Save a deep copy of the provided state.
        If no state is provided, save the current internal state.
        """
        if state is None:
            state = self._state

        state = copy.deepcopy(state)
        if "history" not in state:
            state["history"] = copy.deepcopy(self._history)

        self._state = state

    def load(self) -> Dict[str, Any]:
        """Return a deep copy of the stored state."""
        return copy.deepcopy(self._state)

    # ------------------------------------------------------------
    # Upgraded record_action() — fully compatible with REPL
    # ------------------------------------------------------------
    def record_action(
        self,
        user_input: str,
        command: Dict[str, Any],
        result: Any,
        context_trace=None,
        nlu_cmd=None,
        command_before=None,
    ) -> None:
        """
        Append an action record to the in-memory history.
        Fully compatible with the REPL's debug cockpit.
        """

        entry = {
            "input": user_input,
            "command": copy.deepcopy(command),
            "result": copy.deepcopy(result),
        }

        # Optional debug metadata
        if context_trace is not None:
            entry["context_trace"] = copy.deepcopy(context_trace)

        if nlu_cmd is not None:
            entry["nlu_cmd"] = copy.deepcopy(nlu_cmd)

        if command_before is not None:
            entry["command_before"] = copy.deepcopy(command_before)

        self._history.append(entry)

    # Optional legacy accessor
    def get_history(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._history)
