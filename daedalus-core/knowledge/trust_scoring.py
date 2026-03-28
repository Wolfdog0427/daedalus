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
import threading
from typing import Dict, Any, Optional, List

from knowledge.retrieval import _iter_items, get_item_by_id
from knowledge.storage_manager import replace_item_from_text
from knowledge.ingestion import ingest_text

try:
    from knowledge.source_integrity import validate_source as _validate_source
    _SOURCE_INTEGRITY_AVAILABLE = True
except ImportError:
    _SOURCE_INTEGRITY_AVAILABLE = False


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

# Momentum: how much each consecutive success/failure shifts trust
MOMENTUM_SUCCESS_BONUS = 0.02
MOMENTUM_FAILURE_PENALTY = 0.05
MOMENTUM_CAP = 0.25  # max cumulative momentum bonus above baseline
MOMENTUM_DECAY_FACTOR = 0.99  # per-cycle decay toward zero

# Sim-fix H1: Trust ceiling + natural decay
TRUST_CEILING = 0.95  # effective trust cap — keeps trust discriminating
TRUST_NATURAL_DECAY = 0.001  # per-cycle decay so trust must be continuously earned


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
# TRUST MOMENTUM TRACKER (F4)
# ------------------------------------------------------------

class TrustMomentum:
    """
    Tracks per-source verification outcomes over time. Sources
    with sustained successful verifications earn a momentum bonus
    that lets them break above the ~70% attractor. Failures push
    momentum negative.
    """

    def __init__(self) -> None:
        self._history: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def record_outcome(self, source: str, success: bool) -> None:
        with self._lock:
            if source not in self._history:
                self._history[source] = {
                    "successes": 0, "failures": 0, "momentum": 0.0,
                }
            entry = self._history[source]

            entry["momentum"] *= MOMENTUM_DECAY_FACTOR

            if success:
                entry["successes"] += 1
                entry["momentum"] = min(
                    MOMENTUM_CAP,
                    entry["momentum"] + MOMENTUM_SUCCESS_BONUS,
                )
            else:
                entry["failures"] += 1
                entry["momentum"] = max(
                    -MOMENTUM_CAP,
                    entry["momentum"] - MOMENTUM_FAILURE_PENALTY,
                )

    def apply_natural_decay(self) -> None:
        """H1: Apply per-cycle decay so trust must be continuously earned."""
        with self._lock:
            for entry in self._history.values():
                entry["momentum"] = max(
                    -MOMENTUM_CAP,
                    entry["momentum"] - TRUST_NATURAL_DECAY,
                )

    def get_momentum(self, source: str) -> float:
        with self._lock:
            entry = self._history.get(source)
            if not entry:
                return 0.0
            return entry["momentum"]

    def get_stats(self, source: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._history.get(source)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                src: {
                    "successes": d["successes"],
                    "failures": d["failures"],
                    "momentum": round(d["momentum"], 4),
                }
                for src, d in self._history.items()
            }


_trust_momentum = TrustMomentum()


def record_verification_outcome(source: str, success: bool) -> None:
    """Public API: record whether a verification from this source passed."""
    _trust_momentum.record_outcome(source, success)


def get_trust_momentum_summary() -> Dict[str, Any]:
    return _trust_momentum.summary()


def apply_trust_decay() -> None:
    """H1: Called each meta-cycle to apply natural momentum decay."""
    _trust_momentum.apply_natural_decay()


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
    _raw_meta = item.get("metadata", {}) or {}
    meta = _raw_meta if isinstance(_raw_meta, dict) else {}

    source_score = score_source(source)
    content_score = score_content_quality(text)
    verified_bonus = 0.10 if meta.get("verified", False) else 0.0

    base = (source_score * 0.6) + (content_score * 0.4) + verified_bonus

    integrity_modifier = _get_integrity_modifier(source, text, meta)

    # Trust momentum: sustained verification success pushes above baseline
    momentum = _trust_momentum.get_momentum(source)

    raw_score = base + integrity_modifier + momentum

    # H1: cap at TRUST_CEILING to keep trust as a discriminating signal
    return max(0.0, min(TRUST_CEILING, raw_score))


def _get_integrity_modifier(source: str, text: str, meta: Dict[str, Any]) -> float:
    """
    Apply source integrity validation as a trust modifier.
    Cached per item to avoid re-validation on every score call.
    """
    cached = meta.get("_integrity_modifier")
    if cached is not None:
        return cached

    if not _SOURCE_INTEGRITY_AVAILABLE:
        return 0.0

    if not source and not text:
        return 0.0

    try:
        report = _validate_source(source, text[:2000])
        if report.get("blocked"):
            return -1.0
        return report.get("trust_modifier", 0.0)
    except Exception:
        return 0.0


# ------------------------------------------------------------
# EPISTEMIC CONFIDENCE (P2)
# ------------------------------------------------------------

