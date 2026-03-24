import unittest
from runtime.crash_recovery import CrashRecoveryWrapper


class DummyEngine:
    """A fake engine to simulate success and failure."""

    def __init__(self):
        self.calls = []

    def execute(self, command, state):
        self.calls.append(command)

        if command.get("force_error"):
            raise RuntimeError("boom")

        return {"ok": True, "result": "success"}


class TestCrashRecovery(unittest.TestCase):

    def setUp(self):
        self.engine = DummyEngine()
        self.wrapper = CrashRecoveryWrapper(self.engine)

    # ------------------------------------------------------------
    # SUCCESS PATH
    # ------------------------------------------------------------
    def test_successful_execution_passes_through(self):
        out = self.wrapper.safe_execute({"cmd": "test"}, {})
        self.assertTrue(out["ok"])
        self.assertEqual(out["result"], "success")
        self.assertEqual(self.engine.calls[-1]["cmd"], "test")

    # ------------------------------------------------------------
    # FAILURE PATH
    # ------------------------------------------------------------
    def test_exception_is_caught_and_reported(self):
        out = self.wrapper.safe_execute({"force_error": True}, {})
        self.assertFalse(out["ok"])
        self.assertIn("error", out)
        self.assertIn("boom", out["error"])

    # ------------------------------------------------------------
    # STATE IS NOT MUTATED ON FAILURE
    # ------------------------------------------------------------
    def test_state_is_not_modified_on_failure(self):
        state = {"value": 1}
        original = {"value": 1}

        self.wrapper.safe_execute({"force_error": True}, state)

        self.assertEqual(state, original)

    # ------------------------------------------------------------
    # ENGINE STILL RECORDS CALL ATTEMPT
    # ------------------------------------------------------------
    def test_engine_call_is_recorded_even_on_failure(self):
        self.wrapper.safe_execute({"force_error": True}, {})
        self.assertEqual(self.engine.calls[-1]["force_error"], True)


if __name__ == "__main__":
    unittest.main()
