# knowledge/knowledge_graph.py

"""
Knowledge Graph

A persistent, queryable graph structure built from:
- extracted entities
- extracted relationships
- reasoning outputs
- verified information

Features:
- adjacency list graph
- trust-weighted edges
- entity metadata
- relationship types
- graph queries (neighbors, paths, clusters)
- incremental updates
- persistence to disk

This is the backbone of conceptual reasoning.
"""

from __future__ import annotations

import itertools
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter, deque

from knowledge.pattern_extractor import extract_entities, extract_relations
from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import compute_trust_score
from knowledge._atomic_io import atomic_write_json


# ------------------------------------------------------------
# STORAGE PATHS
# ------------------------------------------------------------

GRAPH_DIR = Path("data/knowledge_graph")
GRAPH_FILE = GRAPH_DIR / "graph.json"
ENTITY_FILE = GRAPH_DIR / "entities.json"

_graph_lock = threading.Lock()
_MAX_ENTITY_SOURCES = 200


# ------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------

def _ensure_storage():
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    if not GRAPH_FILE.exists():
        atomic_write_json(GRAPH_FILE, {})
    if not ENTITY_FILE.exists():
        atomic_write_json(ENTITY_FILE, {})


def _load_graph() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_storage()
    try:
        data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _load_entities() -> Dict[str, Dict[str, Any]]:
    _ensure_storage()
    try:
        data = json.loads(ENTITY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_graph(graph: Dict[str, Any]):
    atomic_write_json(GRAPH_FILE, graph)


def _save_entities(entities: Dict[str, Any]):
    atomic_write_json(ENTITY_FILE, entities)


# ------------------------------------------------------------
# GRAPH UPDATE LOGIC
# ------------------------------------------------------------

def update_graph_from_item(item: Dict[str, Any]):
    """
    Extracts entities and relations from a knowledge item
    and updates the graph accordingly.  Thread-safe.
    """
    with _graph_lock:
        graph = _load_graph()
        entities = _load_entities()

        text = item.get("text", "")
        item_id = item.get("id")
        trust = compute_trust_score(item)

        ents = extract_entities(text)
        for e in ents:
            entities.setdefault(e, {
                "occurrences": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "sources": [],
            })
            entities[e]["last_seen"] = time.time()
            sources = entities[e].get("sources", [])
            entities[e]["sources"] = sources
            if item_id not in sources:
                sources.append(item_id)
                entities[e]["occurrences"] = entities[e].get("occurrences", 0) + 1
            if len(sources) > _MAX_ENTITY_SOURCES:
                entities[e]["sources"] = sources[-_MAX_ENTITY_SOURCES:]
                entities[e]["occurrences"] = len(entities[e]["sources"])

        rels = extract_relations(text)
        for subj, rel, obj in rels:
            edges = graph.setdefault(subj, [])
            if not any(e.get("relation") == rel and e.get("object") == obj
                       and e.get("source_item") == item_id for e in edges):
                edges.append({
                    "relation": rel,
                    "object": obj,
                    "source_item": item_id,
                    "trust": trust,
                    "timestamp": time.time(),
                })

        _save_entities(entities)
        _save_graph(graph)


def rebuild_graph(limit: int = 5000) -> Dict[str, Any]:
    """
    Rebuilds the entire knowledge graph from scratch.  Thread-safe.
    """
    with _graph_lock:
        graph: Dict[str, list] = {}
        entities: Dict[str, Dict[str, Any]] = {}

        items = list(itertools.islice(_iter_items(), limit))

        for item in items:
            text = item.get("text", "")
            item_id = item.get("id")
            trust = compute_trust_score(item)

            ents = extract_entities(text)
            for e in ents:
                entities.setdefault(e, {
                    "occurrences": 0,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "sources": [],
                })
                entities[e]["last_seen"] = time.time()
                sources = entities[e].get("sources", [])
                entities[e]["sources"] = sources
                if item_id not in sources:
                    sources.append(item_id)
                    entities[e]["occurrences"] = entities[e].get("occurrences", 0) + 1
                if len(sources) > _MAX_ENTITY_SOURCES:
                    entities[e]["sources"] = sources[-_MAX_ENTITY_SOURCES:]
                    entities[e]["occurrences"] = len(entities[e]["sources"])

            rels = extract_relations(text)
            for subj, rel, obj in rels:
                edges = graph.setdefault(subj, [])
                if not any(e.get("relation") == rel and e.get("object") == obj
                           and e.get("source_item") == item_id for e in edges):
                    edges.append({
                        "relation": rel,
                        "object": obj,
                        "source_item": item_id,
                        "trust": trust,
                        "timestamp": time.time(),
                    })

        _save_entities(entities)
        _save_graph(graph)

        return {
            "entities": len(entities),
            "relations": sum(len(v) for v in graph.values()),
        }


# ------------------------------------------------------------
# GRAPH QUERIES (all reads hold the lock for consistency)
# ------------------------------------------------------------

def get_entity_info(entity: str) -> Optional[Dict[str, Any]]:
    """Returns metadata about an entity."""
    with _graph_lock:
        entities = _load_entities()
        return entities.get(entity)


def get_neighbors(entity: str) -> List[Dict[str, Any]]:
    """Returns all outgoing edges (relations) from an entity."""
    with _graph_lock:
        graph = _load_graph()
        return list(graph.get(entity, []))


def find_path(start: str, end: str, max_depth: int = 4) -> Optional[List[str]]:
    """Simple BFS to find a path between two entities."""
    with _graph_lock:
        graph = _load_graph()

    visited = set()
    queue = deque([(start, [start])])

    while queue:
        node, path = queue.popleft()
        if node == end:
            return path

        if node in visited:
            continue
        visited.add(node)

        for edge in graph.get(node, []):
            nxt = edge.get("object", "")
            if nxt not in visited and len(path) < max_depth:
                queue.append((nxt, path + [nxt]))

    return None


def get_top_entities(limit: int = 50) -> List[Tuple[str, int]]:
    """Returns the most frequently occurring entities."""
    with _graph_lock:
        entities = _load_entities()
    counts = [(e, data.get("occurrences", 0)) for e, data in entities.items()]
    counts.sort(key=lambda x: x[1], reverse=True)
    return counts[:limit]


def get_relations_for(entity: str) -> List[Tuple[str, str]]:
    """Returns (relation, object) pairs for an entity."""
    with _graph_lock:
        graph = _load_graph()
    return [(edge.get("relation", ""), edge.get("object", "")) for edge in graph.get(entity, [])]


# ------------------------------------------------------------
# GRAPH ANALYTICS
# ------------------------------------------------------------

def compute_entity_centrality() -> List[Tuple[str, int]]:
    """Computes simple degree centrality for each entity."""
    with _graph_lock:
        graph = _load_graph()
    centrality = Counter()

    for subj, edges in graph.items():
        centrality[subj] += len(edges)
        for edge in edges:
            centrality[edge.get("object", "")] += 1

    return centrality.most_common(50)


def get_connected_components() -> List[List[str]]:
    """Finds connected components in the graph (iterative DFS)."""
    with _graph_lock:
        graph = _load_graph()

    visited: set = set()
    components: List[List[str]] = []

    for node in graph.keys():
        if node in visited:
            continue
        comp: List[str] = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            comp.append(current)
            for edge in graph.get(current, []):
                nxt = edge.get("object", "")
                if nxt not in visited:
                    stack.append(nxt)
        components.append(comp)

    return components
