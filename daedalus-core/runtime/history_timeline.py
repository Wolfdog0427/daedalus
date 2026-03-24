import copy
import time

# Import ANSI colors + pretty printer from nlu_debug for consistent formatting
from runtime.nlu_debug import C, _pretty


class HistoryTimeline:
    """
    A chronological, deep‑copy‑safe timeline of state mutations.

    Each entry has:
      - action: string describing what happened
      - state: deep copy of the state at that moment
      - timestamp: strictly increasing float (time.time())
    """

    def __init__(self):
        self._entries = []

    # ------------------------------------------------------------
    # APPEND ENTRY
    # ------------------------------------------------------------
    def append(self, action, state):
        entry = {
            "action": action,
            "state": copy.deepcopy(state),
            "timestamp": time.time(),
        }
        self._entries.append(entry)

    # ------------------------------------------------------------
    # GET ALL ENTRIES (RETURN COPIES)
    # ------------------------------------------------------------
    def get_all(self):
        return copy.deepcopy(self._entries)

    # ------------------------------------------------------------
    # FILTERING
    # ------------------------------------------------------------
    def filter(self, action=None, state_key=None, state_value=None):
        results = []

        for entry in self._entries:
            if action is not None and entry["action"] != action:
                continue

            if state_key is not None:
                if state_key not in entry["state"]:
                    continue
                if state_value is not None and entry["state"][state_key] != state_value:
                    continue

            results.append(copy.deepcopy(entry))

        return results

    # ------------------------------------------------------------
    # CLEAR TIMELINE
    # ------------------------------------------------------------
    def clear(self):
        self._entries.clear()


# ------------------------------------------------------------
# ⭐ PRETTY‑PRINTER REQUIRED BY REPL
# ------------------------------------------------------------

def pretty_debug_history(state):
    """
    Pretty‑print the history timeline stored in state["history"].

    The REPL expects this function to exist.
    """
    history = state.get("history", [])

    if not history:
        return f"{C['red']}No history available.{C['end']}"

    rows = [
        f"{C['header']}{C['bold']}--- HISTORY TIMELINE ---{C['end']}",
    ]

    for i, entry in enumerate(history):
        action = entry.get("action", "<unknown>")
        timestamp = entry.get("timestamp", 0)
        state_snapshot = entry.get("state", {})

        rows.append(
            f"{C['blue']}[{i}] {C['end']}"
            f"{C['cyan']}{action}{C['end']}  "
            f"{C['yellow']}@ {timestamp:.3f}{C['end']}"
        )

        rows.append(
            f"{C['green']}state:{C['end']}\n"
            f"{_pretty(state_snapshot)}"
        )

    rows.append(f"{C['header']}{C['bold']}--- END HISTORY ---{C['end']}")

    return "\n".join(rows)
