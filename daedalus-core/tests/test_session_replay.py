import unittest
from runtime.history_timeline import HistoryTimeline
from runtime.session_replay import SessionReplay
import time


class TestSessionReplay(unittest.TestCase):

    def setUp(self):
        self.timeline = HistoryTimeline()
        self.replay = SessionReplay(self.timeline)

        # seed timeline with deterministic entries
        self.timeline.append("create_goal", {"goal_id": 1, "title": "Clean room"})
        time.sleep(0.001)
        self.timeline.append("add_step", {"goal_id": 1, "step_id": 1, "text": "Pick up clothes"})
        time.sleep(0.001)
        self.timeline.append("add_step", {"goal_id": 1, "step_id": 2, "text": "Vacuum floor"})
        time.sleep(0.001)
        self.timeline.append("complete_step", {"goal_id": 1, "step_id": 1})

    # ------------------------------------------------------------
    # BASIC REPLAY
    # ------------------------------------------------------------
    def test_replay_all(self):
        events = self.replay.replay_all()
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0]["action"], "create_goal")
        self.assertEqual(events[-1]["action"], "complete_step")

    # ------------------------------------------------------------
    # REPLAY LAST N EVENTS
    # ------------------------------------------------------------
    def test_replay_last_n(self):
        events = self.replay.replay_last(2)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["action"], "add_step")
        self.assertEqual(events[1]["action"], "complete_step")

    # ------------------------------------------------------------
    # FILTER BY GOAL
    # ------------------------------------------------------------
    def test_replay_for_goal(self):
        events = self.replay.replay_for_goal(1)
        self.assertEqual(len(events), 4)
        for e in events:
            self.assertEqual(e["state"]["goal_id"], 1)

    # ------------------------------------------------------------
    # FILTER BY STEP
    # ------------------------------------------------------------
    def test_replay_for_step(self):
        events = self.replay.replay_for_step(1)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["action"], "add_step")
        self.assertEqual(events[1]["action"], "complete_step")

    # ------------------------------------------------------------
    # SUMMARY OF SESSION
    # ------------------------------------------------------------
    def test_summary(self):
        summary = self.replay.summary()

        self.assertIn("4 actions", summary)
        self.assertIn("create_goal", summary)
        self.assertIn("complete_step", summary)

    # ------------------------------------------------------------
    # SUMMARY OF LAST N EVENTS
    # ------------------------------------------------------------
    def test_summary_last_n(self):
        summary = self.replay.summary_last(2)

        self.assertIn("2 actions", summary)
        self.assertIn("add_step", summary)
        self.assertIn("complete_step", summary)

    # ------------------------------------------------------------
    # EMPTY TIMELINE HANDLING
    # ------------------------------------------------------------
    def test_empty_timeline(self):
        empty = HistoryTimeline()
        replay = SessionReplay(empty)

        self.assertEqual(replay.replay_all(), [])
        self.assertEqual(replay.summary(), "No actions recorded.")


if __name__ == "__main__":
    unittest.main()
