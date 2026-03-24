import unittest
from runtime.history_timeline import HistoryTimeline
import copy


class TestHistoryTimeline(unittest.TestCase):

    def setUp(self):
        self.timeline = HistoryTimeline()

    # ------------------------------------------------------------
    # BASIC APPEND
    # ------------------------------------------------------------
    def test_append_creates_entry(self):
        state = {"value": 1}
        self.timeline.append("create_goal", state)

        entries = self.timeline.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "create_goal")
        self.assertEqual(entries[0]["state"]["value"], 1)

    # ------------------------------------------------------------
    # DEEP COPY ISOLATION
    # ------------------------------------------------------------
    def test_state_is_deep_copied(self):
        state = {"value": 1}
        self.timeline.append("add_step", state)

        # mutate original
        state["value"] = 999

        entries = self.timeline.get_all()
        self.assertEqual(entries[0]["state"]["value"], 1)

    # ------------------------------------------------------------
    # TIMESTAMP ORDERING
    # ------------------------------------------------------------
    def test_entries_are_timestamped_and_ordered(self):
        self.timeline.append("a", {"n": 1})
        self.timeline.append("b", {"n": 2})
        self.timeline.append("c", {"n": 3})

        entries = self.timeline.get_all()

        self.assertEqual(entries[0]["action"], "a")
        self.assertEqual(entries[1]["action"], "b")
        self.assertEqual(entries[2]["action"], "c")

        # timestamps must be strictly increasing
        self.assertLess(entries[0]["timestamp"], entries[1]["timestamp"])
        self.assertLess(entries[1]["timestamp"], entries[2]["timestamp"])

    # ------------------------------------------------------------
    # FILTERING BY ACTION
    # ------------------------------------------------------------
    def test_filter_by_action(self):
        self.timeline.append("add_step", {"id": 1})
        self.timeline.append("create_goal", {"id": 2})
        self.timeline.append("add_step", {"id": 3})

        filtered = self.timeline.filter(action="add_step")
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["state"]["id"], 1)
        self.assertEqual(filtered[1]["state"]["id"], 3)

    # ------------------------------------------------------------
    # FILTERING BY KEY IN STATE
    # ------------------------------------------------------------
    def test_filter_by_state_key(self):
        self.timeline.append("add_step", {"goal_id": 1})
        self.timeline.append("add_step", {"goal_id": 2})
        self.timeline.append("add_step", {"goal_id": 1})

        filtered = self.timeline.filter(state_key="goal_id", state_value=1)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["state"]["goal_id"], 1)
        self.assertEqual(filtered[1]["state"]["goal_id"], 1)

    # ------------------------------------------------------------
    # CLEARING THE TIMELINE
    # ------------------------------------------------------------
    def test_clear_resets_timeline(self):
        self.timeline.append("x", {"a": 1})
        self.timeline.append("y", {"b": 2})

        self.timeline.clear()

        self.assertEqual(self.timeline.get_all(), [])

    # ------------------------------------------------------------
    # IMMUTABILITY OF RETURNED ENTRIES
    # ------------------------------------------------------------
    def test_returned_entries_are_copies(self):
        self.timeline.append("add_step", {"value": 1})

        entries = self.timeline.get_all()
        entries[0]["state"]["value"] = 999

        # internal timeline must remain unchanged
        internal = self.timeline.get_all()
        self.assertEqual(internal[0]["state"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
