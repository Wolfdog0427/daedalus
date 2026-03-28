# tests/test_federated_exchange.py
"""
Tests for knowledge/federated_exchange.py — peer trust and knowledge sharing.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge.federated_exchange as fe


class _FederatedTempDir(unittest.TestCase):
    """Redirect federated storage to a temp dir."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = fe.FEDERATED_DIR
        self._orig_peers = fe.PEERS_FILE
        self._orig_log = fe.EXCHANGE_LOG

        fe.FEDERATED_DIR = Path(self._tmpdir) / "federated"
        fe.PEERS_FILE = fe.FEDERATED_DIR / "peers.json"
        fe.EXCHANGE_LOG = fe.FEDERATED_DIR / "exchange_log.jsonl"

    def tearDown(self):
        fe.FEDERATED_DIR = self._orig_dir
        fe.PEERS_FILE = self._orig_peers
        fe.EXCHANGE_LOG = self._orig_log

        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestNegotiateTrust(_FederatedTempDir):

    def test_initial_trust(self):
        trust = fe.negotiate_trust("peer-1")
        self.assertAlmostEqual(trust, fe.INITIAL_PEER_TRUST)

    def test_trust_persists(self):
        fe.negotiate_trust("peer-1")
        peers = fe._load_peers()
        self.assertIn("peer-1", peers)
        self.assertEqual(peers["peer-1"]["trust"], fe.INITIAL_PEER_TRUST)

    def test_trust_improves_with_accepted_items(self):
        fe.negotiate_trust("peer-2")
        peers = fe._load_peers()
        peers["peer-2"]["items_accepted"] = 50
        peers["peer-2"]["items_rejected"] = 0
        fe._save_peers(peers)

        trust = fe.negotiate_trust("peer-2")
        self.assertGreater(trust, fe.INITIAL_PEER_TRUST)

    def test_trust_degrades_with_rejections(self):
        fe.negotiate_trust("peer-3")
        peers = fe._load_peers()
        peers["peer-3"]["items_accepted"] = 0
        peers["peer-3"]["items_rejected"] = 50
        fe._save_peers(peers)

        trust = fe.negotiate_trust("peer-3")
        self.assertLess(trust, fe.INITIAL_PEER_TRUST)


class TestConcurrentPeerWrites(_FederatedTempDir):

    def test_no_lost_updates(self):
        barrier = threading.Barrier(4)
        errors = []

        def negotiate(peer_id):
            try:
                barrier.wait(timeout=5)
                for _ in range(5):
                    fe.negotiate_trust(peer_id)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=negotiate, args=(f"peer-{i}",))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertFalse(errors)
        peers = fe._load_peers()
        for i in range(4):
            self.assertIn(f"peer-{i}", peers)


class TestPeersLockProtection(_FederatedTempDir):

    def test_load_peers_returns_dict(self):
        fe._ensure_storage()
        peers = fe._load_peers()
        self.assertIsInstance(peers, dict)

    def test_corrupt_peers_file(self):
        fe._ensure_storage()
        fe.PEERS_FILE.write_text("not json", encoding="utf-8")
        peers = fe._load_peers()
        self.assertEqual(peers, {})


if __name__ == "__main__":
    unittest.main()
