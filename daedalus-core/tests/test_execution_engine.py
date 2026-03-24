import unittest

from runtime.execution import ExecutionEngine
from runtime.goal_manager import GoalManager


class TestExecutionEngine(unittest.TestCase):

    def setUp(self):
        # Fresh state for every test
        self.state = {
            "goals_tree": [],
            "active_goal_id": None,
            "next_goal_id": 1,
            "next_step_id": 1,
            "last_step_id": None,
            "last_goal_id": None,
            "last_action": None,
        }

        self.goal_manager = GoalManager()
        self.engine = ExecutionEngine(self.goal_manager)

        # Create a goal
        out = self.engine.execute(
            {"intent": "create_goal", "args": {"name": "Build a spaceship"}},
            self.state
        )
        self.assertIn("✓ Goal created", out)

        # Add steps
        self.engine.execute(
            {"intent": "add_step", "args": {"description": "Design hull"}},
            self.state
        )
        self.engine.execute(
            {"intent": "add_step", "args": {"description": "Build engine"}},
            self.state
        )
        self.engine.execute(
            {"intent": "add_step", "args": {"description": "Install avionics"}},
            self.state
        )

    # ------------------------------------------------------------
    # CREATE GOAL
    # ------------------------------------------------------------

    def test_create_goal(self):
        out = self.engine.execute(
            {"intent": "create_goal", "args": {"name": "Write docs"}},
            self.state
        )
        self.assertIn("✓ Goal created", out)
        self.assertEqual(self.state["last_action"], "create_goal")

    # ------------------------------------------------------------
    # SWITCH GOAL
    # ------------------------------------------------------------

    def test_switch_goal(self):
        # Create second goal
        out = self.engine.execute(
            {"intent": "create_goal", "args": {"name": "Write docs"}},
            self.state
        )
        self.assertIn("✓ Goal created", out)

        # Switch to goal 2
        out = self.engine.execute(
            {"intent": "switch_goal", "args": {"goal_id": 2}},
            self.state
        )
        self.assertIn("✓ Switched to goal 2", out)
        self.assertEqual(self.state["active_goal_id"], 2)

    def test_switch_goal_invalid(self):
        out = self.engine.execute(
            {"intent": "switch_goal", "args": {"goal_id": 999}},
            self.state
        )
        self.assertIn("⚠ Goal 999 does not exist.", out)

    # ------------------------------------------------------------
    # ADD STEP
    # ------------------------------------------------------------

    def test_add_step(self):
        out = self.engine.execute(
            {"intent": "add_step", "args": {"description": "Paint exterior"}},
            self.state
        )
        self.assertIn("✓ Step added", out)
        self.assertEqual(self.state["last_action"], "add_step")

    # ------------------------------------------------------------
    # COMPLETE STEP
    # ------------------------------------------------------------

    def test_complete_step(self):
        out = self.engine.execute(
            {"intent": "complete_step", "args": {"step_number": 2}},
            self.state
        )
        self.assertIn("✓ Step completed", out)
        self.assertEqual(self.state["last_action"], "complete_step")

    def test_complete_step_invalid(self):
        out = self.engine.execute(
            {"intent": "complete_step", "args": {"step_number": 99}},
            self.state
        )
        self.assertIn("⚠ Step 99 does not exist.", out)

    # ------------------------------------------------------------
    # DELETE STEP
    # ------------------------------------------------------------

    def test_delete_step(self):
        out = self.engine.execute(
            {"intent": "delete_step", "args": {"step_number": 1}},
            self.state
        )
        self.assertIn("✓ Step deleted", out)
        self.assertEqual(self.state["last_action"], "delete_step")

    # ------------------------------------------------------------
    # RENAME STEP
    # ------------------------------------------------------------

    def test_rename_step(self):
        out = self.engine.execute(
            {
                "intent": "rename_step",
                "args": {"step_number": 1, "description": "Design outer hull"},
            },
            self.state
        )
        self.assertIn("✓ Step renamed", out)
        self.assertEqual(self.state["last_action"], "rename_step")

    # ------------------------------------------------------------
    # SHOW PLAN / SHOW GOALS
    # ------------------------------------------------------------

    def test_show_plan(self):
        out = self.engine.execute(
            {"intent": "show_plan", "args": {}},
            self.state
        )
        self.assertIn("📋 Plan for:", out)

    def test_show_goals(self):
        out = self.engine.execute(
            {"intent": "show_goals", "args": {}},
            self.state
        )
        self.assertIn("📋 Goals:", out)

    # ------------------------------------------------------------
    # UNKNOWN INTENT
    # ------------------------------------------------------------

    def test_unknown_intent(self):
        out = self.engine.execute(
            {"intent": "fly_to_mars", "args": {}},
            self.state
        )
        self.assertIn("⚠ Unknown intent", out)


if __name__ == "__main__":
    unittest.main()
