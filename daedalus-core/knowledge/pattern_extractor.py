# knowledge/pattern_extractor.py

"""
Pattern Extractor

This module analyzes the knowledge base to extract:
- entities (names, places, concepts)
- relationships (X is Y, X has Y, X causes Y)
- recurring patterns
- topic clusters
- keyword frequency maps

It is intentionally simple and symbolic.
The LLM can call into this module to get structured signals
that guide deeper reasoning.

This is the beginning of a knowledge graph layer.
"""

from __future__ import annotations

import itertools
import re
from collections import defaultdict, Counter
from typing import Dict, Any, List, Tuple

from knowledge.retrieval import _iter_items


# ------------------------------------------------------------
# BASIC NLP UTILITIES
# ------------------------------------------------------------

ENTITY_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
RELATION_PATTERNS = [
    ("is_a", re.compile(r"(.+?)\s+is\s+(?:a|an|the)\s+(.+?)\.")),
    ("has", re.compile(r"(.+?)\s+has\s+(.+?)\.")),
    ("causes", re.compile(r"(.+?)\s+causes\s+(.+?)\.")),
]


def extract_entities(text: str) -> List[str]:
    """
    Extracts simple capitalized entities.
    """
    return ENTITY_PATTERN.findall(text)


def extract_relations(text: str) -> List[Tuple[str, str, str]]:
    """
    Extracts simple subject-verb-object relations.
    Returns triples: (subject, relation, object)
    """
    triples = []
    for rel_name, pattern in RELATION_PATTERNS:
        for match in pattern.findall(text):
            if len(match) == 2:
                subj, obj = match
                triples.append((subj.strip(), rel_name, obj.strip()))
    return triples


def tokenize(text: str) -> List[str]:
    """
    Simple tokenizer for keyword frequency.
    """
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


# ------------------------------------------------------------
# PATTERN EXTRACTION
# ------------------------------------------------------------

def extract_patterns(limit: int = 500) -> Dict[str, Any]:
    """
    Scans the knowledge base and extracts:
    - entity frequency
    - relation triples
    - keyword frequency
    - topic clusters (keyword-based)

    Returns a structured pattern report.
    """
    entity_counter = Counter()
    keyword_counter = Counter()
    relations = []

    items = list(itertools.islice(_iter_items(), limit))

    for item in items:
        text = item.get("text", "")

        # Entities
        ents = extract_entities(text)
        entity_counter.update(ents)

        # Keywords
        tokens = tokenize(text)
        keyword_counter.update(tokens)

        # Relations
        rels = extract_relations(text)
        relations.extend(rels)

    # Build simple topic clusters
    clusters = _build_topic_clusters(keyword_counter)

    return {
        "entity_frequency": entity_counter.most_common(50),
        "keyword_frequency": keyword_counter.most_common(100),
        "relations": relations[:200],
        "topic_clusters": clusters,
    }


# ------------------------------------------------------------
# TOPIC CLUSTERING
# ------------------------------------------------------------

def _build_topic_clusters(keyword_counter: Counter, cluster_size: int = 10) -> List[List[str]]:
    """
    Groups top keywords into simple clusters based on shared prefixes.
    This is a placeholder for more advanced clustering later.
    """
    top_keywords = [kw for kw, _ in keyword_counter.most_common(200)]
    clusters = defaultdict(list)

    for kw in top_keywords:
        prefix = kw[:3]  # crude but effective for early clustering
        clusters[prefix].append(kw)

    # Only return meaningful clusters
    return [words[:cluster_size] for words in clusters.values() if len(words) >= 3]


# ------------------------------------------------------------
# KNOWLEDGE GRAPH EXPORT
# ------------------------------------------------------------

def build_knowledge_graph(limit: int = 500) -> Dict[str, List[str]]:
    """
    Builds a simple adjacency list representing a knowledge graph.
    Nodes = entities
    Edges = relations between entities
    """
    graph = defaultdict(list)

    items = list(itertools.islice(_iter_items(), limit))

    for item in items:
        text = item.get("text", "")
        rels = extract_relations(text)

        for subj, rel, obj in rels:
            graph[subj].append(f"{rel}:{obj}")

    return dict(graph)
