import unittest
import copy
from runtime.undo_redo import UndoRedoManager


class TestUndoRedo(unittest.TestCase):

    def setUp(self):
        self.mgr = UndoRedoManager()

        self.state1 = {"value": 1}
        self.state2 = {"value": 2}
        self.state3 = {"value": 3}

    # ------------------------------------------------------------
    # BASIC PUSH + UNDO
    # ------------------------------------------------------------
    def test_push_and_undo_returns_previous_state(self):
        self.mgr.push(self.state1)
        self.mgr.push(self.state2)

        out = self.mgr.undo()
        self.assertEqual(out, self.state1)

    # ------------------------------------------------------------
    # MULTI-STEP UNDO
    # ------------------------------------------------------------
    def test_multiple_undo_steps(self):
        self.mgr.push(self.state1)
        self.mgr.push(self.state2)
        self.mgr.push(self.state3)

        self.assertEqual(self.mgr.undo(), self.state2)
        self.assertEqual(self.mgr.undo(), self.state1)

        # No more history
        self.assertIsNone(self.mgr.undo())

    # ------------------------------------------------------------
    # REDO AFTER UNDO
    # ------------------------------------------------------------
    def test_redo_after_undo(self):
        self.mgr.push(self.state1)
        self.mgr.push(self.state2)

        self.mgr.undo()  # back to state1
        out = self.mgr.redo()  # forward to state2

        self.assertEqual(out, self.state2)

    # ------------------------------------------------------------
    # REDO STACK CLEARED ON NEW PUSH
    # ------------------------------------------------------------
    def test_redo_cleared_after_new_push(self):
        self.mgr.push(self.state1)
        self.mgr.push(self.state2)

        self.mgr.undo()  # back to state1

        # New push should clear redo history
        self.mgr.push(self.state3)

        self.assertIsNone(self.mgr.redo())

    # ------------------------------------------------------------
    # DEEP COPY ISOLATION
    # ------------------------------------------------------------
    def test_states_are_deep_copied(self):
        self.mgr.push(self.state1)

        # Mutate original after push
        self.state1["value"] = 999

        restored = self.mgr.undo()
        self.assertEqual(restored["value"], 1)

    # ------------------------------------------------------------
    # EMPTY HISTORY BEHAVIOR
    # ------------------------------------------------------------
    def test_undo_on_empty_history(self):
        self.assertIsNone(self.mgr.undo())

    def test_redo_on_empty_history(self):
        self.assertIsNone(self.mgr.redo())

    # ------------------------------------------------------------
    # UNDO DOES NOT MUTATE INTERNAL HISTORY
    # ------------------------------------------------------------
    def test_undo_does_not_mutate_stored_states(self):
        self.mgr.push(self.state1)
        self.mgr.push(self.state2)

        out = self.mgr.undo()
        out["value"] = 999  # mutate returned state

        # Undo history should remain intact
        again = self.mgr.redo()
        self.assertEqual(again["value"], 2)


if __name__ == "__main__":
    unittest.main()
