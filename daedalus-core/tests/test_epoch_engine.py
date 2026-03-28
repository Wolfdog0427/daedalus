# tests/test_epoch_engine.py
"""
Tests for knowledge/entropy/epoch_engine.py — epoch lifecycle.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import knowledge.entropy.epoch_engine as ee


class _EpochTempDir(unittest.TestCase):
    """Redirect epoch storage to a temp dir."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = ee.EPOCH_DIR
        self._orig_current = ee.CURRENT_EPOCH_FILE
        self._orig_archive = ee.EPOCH_ARCHIVE_DIR

        ee.EPOCH_DIR = Path(self._tmpdir) / "epochs"
        ee.CURRENT_EPOCH_FILE = ee.EPOCH_DIR / "current.json"
        ee.EPOCH_ARCHIVE_DIR = ee.EPOCH_DIR / "archive"

    def tearDown(self):
        ee.EPOCH_DIR = self._orig_dir
        ee.CURRENT_EPOCH_FILE = self._orig_current
        ee.EPOCH_ARCHIVE_DIR = self._orig_archive

        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestStartEpoch(_EpochTempDir):

    def test_start_creates_epoch(self):
        epoch = ee.start_epoch(epoch_id="test-1", duration_hours=1.0)
        self.assertEqual(epoch["id"], "test-1")
        self.assertEqual(epoch["status"], "running")
        self.assertTrue(ee.CURRENT_EPOCH_FILE.exists())

    def test_start_while_running_ends_previous(self):
        ee.start_epoch(epoch_id="epoch-a")
        epoch_b = ee.start_epoch(epoch_id="epoch-b")
        self.assertEqual(epoch_b["id"], "epoch-b")
        self.assertEqual(epoch_b["status"], "running")


class TestEpochDeviation(_EpochTempDir):

    def test_record_deviation(self):
        ee.start_epoch(epoch_id="test-dev")
        dev_id = ee.record_epoch_deviation({"name": "test_deviation"})
        self.assertIsNotNone(dev_id)

        current = ee.get_current_epoch()
        self.assertGreater(len(current["deviations"]), 0)

    def test_no_deviation_without_epoch(self):
        result = ee.record_epoch_deviation({"name": "orphan"})
        self.assertIsNone(result)


class TestEpochStatus(_EpochTempDir):

    def test_no_epoch_status(self):
        status = ee.get_epoch_status()
        self.assertFalse(status["active"])
        self.assertTrue(status["should_start"])

    def test_running_epoch_status(self):
        ee.start_epoch(epoch_id="status-test", duration_hours=24.0)
        status = ee.get_epoch_status()
        self.assertTrue(status["active"])
        self.assertEqual(status["epoch_id"], "status-test")


class TestIsExpired(_EpochTempDir):

    def test_expired_when_no_epoch(self):
        self.assertTrue(ee.is_epoch_expired())

    def test_not_expired_freshly_started(self):
        ee.start_epoch(epoch_id="fresh", duration_hours=24.0)
        self.assertFalse(ee.is_epoch_expired())


class TestCaptureMetrics(_EpochTempDir):

    def test_capture_start_metrics(self):
        ee.start_epoch(epoch_id="metrics-test")
        ee.capture_epoch_metrics({"drift": 0.01}, phase="start")
        current = ee.get_current_epoch()
        self.assertEqual(current["metrics_at_start"]["drift"], 0.01)


class TestSanitizeForJson(unittest.TestCase):

    def test_native_types_unchanged(self):
        data = {"a": 1, "b": "hello", "c": [True, None, 3.14]}
        self.assertEqual(ee._sanitize_for_json(data), data)

    def test_non_native_converted(self):
        data = {"ts": object()}
        result = ee._sanitize_for_json(data)
        self.assertIsInstance(result["ts"], str)

    def test_nested_sanitization(self):
        data = {"outer": {"inner": set()}}
        result = ee._sanitize_for_json(data)
        self.assertIsInstance(result["outer"]["inner"], str)


if __name__ == "__main__":
    unittest.main()
