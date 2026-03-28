# tests/test_governance_kernel.py
"""
Tests for governance/kernel.py — the central governance authority.

Covers:
- evaluate_change pipeline (kill switch, stabilise, circuit breaker)
- Fail-closed behavior when sub-modules are missing
- Circuit breaker trip/reset lifecycle
- Kill switch activate/deactivate
- Stabilise mode gating
- Governance health scoring
- Kernel state and log management
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

import governance.kernel as kernel


class _KernelTestBase(unittest.TestCase):
    """Reset kernel state before every test."""

    def setUp(self):
        kernel.reset_kernel("test_setup")
        kernel._KERNEL_LOG.clear()


class TestEvaluateChange(_KernelTestBase):

    @patch("governance.kernel._knowledge_governor_locked", return_value=False)
    @patch("governance.safety_invariants.enforce_invariants",
           return_value={"passed": True, "violations": [], "checked": 5})
    @patch("governance.change_contracts.enforce_contract",
           return_value={"allowed": True, "risk_score": 10,
                         "needs_approval": False, "reversible": True})
    @patch("governance.envelopes.compute_envelope",
           return_value={"forbidden_operations": [], "risk_ceiling": 60})
    def test_allowed_change(self, _env, _cc, _inv, _lock):
        result = kernel.evaluate_change({"type": "patch_apply"})
        self.assertTrue(result["allowed"])
        self.assertFalse(result.get("needs_approval", True))
        self.assertLessEqual(result["risk_score"], 60)

    def test_kill_switch_blocks_all(self):
        kernel.activate_kill_switch("test")
        result = kernel.evaluate_change({"type": "patch_apply"})
        self.assertFalse(result["allowed"])
        self.assertIn("kill switch", result["reason"])

    def test_stabilise_blocks_non_governance(self):
        kernel.activate_stabilise_mode("test")
        result = kernel.evaluate_change({"type": "patch_apply"})
        self.assertFalse(result["allowed"])
        self.assertIn("stabilise", result["reason"])

    def test_stabilise_allows_governance_meta_changes(self):
        kernel.activate_stabilise_mode("test")
        with patch("governance.safety_invariants.enforce_invariants",
                    return_value={"passed": True, "violations": [], "checked": 1}), \
             patch("governance.change_contracts.enforce_contract",
                    return_value={"allowed": True, "risk_score": 5,
                                  "needs_approval": False, "reversible": True}), \
             patch("governance.envelopes.compute_envelope",
                    return_value={"forbidden_operations": [], "risk_ceiling": 60}):
            result = kernel.evaluate_change({"type": "governance_mode_change"})
            self.assertTrue(result["allowed"])

    @patch("governance.kernel._knowledge_governor_locked", return_value=False)
    def test_fail_closed_on_missing_invariants(self, _lock):
        with patch.dict("sys.modules", {"governance.safety_invariants": None}):
            result = kernel.evaluate_change({"type": "patch_apply"})
            self.assertFalse(result["allowed"])
            self.assertIn("fail-closed", result["reason"])

    @patch("governance.kernel._knowledge_governor_locked", return_value=True)
    def test_knowledge_governor_lock_blocks(self, _lock):
        result = kernel.evaluate_change({"type": "patch_apply"})
        self.assertFalse(result["allowed"])
        self.assertIn("knowledge governor locked", result["reason"])


class TestCircuitBreaker(_KernelTestBase):

    def test_trip_and_reset_lifecycle(self):
        self.assertFalse(kernel._circuit_breaker_tripped)

        with patch("governance.kernel.compute_governance_health",
                    return_value={"governance_score": 10}):
            result = kernel.apply_circuit_breakers()
            self.assertTrue(result["tripped"])

        blocked = kernel.evaluate_change({"type": "patch_apply"})
        self.assertFalse(blocked["allowed"])
        self.assertIn("circuit breaker", blocked["reason"])

        kernel.reset_circuit_breaker("test_reset")
        self.assertFalse(kernel._circuit_breaker_tripped)

    def test_no_trip_when_healthy(self):
        with patch("governance.kernel.compute_governance_health",
                    return_value={"governance_score": 80}):
            result = kernel.apply_circuit_breakers()
            self.assertFalse(result["tripped"])


class TestKillSwitch(_KernelTestBase):

    def test_activate_deactivate(self):
        r = kernel.activate_kill_switch("test")
        self.assertTrue(r["active"])
        self.assertTrue(kernel._kill_switch_active)

        r = kernel.deactivate_kill_switch("test")
        self.assertFalse(r["active"])
        self.assertFalse(kernel._kill_switch_active)


class TestGovernanceHealth(_KernelTestBase):

    def test_healthy_baseline(self):
        health = kernel.compute_governance_health()
        self.assertGreater(health["governance_score"], 0)
        self.assertFalse(health["kill_switch"])
        self.assertFalse(health["circuit_breaker"])
        self.assertFalse(health["stabilise_mode"])

    def test_kill_switch_degrades_score(self):
        baseline = kernel.compute_governance_health()["governance_score"]
        kernel.activate_kill_switch("test")
        degraded = kernel.compute_governance_health()["governance_score"]
        self.assertLess(degraded, baseline)


class TestKernelLog(_KernelTestBase):

    def test_log_accumulates(self):
        kernel.activate_kill_switch("test")
        kernel.evaluate_change({"type": "patch_apply"})
        log = kernel.get_kernel_log(10)
        self.assertGreaterEqual(len(log), 1)

    def test_log_limit(self):
        log = kernel.get_kernel_log(0)
        self.assertEqual(len(log), 0)


class TestResetKernel(_KernelTestBase):

    def test_reset_clears_everything(self):
        kernel.activate_kill_switch("test")
        kernel.activate_stabilise_mode("test")
        kernel.reset_kernel("test")
        self.assertFalse(kernel._kill_switch_active)
        self.assertFalse(kernel._stabilise_mode)
        self.assertFalse(kernel._circuit_breaker_tripped)


if __name__ == "__main__":
    unittest.main()
