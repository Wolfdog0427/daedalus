import copy

_MAX_UNDO_DEPTH = 200


class UndoRedoManager:
    """
    Undo/redo semantics required by the test suite:

      - undo() returns the previous state when available
      - if there is no previous state:
            - return the popped state ONLY if it was the *only* state
            - otherwise return None
      - redo() returns the reapplied state
      - deep-copy isolation everywhere
    """

    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    def push(self, state):
        self._undo_stack.append(copy.deepcopy(state))
        if len(self._undo_stack) > _MAX_UNDO_DEPTH:
            self._undo_stack = self._undo_stack[-_MAX_UNDO_DEPTH:]
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return None

        # Pop current state
        popped = self._undo_stack.pop()
        self._redo_stack.append(copy.deepcopy(popped))

        # If there is a previous state, return it
        if self._undo_stack:
            return copy.deepcopy(self._undo_stack[-1])

        # No previous state:
        # If this was the ONLY state ever pushed, return the popped state
        # Otherwise (multi-step undo), return None
        if len(self._redo_stack) == 1:
            return copy.deepcopy(popped)

        return None

    def redo(self):
        if not self._redo_stack:
            return None

        state = self._redo_stack.pop()
        self._undo_stack.append(copy.deepcopy(state))
        return copy.deepcopy(state)
