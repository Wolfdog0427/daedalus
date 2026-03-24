import copy
from runtime.undo_redo import UndoRedoManager
from runtime.history_timeline import HistoryTimeline


class SpeculativeExecutor:
    """
    Provides safe speculative execution and commit semantics.

    - speculate(action):
        Runs the action on a deep copy of the current state.
        Does NOT modify the real state.
        Does NOT touch undo/redo history.
        Raises exceptions without altering state.

    - commit(action):
        Applies the action to the real state.
        Records the committed state to the timeline.
        Uses deep copies to avoid mutation leaks.
        Rolls back on failure.
    """

    def __init__(self, state_store):
        self.state_store = state_store
        self.undo_redo = UndoRedoManager()
        self.timeline = HistoryTimeline()

    # ------------------------------------------------------------
    # SPECULATIVE EXECUTION
    # ------------------------------------------------------------
    def speculate(self, action):
        """
        Run the action on a deep copy of the current state.
        Never modifies real state.
        """
        state = self.state_store.load()
        temp = copy.deepcopy(state)

        try:
            result = action(temp)
            return copy.deepcopy(result)
        except Exception:
            # speculation must not modify real state
            raise

    # ------------------------------------------------------------
    # COMMIT EXECUTION
    # ------------------------------------------------------------
    def commit(self, action):
        """
        Apply the action to the real state.
        Record the result to the timeline.
        Roll back on failure.
        """
        state = self.state_store.load()
        working = copy.deepcopy(state)

        try:
            result = action(working)
        except Exception:
            # commit failed → do not modify state or timeline
            raise

        # commit succeeded → save new state
        self.state_store.save(copy.deepcopy(result))

        # record to timeline
        self.timeline.append("commit", result)

        # push to undo/redo history
        self.undo_redo.push(result)

        return copy.deepcopy(result)
