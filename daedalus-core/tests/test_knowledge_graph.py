# tests/test_knowledge_graph.py
"""
Tests for knowledge/knowledge_graph.py — graph operations.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge.knowledge_graph as kg
from knowledge._atomic_io import atomic_write_json


class _GraphTempDir(unittest.TestCase):
    """Redirect graph storage to a temp dir."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_dir = kg.GRAPH_DIR
        self._orig_gf = kg.GRAPH_FILE
        self._orig_ef = kg.ENTITY_FILE

        kg.GRAPH_DIR = Path(self._tmpdir) / "knowledge_graph"
        kg.GRAPH_FILE = kg.GRAPH_DIR / "graph.json"
        kg.ENTITY_FILE = kg.GRAPH_DIR / "entities.json"

    def tearDown(self):
        kg.GRAPH_DIR = self._orig_dir
        kg.GRAPH_FILE = self._orig_gf
        kg.ENTITY_FILE = self._orig_ef

        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestGraphBasics(_GraphTempDir):

    def test_ensure_storage_creates_files(self):
        kg._ensure_storage()
        self.assertTrue(kg.GRAPH_FILE.exists())
        self.assertTrue(kg.ENTITY_FILE.exists())

    def test_load_graph_empty(self):
        kg._ensure_storage()
        graph = kg._load_graph()
        self.assertIsInstance(graph, dict)

    def test_load_entities_empty(self):
        kg._ensure_storage()
        entities = kg._load_entities()
        self.assertIsInstance(entities, dict)


class TestUpdateGraph(_GraphTempDir):

    def test_update_creates_entity(self):
        kg._ensure_storage()
        item = {
            "id": "item-1",
            "text": "Python is a programming language",
            "trust_score": 0.8,
        }
        with patch("knowledge.knowledge_graph.extract_entities",
                    return_value=["Python", "programming language"]), \
             patch("knowledge.knowledge_graph.extract_relations",
                    return_value=[("Python", "is_a", "programming language")]):
            kg.update_graph_from_item(item)

        entities = kg._load_entities()
        self.assertIn("Python", entities)
        self.assertIn("programming language", entities)

    def test_duplicate_item_no_double_count(self):
        kg._ensure_storage()
        item = {"id": "item-1", "text": "Test", "trust_score": 0.8}

        with patch("knowledge.knowledge_graph.extract_entities",
                    return_value=["TestEntity"]), \
             patch("knowledge.knowledge_graph.extract_relations",
                    return_value=[]):
            kg.update_graph_from_item(item)
            kg.update_graph_from_item(item)

        entities = kg._load_entities()
        e = entities.get("TestEntity", {})
        self.assertEqual(e.get("occurrences", 0), 1)


class TestFindPath(_GraphTempDir):

    def _write_graph(self, graph):
        kg._ensure_storage()
        atomic_write_json(kg.GRAPH_FILE, graph)

    def test_find_path_direct_neighbor(self):
        self._write_graph({
            "a": [{"object": "b", "relation": "related", "weight": 1.0}],
        })
        path = kg.find_path("a", "b")
        self.assertIsNotNone(path)
        self.assertEqual(path, ["a", "b"])

    def test_find_path_no_connection(self):
        self._write_graph({
            "a": [{"object": "b", "relation": "r", "weight": 1.0}],
            "c": [],
        })
        path = kg.find_path("a", "c")
        self.assertIsNone(path)

    def test_find_path_multi_hop(self):
        self._write_graph({
            "a": [{"object": "b", "relation": "r"}],
            "b": [{"object": "c", "relation": "r"}],
            "c": [],
        })
        path = kg.find_path("a", "c")
        self.assertIsNotNone(path)
        self.assertEqual(path, ["a", "b", "c"])


class TestTopEntities(_GraphTempDir):

    def test_empty_graph(self):
        kg._ensure_storage()
        top = kg.get_top_entities(10)
        self.assertIsInstance(top, list)
        self.assertEqual(len(top), 0)


class TestConnectedComponents(_GraphTempDir):

    def test_empty(self):
        kg._ensure_storage()
        comps = kg.get_connected_components()
        self.assertEqual(comps, [])

    def test_single_component(self):
        kg._ensure_storage()
        atomic_write_json(kg.GRAPH_FILE, {
            "a": [{"object": "b", "relation": "r"}],
            "b": [{"object": "c", "relation": "r"}],
            "c": [],
        })
        comps = kg.get_connected_components()
        self.assertEqual(len(comps), 1)
        self.assertEqual(set(comps[0]), {"a", "b", "c"})

    def test_disconnected_components(self):
        kg._ensure_storage()
        atomic_write_json(kg.GRAPH_FILE, {
            "a": [{"object": "b", "relation": "r"}],
            "b": [],
            "x": [{"object": "y", "relation": "r"}],
            "y": [],
        })
        comps = kg.get_connected_components()
        self.assertEqual(len(comps), 2)


class TestCentrality(_GraphTempDir):

    def test_centrality_empty(self):
        kg._ensure_storage()
        c = kg.compute_entity_centrality()
        self.assertEqual(c, [])


if __name__ == "__main__":
    unittest.main()
