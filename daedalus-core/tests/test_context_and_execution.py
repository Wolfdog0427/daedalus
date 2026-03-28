import unittest

from runtime.execution.execution import ExecutionEngine
from runtime.execution.goal_manager import GoalManager


class TestContextAndExecution(unittest.TestCase):
    """Integration tests for context resolution and execution engine.

    The execution engine returns *strings* (user-facing messages), not dicts.
    These tests verify string output and state mutations.
    """

    def setUp(self):
        self.state = {}
        self.goal_manager = GoalManager()
        self.engine = ExecutionEngine(self.goal_manager)

    def _exec(self, intent, args=None):
        cmd = {"intent": intent, "args": args or {}}
        return self.engine.execute(cmd, self.state)

    def test_goal_creation(self):
        result = self._exec("create_goal", {"name": "test movement"})
        self.assertIn("Goal created", result)
        self.assertEqual(self.state["active_goal_id"], 1)

    def test_step_creation(self):
        self._exec("create_goal", {"name": "test"})
        result = self._exec("add_step", {"description": "alpha"})
        self.assertIn("Step added", result)
        steps = self.goal_manager.get_active_steps(self.state)
        self.assertEqual(steps[0]["description"], "alpha")
        self.assertEqual(steps[0]["number"], 1)

    def test_move_step_explicit(self):
        self._exec("create_goal", {"name": "test"})
        self._exec("add_step", {"description": "alpha"})
        self._exec("add_step", {"description": "beta"})
        self._exec("add_step", {"description": "gamma"})

        result = self._exec("move_step", {"step_number": 3, "new_position": 1})
        self.assertIn("moved", result)
        steps = self.goal_manager.get_active_steps(self.state)
        self.assertEqual(steps[0]["id"], 3)
        self.assertEqual(steps[0]["number"], 1)

    def test_list_goals(self):
        self._exec("create_goal", {"name": "first"})
        self._exec("create_goal", {"name": "second"})

        result = self._exec("show_goals")
        self.assertIn("Operator Task Goals", result)
        self.assertIn("first", result)
        self.assertIn("second", result)

    def test_switch_goal(self):
        self._exec("create_goal", {"name": "first"})
        self._exec("create_goal", {"name": "second"})

        result = self._exec("switch_goal", {"goal_id": 1})
        self.assertIn("Switched to goal 1", result)
        self.assertEqual(self.state["active_goal_id"], 1)

    def test_renumber_after_delete(self):
        self._exec("create_goal", {"name": "test"})
        self._exec("add_step", {"description": "alpha"})
        self._exec("add_step", {"description": "beta"})
        self._exec("add_step", {"description": "gamma"})

        result = self._exec("delete_step", {"step_number": 1})
        self.assertIn("Step deleted", result)

        steps = self.goal_manager.get_active_steps(self.state)
        self.assertEqual(steps[0]["number"], 1)
        self.assertEqual(steps[1]["number"], 2)

    def test_complete_step(self):
        self._exec("create_goal", {"name": "test"})
        self._exec("add_step", {"description": "alpha"})

        result = self._exec("complete_step", {"step_number": 1})
        self.assertIn("Step completed", result)

    def test_add_step_no_goal(self):
        result = self._exec("add_step", {"description": "orphan"})
        self.assertIn("no active goal", result)


if __name__ == "__main__":
    unittest.main()
