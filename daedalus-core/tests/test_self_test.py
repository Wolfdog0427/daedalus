import unittest
from runtime.self_test import SelfTestResult, SelfTestHarness


class TestSelfTestHarness(unittest.TestCase):

    def setUp(self):
        self.harness = SelfTestHarness()

    # ------------------------------------------------------------
    # BASIC CHECK REGISTRATION & EXECUTION
    # ------------------------------------------------------------
    def test_register_and_run_single_check_ok(self):
        def check_ok():
            return True, "all good"

        self.harness.register_check("check_ok", check_ok)
        result = self.harness.run_all()

        self.assertIsInstance(result, SelfTestResult)
        self.assertTrue(result.overall_ok)
        self.assertIn("check_ok", result.details)
        self.assertTrue(result.details["check_ok"]["ok"])
        self.assertEqual(result.details["check_ok"]["message"], "all good")

    def test_register_and_run_single_check_fail(self):
        def check_fail():
            return False, "something broke"

        self.harness.register_check("check_fail", check_fail)
        result = self.harness.run_all()

        self.assertFalse(result.overall_ok)
        self.assertIn("check_fail", result.details)
        self.assertFalse(result.details["check_fail"]["ok"])
        self.assertEqual(result.details["check_fail"]["message"], "something broke")

    # ------------------------------------------------------------
    # MULTIPLE CHECKS & AGGREGATION
    # ------------------------------------------------------------
    def test_multiple_checks_aggregate_status(self):
        def ok1():
            return True, "ok1"

        def ok2():
            return True, "ok2"

        def bad():
            return False, "bad"

        self.harness.register_check("ok1", ok1)
        self.harness.register_check("ok2", ok2)
        self.harness.register_check("bad", bad)

        result = self.harness.run_all()

        self.assertFalse(result.overall_ok)
        self.assertTrue(result.details["ok1"]["ok"])
        self.assertTrue(result.details["ok2"]["ok"])
        self.assertFalse(result.details["bad"]["ok"])

    # ------------------------------------------------------------
    # EXCEPTION HANDLING
    # ------------------------------------------------------------
    def test_check_exception_is_captured_as_failure(self):
        def boom():
            raise RuntimeError("boom")

        self.harness.register_check("boom", boom)
        result = self.harness.run_all()

        self.assertFalse(result.overall_ok)
        self.assertIn("boom", result.details)
        self.assertFalse(result.details["boom"]["ok"])
        self.assertIn("boom", result.details["boom"]["message"])

    # ------------------------------------------------------------
    # EMPTY HARNESS
    # ------------------------------------------------------------
    def test_no_checks_results_in_ok(self):
        result = self.harness.run_all()
        self.assertTrue(result.overall_ok)
        self.assertEqual(result.details, {})


if __name__ == "__main__":
    unittest.main()
