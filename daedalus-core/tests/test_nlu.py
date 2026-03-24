import unittest

from nlu.matcher import match_nlu
from nlu.normalizer import normalize_nlu
from nlu.intent_classifier import classify_intent
from nlu.resolver_adapter import adapt_to_command


class TestNLU(unittest.TestCase):

    # ------------------------------------------------------------
    # MATCHER TESTS
    # ------------------------------------------------------------

    def test_matcher_show_plan(self):
        nlu = match_nlu("show plan")
        self.assertEqual(nlu["canonical_intent"], "show_plan")

    def test_matcher_create_goal(self):
        nlu = match_nlu("create goal Build a spaceship")
        self.assertEqual(nlu["canonical_intent"], "create_goal")

    def test_matcher_add_step(self):
        nlu = match_nlu("add step Design hull")
        self.assertEqual(nlu["canonical_intent"], "add_step")

    def test_matcher_complete_step(self):
        nlu = match_nlu("complete step 2")
        self.assertEqual(nlu["canonical_intent"], "complete_step")
        self.assertIn("2", nlu["tokens"])

    # ------------------------------------------------------------
    # NORMALIZER TESTS
    # ------------------------------------------------------------

    def test_normalizer_show_plan(self):
        nlu = match_nlu("show plan")
        norm = normalize_nlu(nlu)
        self.assertEqual(norm["canonical_intent"], "show_plan")

    def test_normalizer_vague_step(self):
        nlu = match_nlu("finish it")
        norm = normalize_nlu(nlu)
        self.assertTrue(norm["vague_step"])

    # ------------------------------------------------------------
    # INTENT CLASSIFIER TESTS
    # ------------------------------------------------------------

    def test_classifier_extract_step_number(self):
        out = classify_intent("complete step 3")
        self.assertEqual(out["step_number"], 3)
        self.assertEqual(out["canonical_intent"], "complete_step")

    def test_classifier_extract_goal_number(self):
        out = classify_intent("switch to goal 2")
        self.assertEqual(out["goal_number"], 2)
        self.assertEqual(out["canonical_intent"], "switch_goal")

    def test_classifier_show_plan(self):
        out = classify_intent("show plan")
        self.assertEqual(out["canonical_intent"], "show_plan")

    # ------------------------------------------------------------
    # RESOLVER ADAPTER TESTS
    # ------------------------------------------------------------

    def test_adapter_show_plan(self):
        cmd = adapt_to_command("show plan", state={})
        self.assertEqual(cmd["intent"], "show_plan")

    def test_adapter_add_step(self):
        cmd = adapt_to_command("add step Design hull", state={})
        self.assertEqual(cmd["intent"], "add_step")

    def test_adapter_complete_step(self):
        cmd = adapt_to_command("complete step 4", state={})
        self.assertEqual(cmd["intent"], "complete_step")
        self.assertEqual(cmd["args"]["step_number"], 4)

    def test_adapter_vague_step(self):
        cmd = adapt_to_command("finish it", state={})
        self.assertEqual(cmd["intent"], "complete_step")
        self.assertIsNone(cmd["args"]["step_number"])


if __name__ == "__main__":
    unittest.main()
