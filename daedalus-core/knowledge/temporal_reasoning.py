# knowledge/temporal_reasoning.py

"""
Temporal Reasoning Layer

Makes the knowledge base time-aware. Facts have validity windows,
obsolescence is detected automatically, and contradictions are
evaluated in temporal context.

Architecture fit:
- Hooks into batch_ingestion for temporal annotation on ingest
- Hooks into consistency_checker for temporal conflict awareness
- Hooks into retrieval for temporal filtering
- Periodic maintenance sweeps for obsolescence detection
- Uses LLM adapter when available for richer temporal extraction

All items without temporal metadata are treated as temporal_type="unknown"
and considered perpetually valid — no existing behavior changes.
"""

from __future__ import annotations

import re
import time
from typing import Dict, Any, List, Optional

# Temporal type constants
TEMPORAL_PERMANENT = "permanent"    # Laws of physics, definitions
TEMPORAL_BOUNDED = "time-bounded"   # Valid for a specific period
TEMPORAL_EVENT = "event"            # Happened at a specific time
TEMPORAL_UNKNOWN = "unknown"        # No temporal metadata (default)

# Heuristic patterns for temporal extraction
_YEAR_PATTERN = re.compile(r'\b(1[0-9]{3}|2[0-9]{3})\b')
_DATE_PATTERN = re.compile(
    r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
)
_TEMPORAL_KEYWORDS = {
    TEMPORAL_PERMANENT: ["always", "law of", "definition", "axiom", "constant",
                         "fundamental", "invariant", "universal"],
    TEMPORAL_EVENT: ["happened", "occurred", "was discovered", "was founded",
                     "was born", "died", "launched", "released", "announced"],
    TEMPORAL_BOUNDED: ["until", "from.*to", "during", "between", "as of",
                       "effective", "expires", "valid through", "current as of"],
}


# ------------------------------------------------------------
# TEMPORAL ANNOTATION
# ------------------------------------------------------------

