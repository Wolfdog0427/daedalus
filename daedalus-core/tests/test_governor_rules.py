# tests/test_governor_rules.py
"""
Tests for governor/rules.py — tier decisions and blocking logic.
"""

from __future__ import annotations

import unittest
from governor.rules import (
    decide_base_tier,
    should_recommend_tier2,
    should_recommend_tier3,
    is_tier3_blocked,
)


class TestDecideBaseTier(unittest.TestCase):

    def test_locked_always_tier1(self):
        for mode in ("strict", "normal", "permissive", "unknown"):
            self.assertEqual(decide_base_tier(mode, locked=True), 1)

    def test_strict_gives_tier2(self):
        self.assertEqual(decide_base_tier("strict", locked=False), 2)

    def test_normal_gives_tier3(self):
        self.assertEqual(decide_base_tier("normal", locked=False), 3)

    def test_permissive_gives_tier3(self):
        self.assertEqual(decide_base_tier("permissive", locked=False), 3)

    def test_unknown_mode_gives_tier1(self):
        self.assertEqual(decide_base_tier("bogus", locked=False), 1)


class TestShouldRecommendTier2(unittest.TestCase):

    def test_medium_drift_recommends(self):
        self.assertTrue(should_recommend_tier2("medium", "none", 0))

    def test_high_risk_recommends(self):
        self.assertTrue(should_recommend_tier2("none", "high", 0))

    def test_repeated_failures_recommend(self):
        self.assertTrue(should_recommend_tier2("none", "none", 3))

    def test_clean_state_no_recommendation(self):
        self.assertFalse(should_recommend_tier2("none", "none", 0))


class TestShouldRecommendTier3(unittest.TestCase):

    def test_high_drift_and_risk(self):
        self.assertTrue(should_recommend_tier3("high", "high", 0, 0, "none"))

    def test_blocked_by_high_stability_risk(self):
        self.assertFalse(should_recommend_tier3("high", "high", 0, 0, "high"))

    def test_failed_tier2_triggers(self):
        self.assertTrue(should_recommend_tier3("medium", "none", 0, 3, "none"))

    def test_clean_state(self):
        self.assertFalse(should_recommend_tier3("none", "none", 0, 0, "none"))


class TestIsTier3Blocked(unittest.TestCase):

    def test_locked_blocks(self):
        r = is_tier3_blocked(3, "permissive", locked=True, stability_risk="none")
        self.assertTrue(r["blocked"])

    def test_high_stability_blocks(self):
        r = is_tier3_blocked(3, "permissive", locked=False, stability_risk="critical")
        self.assertTrue(r["blocked"])

    def test_strict_below_tier3_blocks(self):
        r = is_tier3_blocked(2, "strict", locked=False, stability_risk="none")
        self.assertTrue(r["blocked"])

    def test_permissive_not_blocked(self):
        r = is_tier3_blocked(3, "permissive", locked=False, stability_risk="none")
        self.assertFalse(r["blocked"])


if __name__ == "__main__":
    unittest.main()
