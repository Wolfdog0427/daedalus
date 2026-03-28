# knowledge/retrieval.py

"""
Knowledge Retrieval

Provides read/query access over the append-only knowledge store.

Features:
- load all knowledge items (streaming)
- lookup by ID
- simple keyword search with scoring
- optional filtering by source
- optional exclusion of superseded items (future-ready)

This module is intentionally simple and file-based.
You can later swap the backend (DB, vector store) without
changing the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Iterable
from pathlib import Path
import json
import time

# Must match knowledge/ingestion.py
KNOWLEDGE_DIR = Path("data/knowledge")
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "knowledge_store.jsonl"
INDEX_FILE = KNOWLEDGE_DIR / "index.json"


@dataclass
class RetrievedItem:
    id: str
    source: str
    text: str
    created_at: float
    metadata: Dict[str, Any]
    score: float
    snippet: str


# ------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------

def _ensure_storage():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    if not KNOWLEDGE_FILE.exists():
        KNOWLEDGE_FILE.touch()
    if not INDEX_FILE.exists():
        _initial_index = {
            "canonical": {},
            "superseded": {},
            "meta": {
                "created_at": time.time(),
                "version": 1,
            },
        }
        try:
            from knowledge._atomic_io import atomic_write_json
            atomic_write_json(INDEX_FILE, _initial_index)
        except ImportError:
            with INDEX_FILE.open("w", encoding="utf-8") as f:
                json.dump(_initial_index, f, ensure_ascii=False, indent=2)


def _load_index() -> Dict[str, Any]:
    _ensure_storage()
    with INDEX_FILE.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {
                "canonical": {},
                "superseded": {},
                "meta": {"created_at": time.time(), "version": 1},
            }


def _is_superseded(item_id: str, index: Dict[str, Any]) -> bool:
    return item_id in index.get("superseded", {})


def _iter_items() -> Iterable[Dict[str, Any]]:
    _ensure_storage()
    with KNOWLEDGE_FILE.open("r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue


def _make_snippet(text: str, query: str, max_len: int = 200) -> str:
    if not text:
        return ""
    lower = text.lower()
    q = query.lower().strip()
    if not q:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    idx = lower.find(q)
    if idx == -1:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    start = max(0, idx - max_len // 4)
    end = min(len(text), idx + len(q) + max_len // 2)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------

def get_item_by_id(item_id: str, include_superseded: bool = True) -> Optional[Dict[str, Any]]:
    """
    Returns a single knowledge item by ID, or None if not found.

    If include_superseded is False, items marked as superseded
    in the index will be excluded.
    """
    index = _load_index()

    for item in _iter_items():
        if item.get("id") == item_id:
            if not include_superseded and _is_superseded(item_id, index):
                return None
            return item

    return None


def search(
    query: str,
    limit: int = 20,
    include_superseded: bool = False,
    source_filter: Optional[str] = None,
) -> List[RetrievedItem]:
    """
    Simple keyword search over the knowledge store.

    Scoring:
    - +1 per occurrence of the query (case-insensitive)
    - +0.5 if query appears in metadata
    - +0.2 if query appears in source
    """

    index = _load_index()
    q = query.lower().strip()
    if not q:
        return []
    results: List[RetrievedItem] = []

    for item in _iter_items():
        item_id = item.get("id")
        if not item_id:
            continue

        if not include_superseded and _is_superseded(item_id, index):
            continue

        if source_filter and item.get("source") != source_filter:
            continue

        text = item.get("text") or ""
        metadata = item.get("metadata") or {}
        source = item.get("source") or ""

        score = 0.0
        score += text.lower().count(q)
        score += 0.5 if q in json.dumps(metadata).lower() else 0.0
        score += 0.2 if q in source.lower() else 0.0

        if score <= 0:
            continue

        snippet = _make_snippet(text, query)

        results.append(
            RetrievedItem(
                id=item_id,
                source=source,
                text=text,
                created_at=item.get("created_at", 0),
                metadata=metadata,
                score=score,
                snippet=snippet,
            )
        )

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]


# Historical API name (callers expect `search_knowledge`)
search_knowledge = search
