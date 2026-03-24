# knowledge/trust_scoring.py

"""
Trust Scoring

This module assigns trust scores to knowledge items and sources.
It also provides a candidate-scoring function for the
Self-Healing Orchestrator (SHO).
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, Any, Optional, List

from knowledge.retrieval import _iter_items, get_item_by_id
from knowledge.storage_manager import replace_item
from knowledge.ingestion import ingest_text


# ------------------------------------------------------------
# DEFAULT SOURCE TRUST SCORES
# ------------------------------------------------------------

DEFAULT_SOURCE_TRUST = {
    "manual": 0.80,
    "verified": 0.95,
    "summarization_pass": 0.70,
    "replacement": 0.85,
}

TRUST_BY_DOMAIN = {
    "wikipedia.org": 0.75,
    "mit.edu": 0.90,
    "stanford.edu": 0.90,
    "gov": 0.95,
    "edu": 0.85,
}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _domain_from_source(source: str) -> Optional[str]:
    if "://" not in source:
        return None
    try:
        return source.split("/")[2].lower()
    except Exception:
        return None


def _domain_trust(domain: Optional[str]) -> float:
    if not domain:
        return 0.0
    for key, score in TRUST_BY_DOMAIN.items():
        if domain.endswith(key):
            return score
    return 0.0


# ------------------------------------------------------------
# CONTENT-LEVEL TRUST
# ------------------------------------------------------------

def score_content_quality(text: str) -> float:
    length = len(text)

    if length < 50:
        return 0.10
    if length < 200:
        return 0.30
    if length < 1000:
        return 0.60
    if length < 5000:
        return 0.80
    if length < 20000:
        return 0.90
    return 0.70


# ------------------------------------------------------------
# SOURCE-LEVEL TRUST
# ------------------------------------------------------------

def score_source(source: str) -> float:
    if source in DEFAULT_SOURCE_TRUST:
        return DEFAULT_SOURCE_TRUST[source]

    domain = _domain_from_source(source)
    domain_score = _domain_trust(domain)

    if domain_score > 0:
        return domain_score

    return 0.50


# ------------------------------------------------------------
# FULL TRUST SCORE
# ------------------------------------------------------------

def compute_trust_score(item: Dict[str, Any]) -> float:
    source = item.get("source", "")
    text = item.get("text", "")
    meta = item.get("metadata", {}) or {}

    source_score = score_source(source)
    content_score = score_content_quality(text)
    verified_bonus = 0.10 if meta.get("verified", False) else 0.0

    return max(0.0, min(1.0, (source_score * 0.6) + (content_score * 0.4) + verified_bonus))


# ------------------------------------------------------------
# CONTRADICTION DETECTION
# ------------------------------------------------------------

def detect_contradiction(text_a: str, text_b: str) -> bool:
    a = text_a.lower()
    b = text_b.lower()

    negations = ["not", "never", "no ", "false", "incorrect"]

    if any(n in a for n in negations) and any(n in b for n in negations):
        overlap = len(set(a.split()) & set(b.split()))
        if overlap < 5:
            return True

    return False


# ------------------------------------------------------------
# REPLACEMENT DECISION LOGIC
# ------------------------------------------------------------

def should_replace(old_item: Dict[str, Any], new_text: str) -> bool:
    old_score = compute_trust_score(old_item)
    new_score = score_content_quality(new_text)

    if new_score > old_score + 0.15:
        return True

    if detect_contradiction(old_item.get("text", ""), new_text):
        if new_score > old_score:
            return True

    return False


# ------------------------------------------------------------
# PUBLIC API: VERIFY + REPLACE
# ------------------------------------------------------------

def verify_and_ingest(text: str, source: str = "verified") -> str:
    return ingest_text(text, source=source, metadata={"verified": True})


def ingest_with_replacement_check(new_text: str, source: str = "manual") -> str:
    new_hash = _hash_text(new_text)

    for item in _iter_items():
        old_text = item.get("text", "")
        old_hash = _hash_text(old_text)

        if new_hash == old_hash:
            return item["id"]

        if old_text[:100] == new_text[:100]:
            if should_replace(item, new_text):
                return replace_item(
                    old_id=item["id"],
                    new_text=new_text,
                    reason="trust_score_replacement",
                    source=source,
                )

    return ingest_text(new_text, source=source)


# ------------------------------------------------------------
# SHO CANDIDATE SCORING (NEW)
# ------------------------------------------------------------

def score_candidate(
    candidate: Dict[str, Any],
    sandbox_result: Dict[str, Any],
    diagnostics: Dict[str, Any],
) -> Dict[str, float]:
    """
    Produces a unified score for SHO candidate selection.
    """

    # Patch quality heuristic
    patch_quality = 0.5
    if "strategy" in candidate:
        if candidate["strategy"] == "generic_improvement":
            patch_quality = 0.6

    # Diagnostics heuristic
    diag_penalty = 0.0
    if diagnostics.get("error_type") not in (None, "", "system_review"):
        diag_penalty = 0.2

    # Stability heuristic
    stability = sandbox_result.get("stability", {})
    stability_score = stability.get("stability_score", 0.5)

    # Final improvement score
    improvement_score = max(
        0.0,
        min(
            1.0,
            (patch_quality * 0.5)
            + (stability_score * 0.4)
            - diag_penalty
        ),
    )

    return {
        "improvement_score": improvement_score,
        "risk_score": 1.0 - stability_score,
        "trust_score": patch_quality,
    }