class EpistemicConfidence:
    """
    Separate metric from trust score that answers: "How sure is
    Daedalus about this item?" Trust measures source reliability.
    Confidence measures epistemic certainty — corroboration,
    consistency with neighbors, and verification depth.

    An item can have high trust (from .gov source) but low confidence
    (single uncorroborated claim). Or low trust (unknown blog) but
    high confidence (5 other sources say the same thing).

    This lets trust_mean rise for well-corroborated knowledge
    without also raising trust for poorly-verified items.
    """

    CORROBORATION_WEIGHT = 0.35
    CONSISTENCY_WEIGHT = 0.30
    VERIFICATION_DEPTH_WEIGHT = 0.20
    RECENCY_WEIGHT = 0.15

    def compute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        text = item.get("text", "")
        _raw_meta = item.get("metadata", {}) or {}
        meta = _raw_meta if isinstance(_raw_meta, dict) else {}

        corroboration = self._corroboration_score(text)
        consistency = self._neighborhood_consistency(text)
        depth = self._verification_depth(meta)
        recency = self._recency_score(meta)

        weighted = (
            corroboration * self.CORROBORATION_WEIGHT
            + consistency * self.CONSISTENCY_WEIGHT
            + depth * self.VERIFICATION_DEPTH_WEIGHT
            + recency * self.RECENCY_WEIGHT
        )

        return {
            "confidence": round(max(0.0, min(1.0, weighted)), 4),
            "corroboration": round(corroboration, 4),
            "consistency": round(consistency, 4),
            "verification_depth": round(depth, 4),
            "recency": round(recency, 4),
        }

    def _corroboration_score(self, text: str) -> float:
        """How many other items say roughly the same thing?"""
        try:
            from knowledge.retrieval import search_knowledge
            neighbors = search_knowledge(text[:200], limit=5, include_superseded=False)
        except Exception:
            return 0.3

        if not neighbors:
            return 0.2

        agreeing = 0
        for n in neighbors:
            if not detect_contradiction(text, n.text):
                overlap = len(set(text.lower().split()) & set(n.text.lower().split()))
                if overlap >= 3:
                    agreeing += 1

        return min(1.0, 0.2 + agreeing * 0.2)

    def _neighborhood_consistency(self, text: str) -> float:
        """Is this item consistent with its knowledge neighborhood?"""
        try:
            from knowledge.retrieval import search_knowledge
            neighbors = search_knowledge(text[:200], limit=5, include_superseded=False)
        except Exception:
            return 0.5

        if not neighbors:
            return 0.5

        contradictions = 0
        for n in neighbors:
            if detect_contradiction(text, n.text):
                contradictions += 1

        if contradictions == 0:
            return 1.0
        return max(0.0, 1.0 - contradictions * 0.3)

    def _verification_depth(self, meta: Dict[str, Any]) -> float:
        """How deeply has this item been verified?"""
        status = meta.get("verification_status", "unknown")
        depth_map = {
            "verified": 1.0,
            "light_verified": 0.7,
            "provisional": 0.4,
            "unknown": 0.3,
            "flagged": 0.1,
        }
        return depth_map.get(status, 0.3)

    def _recency_score(self, meta: Dict[str, Any]) -> float:
        """More recently verified items get higher confidence."""
        ts = meta.get("timestamp") or meta.get("ingested_at", 0)
        if not ts:
            return 0.3
        age_sec = time.time() - ts
        age_days = age_sec / 86400
        if age_days < 7:
            return 1.0
        if age_days < 30:
            return 0.8
        if age_days < 365:
            return 0.5
        return 0.3


_epistemic_confidence = EpistemicConfidence()


def compute_epistemic_confidence(item: Dict[str, Any]) -> Dict[str, Any]:
    """Public API: compute epistemic confidence for an item."""
    return _epistemic_confidence.compute(item)


def compute_calibrated_trust(item: Dict[str, Any]) -> float:
    """
    Combined trust+confidence score. Uses the geometric mean so
    that both trust AND confidence must be high for the combined
    score to be high. A .gov item with no corroboration scores
    lower than a .gov item with 3 corroborating sources.

    This raises the effective trust mean for well-known facts
    without also raising it for dubious-but-sourced claims.
    """
    trust = compute_trust_score(item)
    confidence = _epistemic_confidence.compute(item)["confidence"]
    return (trust * confidence) ** 0.5


def batch_calibrate_trust(sample_cap: int = 500) -> Dict[str, Any]:
    """
    Batch calibration sweep: sample items from the KB and compute
    calibrated trust.  Returns metrics showing how many items have
    calibrated trust significantly above their raw score.

    This is a **read-only diagnostic** — it does not mutate items.
    Trust scores are derived live by ``compute_trust_score`` /
    ``compute_calibrated_trust``; injecting boosts into metadata
    would create a divergent trust source.
    """
    import random as _rnd

    reservoir: list = []
    count = 0
    for item in _iter_items():
        count += 1
        if count <= sample_cap:
            reservoir.append(item)
        else:
            j = _rnd.randint(0, count - 1)
            if j < sample_cap:
                reservoir[j] = item

    calibrated = 0
    boosted = 0
    for item in reservoir:
        try:
            raw_trust = compute_trust_score(item)
            cal_trust = compute_calibrated_trust(item)
            calibrated += 1
            if cal_trust > raw_trust + 0.05:
                boosted += 1
        except Exception:
            continue

    return {
        "sampled": len(reservoir),
        "calibrated": calibrated,
        "boosted": boosted,
        "total_items": count,
        "coverage_pct": round(calibrated / max(count, 1) * 100, 2),
    }


# ------------------------------------------------------------
# CONTRADICTION DETECTION
# ------------------------------------------------------------

def detect_contradiction(text_a: str, text_b: str) -> bool:
    a = text_a.lower()
    b = text_b.lower()

    negations = ["not", "never", "no ", "false", "incorrect"]

    a_has_neg = any(n in a for n in negations)
    b_has_neg = any(n in b for n in negations)

    overlap = len(set(a.split()) & set(b.split()))

    if a_has_neg != b_has_neg and overlap >= 5:
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
        old_id = item.get("id", "")
        if not old_id:
            continue
        old_text = item.get("text", "")
        old_hash = _hash_text(old_text)

        if new_hash == old_hash:
            return old_id

        if old_text[:100] == new_text[:100]:
            if should_replace(item, new_text):
                return replace_item_from_text(
                    old_id=old_id,
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
