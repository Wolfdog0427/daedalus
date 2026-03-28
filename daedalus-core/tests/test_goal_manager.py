import unittest
from runtime.execution.goal_manager import GoalManager


class TestGoalManager(unittest.TestCase):

    def setUp(self):
        self.state = {
            "goals_tree": [],
            "active_goal_id": None,
            "next_goal_id": 1,
            "next_step_id": 1,
            "last_step_id": None,
            "last_goal_id": None,
            "last_action": None,
        }
        self.manager = GoalManager()

    # ------------------------------------------------------------
    # GOAL CREATION
    # ------------------------------------------------------------

    def test_create_goal(self):
        goal = self.manager.create_goal("Build a spaceship", self.state)
        self.assertEqual(goal["id"], 1)
        self.assertEqual(goal["name"], "Build a spaceship")
        self.assertEqual(self.state["active_goal_id"], 1)
        self.assertEqual(len(self.state["goals_tree"]), 1)

    def test_create_multiple_goals(self):
        g1 = self.manager.create_goal("Goal A", self.state)
        g2 = self.manager.create_goal("Goal B", self.state)
        self.assertEqual(g1["id"], 1)
        self.assertEqual(g2["id"], 2)
        self.assertEqual(self.state["active_goal_id"], 2)

    # ------------------------------------------------------------
    # SWITCH GOAL
    # ------------------------------------------------------------

    def test_switch_goal(self):
        self.manager.create_goal("A", self.state)
        self.manager.create_goal("B", self.state)
        ok = self.manager.switch_goal(1, self.state)
        self.assertTrue(ok)
        self.assertEqual(self.state["active_goal_id"], 1)

    def test_switch_goal_invalid(self):
        self.manager.create_goal("A", self.state)
        ok = self.manager.switch_goal(999, self.state)
        self.assertFalse(ok)
        self.assertEqual(self.state["active_goal_id"], 1)

    # ------------------------------------------------------------
    # STEP CREATION
    # ------------------------------------------------------------

    def test_add_step(self):
        self.manager.create_goal("A", self.state)
        step = self.manager.add_step("Design hull", self.state)
        self.assertEqual(step["id"], 1)
        self.assertEqual(step["description"], "Design hull")
        self.assertEqual(len(self.state["goals_tree"][0]["steps"]), 1)

    def test_add_multiple_steps(self):
        self.manager.create_goal("A", self.state)
        s1 = self.manager.add_step("One", self.state)
        s2 = self.manager.add_step("Two", self.state)
        self.assertEqual(s1["id"], 1)
        self.assertEqual(s2["id"], 2)

    # ------------------------------------------------------------
    # COMPLETE STEP
    # ------------------------------------------------------------

    def test_complete_step(self):
        self.manager.create_goal("A", self.state)
        self.manager.add_step("One", self.state)
        ok = self.manager.complete_step(1, self.state)
        self.assertTrue(ok)
        step = self.state["goals_tree"][0]["steps"][0]
        self.assertTrue(step["done"])

    def test_complete_step_invalid(self):
        self.manager.create_goal("A", self.state)
        ok = self.manager.complete_step(999, self.state)
        self.assertFalse(ok)

    # ------------------------------------------------------------
    # DELETE STEP
    # ------------------------------------------------------------

    def test_delete_step(self):
        self.manager.create_goal("A", self.state)
        self.manager.add_step("One", self.state)
        ok = self.manager.delete_step(1, self.state)
        self.assertTrue(ok)
        self.assertEqual(len(self.state["goals_tree"][0]["steps"]), 0)

    def test_delete_step_invalid(self):
        self.manager.create_goal("A", self.state)
        ok = self.manager.delete_step(999, self.state)
        self.assertFalse(ok)

    # ------------------------------------------------------------
    # RENAME STEP
    # ------------------------------------------------------------

    def test_rename_step(self):
        self.manager.create_goal("A", self.state)
        self.manager.add_step("One", self.state)
        ok = self.manager.rename_step(1, "New Name", self.state)
        self.assertTrue(ok)
        step = self.state["goals_tree"][0]["steps"][0]
        self.assertEqual(step["description"], "New Name")

    def test_rename_step_invalid(self):
        self.manager.create_goal("A", self.state)
        ok = self.manager.rename_step(999, "New Name", self.state)
        self.assertFalse(ok)

    # ------------------------------------------------------------
    # GETTERS
    # ------------------------------------------------------------

    def test_get_goal(self):
        self.manager.create_goal("A", self.state)
        goal = self.manager.get_goal(1, self.state)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["name"], "A")

    def test_get_goal_invalid(self):
        goal = self.manager.get_goal(999, self.state)
        self.assertIsNone(goal)

    def test_get_step(self):
        self.manager.create_goal("A", self.state)
        self.manager.add_step("One", self.state)
        step = self.manager.get_step(1, self.state)
        self.assertIsNotNone(step)
        self.assertEqual(step["description"], "One")

    def test_get_step_invalid(self):
        self.manager.create_goal("A", self.state)
        step = self.manager.get_step(999, self.state)
        self.assertIsNone(step)


if __name__ == "__main__":
    unittest.main()
