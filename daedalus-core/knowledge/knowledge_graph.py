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

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter

from knowledge.pattern_extractor import extract_entities, extract_relations
from knowledge.retrieval import _iter_items
from knowledge.trust_scoring import compute_trust_score


# ------------------------------------------------------------
# STORAGE PATHS
# ------------------------------------------------------------

GRAPH_DIR = Path("data/knowledge_graph")
GRAPH_FILE = GRAPH_DIR / "graph.json"
ENTITY_FILE = GRAPH_DIR / "entities.json"


# ------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------

def _ensure_storage():
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    if not GRAPH_FILE.exists():
        GRAPH_FILE.write_text(json.dumps({}, indent=2))
    if not ENTITY_FILE.exists():
        ENTITY_FILE.write_text(json.dumps({}, indent=2))


def _load_graph() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_storage()
    try:
        return json.loads(GRAPH_FILE.read_text())
    except Exception:
        return {}


def _load_entities() -> Dict[str, Dict[str, Any]]:
    _ensure_storage()
    try:
        return json.loads(ENTITY_FILE.read_text())
    except Exception:
        return {}


def _save_graph(graph: Dict[str, Any]):
    GRAPH_FILE.write_text(json.dumps(graph, indent=2))


def _save_entities(entities: Dict[str, Any]):
    ENTITY_FILE.write_text(json.dumps(entities, indent=2))


# ------------------------------------------------------------
# GRAPH UPDATE LOGIC
# ------------------------------------------------------------

def update_graph_from_item(item: Dict[str, Any]):
    """
    Extracts entities and relations from a knowledge item
    and updates the graph accordingly.
    """
    graph = _load_graph()
    entities = _load_entities()

    text = item.get("text", "")
    item_id = item.get("id")
    trust = compute_trust_score(item)

    # Extract entities
    ents = extract_entities(text)
    for e in ents:
        entities.setdefault(e, {
            "occurrences": 0,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "sources": [],
        })
        entities[e]["occurrences"] += 1
        entities[e]["last_seen"] = time.time()
        entities[e]["sources"].append(item_id)

    # Extract relations
    rels = extract_relations(text)
    for subj, rel, obj in rels:
        graph.setdefault(subj, [])
        graph[subj].append({
            "relation": rel,
            "object": obj,
            "source_item": item_id,
            "trust": trust,
            "timestamp": time.time(),
        })

    _save_graph(graph)
    _save_entities(entities)


def rebuild_graph(limit: int = 5000) -> Dict[str, Any]:
    """
    Rebuilds the entire knowledge graph from scratch.
    Useful after major ingestion or cleanup.
    """
    graph = {}
    entities = {}

    items = list(_iter_items())[:limit]

    for item in items:
        text = item.get("text", "")
        item_id = item.get("id")
        trust = compute_trust_score(item)

        # Entities
        ents = extract_entities(text)
        for e in ents:
            entities.setdefault(e, {
                "occurrences": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "sources": [],
            })
            entities[e]["occurrences"] += 1
            entities[e]["sources"].append(item_id)

        # Relations
        rels = extract_relations(text)
        for subj, rel, obj in rels:
            graph.setdefault(subj, [])
            graph[subj].append({
                "relation": rel,
                "object": obj,
                "source_item": item_id,
                "trust": trust,
                "timestamp": time.time(),
            })

    _save_graph(graph)
    _save_entities(entities)

    return {
        "entities": len(entities),
        "relations": sum(len(v) for v in graph.values()),
    }


# ------------------------------------------------------------
# GRAPH QUERIES
# ------------------------------------------------------------

def get_entity_info(entity: str) -> Optional[Dict[str, Any]]:
    """
    Returns metadata about an entity.
    """
    entities = _load_entities()
    return entities.get(entity)


def get_neighbors(entity: str) -> List[Dict[str, Any]]:
    """
    Returns all outgoing edges (relations) from an entity.
    """
    graph = _load_graph()
    return graph.get(entity, [])


def find_path(start: str, end: str, max_depth: int = 4) -> Optional[List[str]]:
    """
    Simple BFS to find a path between two entities.
    """
    graph = _load_graph()
    visited = set()
    queue = [(start, [start])]

    while queue:
        node, path = queue.pop(0)
        if node == end:
            return path

        if node in visited:
            continue
        visited.add(node)

        for edge in graph.get(node, []):
            nxt = edge["object"]
            if nxt not in visited and len(path) < max_depth:
                queue.append((nxt, path + [nxt]))

    return None


def get_top_entities(limit: int = 50) -> List[Tuple[str, int]]:
    """
    Returns the most frequently occurring entities.
    """
    entities = _load_entities()
    counts = [(e, data["occurrences"]) for e, data in entities.items()]
    counts.sort(key=lambda x: x[1], reverse=True)
    return counts[:limit]


def get_relations_for(entity: str) -> List[Tuple[str, str]]:
    """
    Returns (relation, object) pairs for an entity.
    """
    graph = _load_graph()
    return [(edge["relation"], edge["object"]) for edge in graph.get(entity, [])]


# ------------------------------------------------------------
# GRAPH ANALYTICS
# ------------------------------------------------------------

def compute_entity_centrality() -> List[Tuple[str, int]]:
    """
    Computes simple degree centrality for each entity.
    """
    graph = _load_graph()
    centrality = Counter()

    for subj, edges in graph.items():
        centrality[subj] += len(edges)
        for edge in edges:
            centrality[edge["object"]] += 1

    return centrality.most_common(50)


def get_connected_components() -> List[List[str]]:
    """
    Finds connected components in the graph.
    """
    graph = _load_graph()
    visited = set()
    components = []

    def dfs(node, comp):
        visited.add(node)
        comp.append(node)
        for edge in graph.get(node, []):
            nxt = edge["object"]
            if nxt not in visited:
                dfs(nxt, comp)

    for node in graph.keys():
        if node not in visited:
            comp = []
            dfs(node, comp)
            components.append(comp)

    return components
