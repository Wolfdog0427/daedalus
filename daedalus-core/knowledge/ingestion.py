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


def ingest_text(
    text: str,
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None,
    verification_status: str = "unverified",
) -> str:
    """
    Ingests raw text into the knowledge store.

    Args:
        text: The knowledge content to ingest.
        source: Origin identifier (e.g., "manual", URL, "curiosity_engine").
        metadata: Optional metadata dict.
        verification_status: Trust lifecycle stage. One of:
            "unverified" - default, not yet checked
            "provisional" - ingested via fast path, queued for background verification
            "light_verified" - passed contradiction check only
            "verified" - passed full verification pipeline

    Returns:
        The ID of the created KnowledgeItem.
    """
    if not text.strip():
        raise ValueError("Cannot ingest empty text.")

    _ensure_storage()

    content_hash = _hash_text(text)
    item_id = _generate_id(source, content_hash)

    meta = metadata or {}
    meta.setdefault("verification_status", verification_status)

    item = KnowledgeItem(
        id=item_id,
        source=source,
        text=text,
        content_hash=content_hash,
        created_at=time.time(),
        metadata=meta,
    )

    from knowledge._atomic_io import knowledge_file_lock
    with knowledge_file_lock:
        if KNOWLEDGE_FILE.exists():
            for raw_line in KNOWLEDGE_FILE.open("r", encoding="utf-8"):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    existing = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if existing.get("id") == item_id:
                    return item_id
        with KNOWLEDGE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    return item_id


def ingest_url(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Fetches a URL via the Web Access Layer and ingests its text content.

    Returns:
        The ID of the created KnowledgeItem.

    Raises:
        ValueError: If the URL fetch fails or yields no text content.
    """
    try:
        doc = fetch_url(url)
    except Exception as e:
        raise ValueError(f"URL fetch failed during ingestion: {e}") from e

    text = doc.get("text", "")
    if not text.strip():
        raise ValueError("Fetched URL has no text content to ingest.")

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
