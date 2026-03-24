import unittest

from runtime.context_resolver import ContextResolver


class TestContextResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = ContextResolver()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def make_state(self):
        return {
            "active_goal_id": 1,
            "last_step_id": 3,
            "last_goal_id": 2,
            "goals_tree": [
                {
                    "id": 1,
                    "name": "Build a spaceship",
                    "steps": [
                        {"id": 1, "name": "Design hull"},
                        {"id": 2, "name": "Build engine"},
                        {"id": 3, "name": "Install avionics"},
                    ],
                },
                {
                    "id": 2,
                    "name": "Write documentation",
                    "steps": [
                        {"id": 10, "name": "Outline"},
                        {"id": 11, "name": "Draft"},
                    ],
                },
            ],
        }

    # ------------------------------------------------------------
    # STEP RESOLUTION
    # ------------------------------------------------------------

    def test_resolve_explicit_step_number(self):
        state = self.make_state()
        cmd = {"intent": "complete_step", "args": {"step_number": 2}}
        out = self.resolver.resolve(cmd, state)
        self.assertEqual(out["args"]["step_number"], 2)

    def test_resolve_vague_step_last(self):
        state = self.make_state()
        cmd = {
            "intent": "complete_step",
            "args": {"step_number": None},
            "raw": "finish it",
            "repaired": "finish it",
            "repair_confidence": 1.0,
        }
        out = self.resolver.resolve(cmd, state)
        self.assertEqual(out["args"]["step_number"], 3)

    def test_resolve_vague_step_no_last_step(self):
        state = self.make_state()
        state["last_step_id"] = None
        cmd = {
            "intent": "complete_step",
            "args": {"step_number": None},
            "raw": "finish it",
            "repaired": "finish it",
            "repair_confidence": 1.0,
        }
        out = self.resolver.resolve(cmd, state)
        # Should NOT fill anything
        self.assertIsNone(out["args"]["step_number"])

    # ------------------------------------------------------------
    # GOAL RESOLUTION
    # ------------------------------------------------------------

    def test_resolve_explicit_goal_number(self):
        state = self.make_state()
        cmd = {"intent": "switch_goal", "args": {"goal_id": 2}}
        out = self.resolver.resolve(cmd, state)
        self.assertEqual(out["args"]["goal_id"], 2)

    def test_resolve_vague_goal_last(self):
        state = self.make_state()
        cmd = {
            "intent": "switch_goal",
            "args": {"goal_id": None},
            "raw": "switch to my last goal",
            "repaired": "switch to my last goal",
            "repair_confidence": 1.0,
        }
        out = self.resolver.resolve(cmd, state)
        self.assertEqual(out["args"]["goal_id"], 2)

    def test_resolve_vague_goal_no_last_goal(self):
        state = self.make_state()
        state["last_goal_id"] = None
        cmd = {
            "intent": "switch_goal",
            "args": {"goal_id": None},
            "raw": "switch to my last goal",
            "repaired": "switch to my last goal",
            "repair_confidence": 1.0,
        }
        out = self.resolver.resolve(cmd, state)
        self.assertIsNone(out["args"]["goal_id"])

    # ------------------------------------------------------------
    # LOW CONFIDENCE → NO RESOLUTION
    # ------------------------------------------------------------

    def test_low_confidence_skips_resolution(self):
        state = self.make_state()
        cmd = {
            "intent": "complete_step",
            "args": {"step_number": None},
            "raw": "finish it",
            "repaired": "finish it",
            "repair_confidence": 0.5,
        }
        out = self.resolver.resolve(cmd, state)
        # Should NOT resolve because confidence < 0.80
        self.assertIsNone(out["args"]["step_number"])


if __name__ == "__main__":
    unittest.main()
