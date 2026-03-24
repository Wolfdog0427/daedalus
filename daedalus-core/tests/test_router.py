import unittest
from runtime.router import Router


class TestRouter(unittest.TestCase):

    def setUp(self):
        self.router = Router()

    # ------------------------------------------------------------
    # BASIC INTENT ROUTING
    # ------------------------------------------------------------
    def test_route_create_goal(self):
        out = self.router.route(
            {"intent": "create_goal", "args": {"name": "Build a spaceship"}}
        )
        self.assertEqual(out["command"], "create_goal")
        self.assertEqual(out["args"]["name"], "Build a spaceship")

    def test_route_add_step(self):
        out = self.router.route(
            {"intent": "add_step", "args": {"title": "Design hull"}}
        )
        self.assertEqual(out["command"], "add_step")
        self.assertEqual(out["args"]["title"], "Design hull")

    def test_route_complete_step(self):
        out = self.router.route(
            {"intent": "complete_step", "args": {"step_number": 2}}
        )
        self.assertEqual(out["command"], "complete_step")
        self.assertEqual(out["args"]["step_number"], 2)

    # ------------------------------------------------------------
    # SWITCHING GOALS
    # ------------------------------------------------------------
    def test_route_switch_goal(self):
        out = self.router.route(
            {"intent": "switch_goal", "args": {"goal_number": 1}}
        )
        self.assertEqual(out["command"], "switch_goal")
        self.assertEqual(out["args"]["goal_number"], 1)

    # ------------------------------------------------------------
    # SHOW COMMANDS
    # ------------------------------------------------------------
    def test_route_show_goals(self):
        out = self.router.route({"intent": "show_goals", "args": {}})
        self.assertEqual(out["command"], "show_goals")

    def test_route_show_plan(self):
        out = self.router.route({"intent": "show_plan", "args": {}})
        self.assertEqual(out["command"], "show_plan")

    # ------------------------------------------------------------
    # DELETE / RENAME
    # ------------------------------------------------------------
    def test_route_delete_step(self):
        out = self.router.route(
            {"intent": "delete_step", "args": {"step_number": 3}}
        )
        self.assertEqual(out["command"], "delete_step")
        self.assertEqual(out["args"]["step_number"], 3)

    def test_route_rename_step(self):
        out = self.router.route(
            {"intent": "rename_step", "args": {"step_number": 1, "new_title": "Updated"}}
        )
        self.assertEqual(out["command"], "rename_step")
        self.assertEqual(out["args"]["step_number"], 1)
        self.assertEqual(out["args"]["new_title"], "Updated")

    # ------------------------------------------------------------
    # UNKNOWN INTENT HANDLING
    # ------------------------------------------------------------
    def test_route_unknown_intent(self):
        out = self.router.route({"intent": "nonsense_intent", "args": {}})
        self.assertEqual(out["command"], "unknown_intent")

    # ------------------------------------------------------------
    # ARGUMENT PASS-THROUGH
    # ------------------------------------------------------------
    def test_route_preserves_all_args(self):
        out = self.router.route(
            {"intent": "add_step", "args": {"title": "Test", "priority": "high"}}
        )
        self.assertEqual(out["args"]["priority"], "high")


if __name__ == "__main__":
    unittest.main()
