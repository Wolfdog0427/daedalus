# tests/test_governor_state_store.py
"""
Tests for governor/state_store.py — governor state persistence,
thread-safe mutate_state context manager, and proposal storage.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import governor.state_store as store


class _StoreTempDir(unittest.TestCase):
    """Redirect state_store paths to a temp directory for isolation."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = store.STATE_DIR
        self._orig_path = store.STATE_PATH
        self._orig_prop = store.PROPOSALS_PATH
        self._orig_lock = store._LOCK_FILE

        store.STATE_DIR = Path(self._tmpdir)
        store.STATE_PATH = store.STATE_DIR / "governor_state.json"
        store.PROPOSALS_PATH = store.STATE_DIR / "governor_proposals.json"
        store._LOCK_FILE = store.STATE_DIR / ".governor_state.lock"

    def tearDown(self):
        store.STATE_DIR = self._orig_dir
        store.STATE_PATH = self._orig_path
        store.PROPOSALS_PATH = self._orig_prop
        store._LOCK_FILE = self._orig_lock

        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestLoadSaveState(_StoreTempDir):

    def test_default_state_on_missing_file(self):
        state = store.load_state()
        self.assertIn("autonomy_mode", state)
        self.assertIn("proposals", state)
        self.assertIsInstance(state["proposals"]["pending"], list)

    def test_round_trip(self):
        state = store.load_state()
        state["autonomy_mode"] = "permissive"
        store.save_state(state)

        loaded = store.load_state()
        self.assertEqual(loaded["autonomy_mode"], "permissive")

    def test_corrupt_file_returns_defaults(self):
        store.STATE_DIR.mkdir(parents=True, exist_ok=True)
        store.STATE_PATH.write_text("not json", encoding="utf-8")
        state = store.load_state()
        self.assertEqual(state["autonomy_mode"], "strict")

    def test_preserves_patch_history_defaults(self):
        store.STATE_DIR.mkdir(parents=True, exist_ok=True)
        store.STATE_PATH.write_text(
            json.dumps({"patch_history": {"total_cycles": 5}}),
            encoding="utf-8",
        )
        state = store.load_state()
        self.assertEqual(state["patch_history"]["total_cycles"], 5)
        self.assertIn("successful_patches", state["patch_history"])


class TestMutateState(_StoreTempDir):

    def test_basic_mutate(self):
        with store.mutate_state() as state:
            state["current_tier"] = 3

        loaded = store.load_state()
        self.assertEqual(loaded["current_tier"], 3)

    def test_exception_does_not_persist(self):
        original = store.load_state()
        try:
            with store.mutate_state() as state:
                state["current_tier"] = 99
                raise ValueError("abort")
        except ValueError:
            pass

        loaded = store.load_state()
        self.assertEqual(loaded.get("current_tier", original.get("current_tier")),
                         original.get("current_tier"))

    def test_concurrent_mutate_no_lost_updates(self):
        barrier = threading.Barrier(4)
        errors = []

        def increment(field):
            try:
                barrier.wait(timeout=5)
                for _ in range(10):
                    with store.mutate_state() as state:
                        state[field] = state.get(field, 0) + 1
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=increment, args=(f"counter_{i}",))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertFalse(errors, f"Thread errors: {errors}")
        loaded = store.load_state()
        for i in range(4):
            self.assertEqual(loaded.get(f"counter_{i}", 0), 10)


class TestProposals(_StoreTempDir):

    def test_round_trip(self):
        proposals = [{"id": "prop-1", "status": "pending"}]
        store.save_proposals(proposals)
        loaded = store.load_proposals()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["id"], "prop-1")

    def test_corrupt_returns_empty(self):
        store.STATE_DIR.mkdir(parents=True, exist_ok=True)
        store.PROPOSALS_PATH.write_text("bad", encoding="utf-8")
        self.assertEqual(store.load_proposals(), [])


if __name__ == "__main__":
    unittest.main()
