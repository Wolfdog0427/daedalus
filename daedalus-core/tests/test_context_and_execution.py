import unittest

from core.execution import ExecutionEngine
from runtime.context_resolver import ContextResolver
from runtime.goal_manager import GoalManager


class TestContextAndExecution(unittest.TestCase):

    def setUp(self):
        self.state = {}
        self.goal_manager = GoalManager()
        self.engine = ExecutionEngine(self.goal_manager)
        self.resolver = ContextResolver()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def run_cmd(self, cmd):
        """Simulate full pipeline: resolver → execution."""
        resolved = self.resolver.resolve(cmd, self.state)
        result = self.engine.execute(resolved, self.state)
        return resolved, result

    def make_cmd(self, intent, args=None, text=""):
        """Build a synthetic command dict like resolver_adapter would."""
        return {
            "intent": intent,
            "args": args or {},
            "raw": text,
            "repaired": text,
            "repair_confidence": 1.0,
            "repair_notes": [],
        }

    # ------------------------------------------------------------
    # TESTS
    # ------------------------------------------------------------

    def test_goal_creation(self):
        cmd = self.make_cmd("create_goal", text="create a new goal to test movement")
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertEqual(result["goal"]["name"], "test movement")
        self.assertEqual(self.state["active_goal_id"], 1)

    def test_step_creation(self):
        # Create goal
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to test"))

        # Add step
        cmd = self.make_cmd("add_step", text="add a step to alpha")
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertEqual(result["step"]["description"], "alpha")
        self.assertEqual(result["step"]["number"], 1)

    def test_move_step_explicit(self):
        # Setup
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to test"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to alpha"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to beta"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to gamma"))

        # Move step 3 → position 1
        cmd = self.make_cmd(
            "move_step",
            args={"step_number": 3, "new_position": 1},
            text="move step 3 to position 1",
        )
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        steps = result["steps"]
        self.assertEqual(steps[0]["id"], 3)
        self.assertEqual(steps[0]["number"], 1)

    def test_move_step_vague(self):
        # Setup
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to test"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to alpha"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to beta"))

        # Mark last_step_id
        self.state["last_step_id"] = 2

        # Vague reference: "move it to position 1"
        cmd = self.make_cmd(
            "move_step",
            args={"new_position": 1},
            text="move it to position 1",
        )
        resolved, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertEqual(resolved["args"]["step_number"], 2)

    def test_list_goals(self):
        # Create two goals
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to first"))
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to second"))

        cmd = self.make_cmd("list_goals", text="list goals")
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["goals"]), 2)
        self.assertEqual(result["active_goal_id"], 2)

    def test_switch_goal(self):
        # Create two goals
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to first"))
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to second"))

        # Switch back to goal 1
        cmd = self.make_cmd("switch_goal", args={"goal_id": 1}, text="switch goal 1")
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertEqual(self.state["active_goal_id"], 1)

    def test_renumber_after_delete(self):
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to test"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to alpha"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to beta"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to gamma"))

        # Delete step 1
        cmd = self.make_cmd("delete_step", args={"step_number": 1}, text="delete step 1")
        _, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])

        steps = self.goal_manager.get_active_steps(self.state)
        self.assertEqual(steps[0]["number"], 1)
        self.assertEqual(steps[1]["number"], 2)

    def test_context_trace(self):
        self.run_cmd(self.make_cmd("create_goal", text="create a new goal to test"))
        self.run_cmd(self.make_cmd("add_step", text="add a step to alpha"))

        # Mark last step
        self.state["last_step_id"] = 1

        cmd = self.make_cmd("complete_step", args={}, text="finish it")
        resolved, result = self.run_cmd(cmd)

        self.assertTrue(result["ok"])
        self.assertIn("resolve_last_step", [t["rule"] for t in resolved["context_trace"]])


if __name__ == "__main__":
    unittest.main()
