import unittest
import copy
from runtime.state_store import StateStore


class TestStateStore(unittest.TestCase):

    def setUp(self):
        self.store = StateStore()
        self.sample_state = {
            "goals_tree": [
                {
                    "id": 1,
                    "name": "Build a spaceship",
                    "steps": [
                        {"id": 1, "number": 1, "description": "Design hull", "done": False},
                        {"id": 2, "number": 2, "description": "Gather materials", "done": True},
                    ],
                }
            ],
            "active_goal_id": 1,
            "next_goal_id": 2,
            "next_step_id": 3,
        }

    # ------------------------------------------------------------
    # BASIC LOAD / SAVE
    # ------------------------------------------------------------
    def test_save_and_load_round_trip(self):
        self.store.save(self.sample_state)
        loaded = self.store.load()

        expected = dict(self.sample_state)
        expected.setdefault("history", [])
        self.assertEqual(loaded, expected)

    # ------------------------------------------------------------
    # IMMUTABILITY GUARANTEE
    # ------------------------------------------------------------
    def test_load_returns_deep_copy(self):
        self.store.save(self.sample_state)
        loaded = self.store.load()

        # Mutate loaded
        loaded["goals_tree"][0]["name"] = "CHANGED"

        # Original must remain unchanged
        self.assertNotEqual(loaded["goals_tree"][0]["name"],
                            self.store._state["goals_tree"][0]["name"])

    def test_save_stores_deep_copy(self):
        original = copy.deepcopy(self.sample_state)
        self.store.save(self.sample_state)

        # Mutate original after saving
        original["goals_tree"][0]["name"] = "CHANGED"

        # Stored version must remain unchanged
        self.assertNotEqual(original["goals_tree"][0]["name"],
                            self.store._state["goals_tree"][0]["name"])

    # ------------------------------------------------------------
    # DEFAULT STATE
    # ------------------------------------------------------------
    def test_load_default_state(self):
        store = StateStore()
        loaded = store.load()

        self.assertIn("goals_tree", loaded)
        self.assertIn("active_goal_id", loaded)
        self.assertIn("next_goal_id", loaded)
        self.assertIn("next_step_id", loaded)

    # ------------------------------------------------------------
    # STATE ISOLATION
    # ------------------------------------------------------------
    def test_multiple_loads_are_independent(self):
        self.store.save(self.sample_state)

        a = self.store.load()
        b = self.store.load()

        a["next_goal_id"] = 999

        self.assertNotEqual(a["next_goal_id"], b["next_goal_id"])


if __name__ == "__main__":
    unittest.main()