def annotate_temporal(
    text: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract or infer temporal bounds from text content.
    Uses heuristic analysis; falls back to LLM when available.

    Returns metadata dict with temporal fields added:
    - temporal_type: str
    - valid_from: Optional[float] (epoch)
    - valid_until: Optional[float] (epoch or None)
    - temporal_confidence: float (0-1)
    """
    meta = dict(metadata) if metadata else {}
    result = _heuristic_temporal_analysis(text)

    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            llm_result = _llm_temporal_analysis(text, llm_adapter)
            if llm_result.get("confidence", 0) > result.get("confidence", 0):
                result = llm_result
    except ImportError:
        pass

    meta["temporal_type"] = result.get("temporal_type", TEMPORAL_UNKNOWN)
    meta["temporal_confidence"] = result.get("confidence", 0.0)

    if result.get("valid_from") is not None:
        meta["valid_from"] = result["valid_from"]
    if result.get("valid_until") is not None:
        meta["valid_until"] = result["valid_until"]

    return meta


def _heuristic_temporal_analysis(text: str) -> Dict[str, Any]:
    """Classify temporal type using keyword and pattern matching."""
    text_lower = text.lower()
    scores = {TEMPORAL_PERMANENT: 0.0, TEMPORAL_EVENT: 0.0, TEMPORAL_BOUNDED: 0.0}

    for ttype, keywords in _TEMPORAL_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                scores[ttype] += 1.0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {"temporal_type": TEMPORAL_UNKNOWN, "confidence": 0.1}

    confidence = min(0.8, 0.3 + best_score * 0.15)

    result: Dict[str, Any] = {
        "temporal_type": best_type,
        "confidence": confidence,
    }

    years = _YEAR_PATTERN.findall(text)
    if years:
        year_ints = sorted(int(y) for y in years)
        if best_type == TEMPORAL_EVENT and year_ints:
            result["valid_from"] = _year_to_epoch(year_ints[0])
            result["valid_until"] = result["valid_from"]
        elif best_type == TEMPORAL_BOUNDED and len(year_ints) >= 2:
            result["valid_from"] = _year_to_epoch(year_ints[0])
            result["valid_until"] = _year_to_epoch(year_ints[-1])

    return result


def _llm_temporal_analysis(text: str, adapter: Any) -> Dict[str, Any]:
    """Use LLM for richer temporal classification."""
    prompt = (
        f"Classify the temporal nature of this text. "
        f"Reply with exactly one of: permanent, time-bounded, event, unknown. "
        f"Then on a new line, any year references.\n\n"
        f"Text: {text[:500]}"
    )
    try:
        response = adapter.complete(prompt, max_tokens=64, temperature=0.1)
        lines = response.strip().split("\n")
        ttype = lines[0].strip().lower()
        if ttype in ("permanent", "time-bounded", "event", "unknown"):
            return {
                "temporal_type": ttype if ttype != "time-bounded" else TEMPORAL_BOUNDED,
                "confidence": 0.85,
            }
    except Exception:
        pass
    return {"temporal_type": TEMPORAL_UNKNOWN, "confidence": 0.0}


def _year_to_epoch(year: int) -> float:
    """Convert a year integer to approximate epoch timestamp."""
    import calendar
    try:
        return float(calendar.timegm((year, 1, 1, 0, 0, 0, 0, 0, 0)))
    except (ValueError, OverflowError):
        return 0.0


# ------------------------------------------------------------
# TEMPORAL VALIDITY
# ------------------------------------------------------------

def check_temporal_validity(
    item: Dict[str, Any],
    reference_time: Optional[float] = None,
) -> bool:
    """
    Check if a knowledge item is temporally valid at the given time.
    Items without temporal metadata are always considered valid.
    """
    meta = item.get("metadata", {})
    if not isinstance(meta, dict):
        return True

    ttype = meta.get("temporal_type", TEMPORAL_UNKNOWN)
    if ttype in (TEMPORAL_UNKNOWN, TEMPORAL_PERMANENT):
        return True

    ref = reference_time or time.time()

    valid_from = meta.get("valid_from")
    valid_until = meta.get("valid_until")

    if valid_from is not None and ref < valid_from:
        return False
    if valid_until is not None and ref > valid_until:
        return False

    return True


# ------------------------------------------------------------
# TEMPORAL CONFLICT DETECTION
# ------------------------------------------------------------

def find_temporal_conflicts(
    text: str,
    timestamp: Optional[float] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Find KB items that potentially contradict the given text at a
    specific point in time. Temporal awareness means two facts about
    the same entity at different times are NOT contradictions.
    """
    try:
        from knowledge.retrieval import search_knowledge
        from knowledge.trust_scoring import detect_contradiction
    except ImportError:
        return []

    ref_time = timestamp or time.time()
    neighbors = search_knowledge(text[:400], limit=limit * 2)
    conflicts = []

    for item in neighbors:
        item_dict = {
            "text": item.text,
            "metadata": item.metadata,
            "source": item.source,
            "id": item.id,
        }

        if not check_temporal_validity(item_dict, ref_time):
            continue

        try:
            if detect_contradiction(text, item.text):
                conflicts.append({
                    "item_id": item.id,
                    "text_preview": item.text[:200],
                    "temporal_type": item.metadata.get("temporal_type", TEMPORAL_UNKNOWN)
                        if isinstance(item.metadata, dict) else TEMPORAL_UNKNOWN,
                    "conflict_type": "temporal_aware",
                })
        except Exception:
            continue

    return conflicts[:limit]


# ------------------------------------------------------------
# TEMPORAL CHAINS
# ------------------------------------------------------------

def temporal_chain(entity: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Build an ordered sequence of temporal facts about an entity.
    Returns items sorted by valid_from timestamp.
    """
    try:
        from knowledge.retrieval import search_knowledge
    except ImportError:
        return []

    results = search_knowledge(entity, limit=limit)
    temporal_items = []

    for item in results:
        meta = item.metadata if isinstance(item.metadata, dict) else {}
        valid_from = meta.get("valid_from")
        if valid_from is not None:
            temporal_items.append({
                "item_id": item.id,
                "text_preview": item.text[:200],
                "valid_from": valid_from,
                "valid_until": meta.get("valid_until"),
                "temporal_type": meta.get("temporal_type", TEMPORAL_UNKNOWN),
            })

    temporal_items.sort(key=lambda x: x["valid_from"])
    return temporal_items


# ------------------------------------------------------------
# OBSOLESCENCE DETECTION
# ------------------------------------------------------------

def detect_obsolescence(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Scan for items that have been superseded by newer information.
    An item is obsolete if a newer item about the same entity
    contradicts it AND the newer item has a later valid_from.
    """
    try:
        from knowledge.retrieval import search_knowledge, _iter_items
        from knowledge.trust_scoring import detect_contradiction
    except ImportError:
        return []

    obsolete = []
    checked = 0

    for item in _iter_items():
        if checked >= limit:
            break

        meta = item.get("metadata", {})
        if not isinstance(meta, dict):
            continue

        ttype = meta.get("temporal_type", TEMPORAL_UNKNOWN)
        if ttype == TEMPORAL_PERMANENT:
            continue

        valid_from = meta.get("valid_from", 0)
        text = item.get("text", "")
        if not text:
            continue

        checked += 1
        neighbors = search_knowledge(text[:300], limit=5)

        for neighbor in neighbors:
            n_meta = neighbor.metadata if isinstance(neighbor.metadata, dict) else {}
            n_from = n_meta.get("valid_from", 0)

            if n_from > valid_from:
                try:
                    if detect_contradiction(text, neighbor.text):
                        obsolete.append({
                            "item_id": item.get("id", ""),
                            "text_preview": text[:200],
                            "superseded_by": neighbor.id,
                            "age_gap": n_from - valid_from,
                        })
                        break
                except Exception:
                    continue

    return obsolete


# ------------------------------------------------------------
# PERIODIC MAINTENANCE
# ------------------------------------------------------------

def run_temporal_maintenance(
    obsolescence_limit: int = 50,
) -> Dict[str, Any]:
    """
    Periodic sweep: detect obsolete items and surface them for
    review. Does NOT auto-delete — returns findings for the
    consistency checker or operator to act on.
    """
    obsolete = detect_obsolescence(limit=obsolescence_limit)

    return {
        "action": "temporal_maintenance",
        "timestamp": time.time(),
        "obsolete_found": len(obsolete),
        "obsolete_items": obsolete[:20],
    }
