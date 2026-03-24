# knowledge/ingestion.py

"""
Knowledge Ingestion

Provides a simple, append-only knowledge store for:
- raw text ingestion
- URL-based ingestion (via Web Access Layer)

Each ingested item is stored with:
- id
- source (e.g., "manual", URL)
- text
- content_hash
- created_at
- metadata (optional)

Storage is file-based JSONL for simplicity and auditability.
You can later swap this for a DB or vector store without
changing the public API.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import hashlib
import json
import os
import time
from pathlib import Path

from web.tools import fetch_url

# Where ingested knowledge is stored
KNOWLEDGE_DIR = Path("data/knowledge")
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "knowledge_store.jsonl"


@dataclass
class KnowledgeItem:
    id: str
    source: str
    text: str
    content_hash: str
    created_at: float
    metadata: Optional[Dict[str, Any]] = None


def _ensure_storage():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    if not KNOWLEDGE_FILE.exists():
        KNOWLEDGE_FILE.touch()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _generate_id(source: str, content_hash: str) -> str:
    base = f"{source}:{content_hash}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def ingest_text(text: str, source: str = "manual", metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Ingests raw text into the knowledge store.

    Returns:
        The ID of the created KnowledgeItem.
    """
    if not text.strip():
        return "❗ Cannot ingest empty text."

    _ensure_storage()

    content_hash = _hash_text(text)
    item_id = _generate_id(source, content_hash)

    item = KnowledgeItem(
        id=item_id,
        source=source,
        text=text,
        content_hash=content_hash,
        created_at=time.time(),
        metadata=metadata or {},
    )

    with KNOWLEDGE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    return item_id


def ingest_url(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Fetches a URL via the Web Access Layer and ingests its text content.

    Returns:
        The ID of the created KnowledgeItem, or an error string.
    """
    try:
        doc = fetch_url(url)
    except Exception as e:
        return f"❗ URL fetch failed during ingestion: {e}"

    text = doc.get("text", "")
    if not text.strip():
        return "❗ Fetched URL has no text content to ingest."

    meta = metadata or {}
    meta.update(
        {
            "url": doc.get("url"),
            "status": doc.get("status"),
            "content_type": doc.get("content_type"),
            "elapsed_sec": doc.get("elapsed_sec"),
            "content_hash": doc.get("content_hash"),
        }
    )

    return ingest_text(text=text, source=url, metadata=meta)
