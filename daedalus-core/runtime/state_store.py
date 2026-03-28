# runtime/state_store.py

import copy
from typing import Any, Dict, List

_MAX_ACTION_HISTORY = 500


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
            "last_step_id": None,
            "last_goal_id": None,
            "last_action": None,
            "last_step_referenced": None,
            "last_goal_referenced": None,
            "history": [],
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
        Persist the provided (or current internal) state.
        Copies domain keys shallowly; history is shared by reference
        to avoid quadratic deep-copy expansion.
        """
        if state is None:
            state = self._state

        snapshot: Dict[str, Any] = {}
        for k, v in state.items():
            if k == "history":
                snapshot[k] = list(v)
            elif k.startswith("_"):
                snapshot[k] = v
            else:
                snapshot[k] = copy.deepcopy(v)

        if "history" not in snapshot:
            snapshot["history"] = list(self._history)

        self._state = snapshot

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
        state=None,
        watch_changes=None,
    ) -> Dict[str, Any]:
        """
        Append an action record to the in-memory history.
        Returns the created entry so callers can sync it to the live state.
        """

        entry: Dict[str, Any] = {
            "input": user_input,
            "command": copy.deepcopy(command),
            "result": copy.deepcopy(result),
        }

        if context_trace is not None:
            entry["context_trace"] = copy.deepcopy(context_trace)

        if nlu_cmd is not None:
            entry["nlu_cmd"] = copy.deepcopy(nlu_cmd)

        if command_before is not None:
            entry["command_before"] = copy.deepcopy(command_before)

        if state is not None:
            entry["state"] = copy.deepcopy({
                k: v for k, v in state.items()
                if k not in ("history",) and not k.startswith("_")
            })

        if watch_changes is not None:
            entry["watch_changes"] = copy.deepcopy(watch_changes)

        self._history.append(entry)
        if len(self._history) > _MAX_ACTION_HISTORY:
            self._history = self._history[-_MAX_ACTION_HISTORY:]

        return entry

    # Optional legacy accessor
    def get_history(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._history)
