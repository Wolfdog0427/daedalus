import unittest
from runtime.speculative_execution import SpeculativeExecutor
from runtime.state_store import StateStore


class TestSpeculativeExecution(unittest.TestCase):

    def setUp(self):
        self.store = StateStore()
        self.store.save({"value": 1})
        self.exec = SpeculativeExecutor(self.store)

    # ------------------------------------------------------------
    # BASIC SPECULATION RETURNS HYPOTHETICAL RESULT
    # ------------------------------------------------------------
    def test_speculate_returns_hypothetical_state(self):
        def action(state):
            state["value"] += 1
            return state

        result = self.exec.speculate(action)
        self.assertEqual(result["value"], 2)

        # original state must remain unchanged
        self.assertEqual(self.store.load()["value"], 1)

    # ------------------------------------------------------------
    # SPECULATION DOES NOT COMMIT CHANGES
    # ------------------------------------------------------------
    def test_speculation_does_not_commit(self):
        def action(state):
            state["value"] = 999
            return state

        _ = self.exec.speculate(action)

        # state store must remain unchanged
        self.assertEqual(self.store.load()["value"], 1)

    # ------------------------------------------------------------
    # COMMIT APPLIES THE ACTION
    # ------------------------------------------------------------
    def test_commit_applies_action(self):
        def action(state):
            state["value"] += 10
            return state

        self.exec.commit(action)

        self.assertEqual(self.store.load()["value"], 11)

    # ------------------------------------------------------------
    # COMMIT RECORDS TO TIMELINE
    # ------------------------------------------------------------
    def test_commit_records_timeline_entry(self):
        def action(state):
            state["value"] += 5
            return state

        self.exec.commit(action)

        entries = self.exec.timeline.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "commit")
        self.assertEqual(entries[0]["state"]["value"], 6)

    # ------------------------------------------------------------
    # SPECULATION USES UNDO/REDO SAFELY
    # ------------------------------------------------------------
    def test_speculation_uses_undo_redo_safely(self):
        def action(state):
            state["value"] = 42
            return state

        result = self.exec.speculate(action)
        self.assertEqual(result["value"], 42)

        # ensure undo/redo stack is untouched
        self.assertIsNone(self.exec.undo_redo.undo())

    # ------------------------------------------------------------
    # FAILED SPECULATION DOES NOT MODIFY STATE
    # ------------------------------------------------------------
    def test_failed_speculation_does_not_modify_state(self):
        def action(state):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            self.exec.speculate(action)

        # state must remain unchanged
        self.assertEqual(self.store.load()["value"], 1)

    # ------------------------------------------------------------
    # FAILED COMMIT DOES NOT MODIFY STATE
    # ------------------------------------------------------------
    def test_failed_commit_does_not_modify_state(self):
        def action(state):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            self.exec.commit(action)

        # state must remain unchanged
        self.assertEqual(self.store.load()["value"], 1)

        # timeline must remain empty
        self.assertEqual(self.exec.timeline.get_all(), [])


if __name__ == "__main__":
    unittest.main()
