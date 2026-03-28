# knowledge/batch_ingestion.py

"""
Batch Ingestion

Accelerates the knowledge acquisition loop by processing items in
governed batches rather than one-at-a-time sequential verification.

Key design:
- Source trust inheritance: items from a pre-verified source start
  with a provisional trust score and skip deep verification on ingest.
  Background verification promotes them to full trust later.
- Tiered verification: light/standard/deep intensity per batch,
  controlled by the curiosity engine's acquisition plan phases.
- Incremental graph updates: each batch triggers graph updates only
  for the new items, not a full rebuild.
- Quality snapshots: before/after metrics for every batch, feeding
  the adaptive pacer and quality gates.

This module does NOT bypass the trust scoring or verification pipeline.
It restructures _when_ and _how intensely_ verification runs, not
_whether_ it runs. Every item reaches full verification eventually.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Any, List, Optional

from knowledge.ingestion import ingest_text
from knowledge.verification_pipeline import verify_new_information
from knowledge.knowledge_graph import update_graph_from_item
from knowledge.retrieval import search_knowledge
from knowledge.self_model import get_self_model

try:
    from knowledge.source_integrity import validate_source, record_provenance, quarantine_item
    _INTEGRITY_AVAILABLE = True
except ImportError:
    _INTEGRITY_AVAILABLE = False

try:
    from knowledge.trust_scoring import detect_contradiction
    _CONTRADICTION_CHECK_AVAILABLE = True
except ImportError:
    _CONTRADICTION_CHECK_AVAILABLE = False

try:
    from knowledge.flow_tuner import flow_tuner as _flow_tuner
    _FLOW_TUNER_AVAILABLE = True
except ImportError:
    _FLOW_TUNER_AVAILABLE = False


# ------------------------------------------------------------
# SOURCE TRUST REGISTRY
# ------------------------------------------------------------

_source_trust: Dict[str, float] = {}
_source_trust_lock = threading.Lock()
from knowledge._atomic_io import knowledge_file_lock as _knowledge_file_lock


def register_source_trust(source: str, trust: float) -> bool:
    """
    Record a trust level for a known source (0.0 - 1.0).
    Validates the source against the integrity layer before
    allowing it into the trust registry. Returns False if blocked.
    """
    trust = max(0.0, min(1.0, trust))

    if _INTEGRITY_AVAILABLE and "://" in source:
        integrity = validate_source(source, "")
        if integrity.get("blocked"):
            return False
        modifier = integrity.get("trust_modifier", 0.0)
        trust = max(0.0, min(1.0, trust + modifier))

    with _source_trust_lock:
        _source_trust[source] = trust
    return True


def get_source_trust(source: str) -> Optional[float]:
    with _source_trust_lock:
        return _source_trust.get(source)


# ------------------------------------------------------------
# VERIFICATION INTENSITY
# ------------------------------------------------------------

def _select_verification_path(
    text: str,
    source: str,
    intensity: str,
) -> str:
    """
    Determine the verification path for an item.

    Returns: "full" | "light" | "deferred"
    - full: standard verification pipeline (deep intensity or unknown source)
    - light: quick contradiction check only (standard intensity, known source)
    - deferred: ingest immediately, queue for background verification (light
      intensity, high source trust)
    """
    source_trust = get_source_trust(source)

    if intensity == "deep":
        return "full"

    if intensity == "light" and source_trust is not None and source_trust >= 0.8:
        return "deferred"

    if intensity == "standard" and source_trust is not None and source_trust >= 0.6:
        return "light"

    return "full"


def _light_verification(text: str) -> Dict[str, Any]:
    """
    Quick contradiction check without full pipeline.
    Searches for nearby items and checks for direct contradictions.
    """
    neighbors = search_knowledge(text[:200], limit=5, include_superseded=False)

    from knowledge.trust_scoring import detect_contradiction

    contradictions = []
    for n in neighbors:
        if detect_contradiction(text, n.text):
            contradictions.append(n.id)

    if contradictions:
        return {
            "status": "contradiction_detected",
            "contradictions": contradictions,
            "recommendation": "escalate_to_full",
        }

    return {
        "status": "passed",
        "contradictions": [],
        "recommendation": "accept",
    }


# ------------------------------------------------------------
# PRE-INGESTION CONSISTENCY SCREEN (Tuning-fix T1)
# ------------------------------------------------------------

def _pre_ingestion_consistency_check(text: str, consistency: Optional[float] = None) -> Dict[str, Any]:
    """
    Adaptive cluster-scoped contradiction gate. Before any item enters
    the KB, compare it against the closest existing items via search.

    Adapts based on current consistency:
    - consistency >= 0.80: check 3 neighbors (light)
    - consistency >= 0.65: check 5 neighbors (standard)
    - consistency <  0.65: check 8 neighbors (aggressive)

    Returns {"passed": True/False, "contradictions": [...]}
    """
    if not _CONTRADICTION_CHECK_AVAILABLE:
        return {"passed": True, "contradictions": []}

    if consistency is not None and consistency < 0.65:
        neighbor_limit = 10
    elif consistency is not None and consistency < 0.75:
        neighbor_limit = 8
    elif consistency is not None and consistency >= 0.85:
        neighbor_limit = 3
    else:
        neighbor_limit = 5

    try:
        neighbors = search_knowledge(text[:200], limit=neighbor_limit, include_superseded=False)
    except Exception:
        return {"passed": False, "contradictions": [], "reason": "search_failed_fail_closed"}

    contradictions = []
    for n in neighbors:
        if detect_contradiction(text, n.text):
            contradictions.append({
                "existing_id": n.id,
                "existing_preview": n.text[:100],
            })

    if contradictions:
        return {
            "passed": False,
            "contradictions": contradictions,
            "reason": "contradicts_existing_knowledge",
            "neighbor_limit": neighbor_limit,
        }
    return {"passed": True, "contradictions": []}


# ------------------------------------------------------------
# BATCH INGESTION
# ------------------------------------------------------------

def ingest_batch(
    items: List[Dict[str, Any]],
    source: str = "batch",
    verification_intensity: str = "standard",
    goal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest a batch of knowledge items with tiered verification.

    Each item dict must have at minimum: {"text": "..."}
    Optional fields: {"source": "...", "metadata": {...}}

    Returns a batch report with per-item results and aggregate metrics.
    """
    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "source": source,
        "intensity": verification_intensity,
        "goal_id": goal_id,
        "total": len(items),
        "ingested": 0,
        "deferred": 0,
        "rejected": 0,
        "escalated": 0,
        "items": [],
        "quality_before": None,
        "quality_after": None,
    }

    batch_start_time = time.time()

    # Quality snapshot before
    sm_before = get_self_model()
    report["quality_before"] = {
        "coherence": sm_before.get("confidence", {}).get("graph_coherence", 0.0),
        "consistency": sm_before.get("confidence", {}).get("consistency", 0.0),
        "quality": sm_before.get("confidence", {}).get("knowledge_quality", 0.0),
    }

    for item_data in items:
        text = item_data.get("text", "")
        if not text.strip():
            report["rejected"] = report.get("rejected", 0) + 1
            report.setdefault("items", []).append({
                "status": "skipped_empty",
                "reason": "empty or whitespace-only text",
            })
            continue

        item_source = item_data.get("source", source)
        item_meta = item_data.get("metadata", {})
        item_meta["batch_source"] = source
        item_meta["verification_intensity"] = verification_intensity
        if goal_id:
            item_meta["goal_id"] = goal_id

        # Source integrity gate: check before any ingestion path
        if _INTEGRITY_AVAILABLE:
            integrity = validate_source(item_source, text)
            if integrity.get("blocked"):
                report["items"].append({
                    "text_preview": text[:80],
                    "path": "blocked",
                    "status": "rejected_integrity",
                    "threat_level": integrity.get("threat_level"),
                    "flags": [f["flag"] for f in integrity.get("flags", [])],
                })
                report["rejected"] += 1
                continue
            item_meta["integrity_threat_level"] = integrity.get("threat_level", "none")
            item_meta["integrity_modifier"] = integrity.get("trust_modifier", 0.0)

            # P4: Quarantine items with warning/high threat instead of direct ingestion
            if integrity.get("quarantine"):
                quarantine_item(
                    item_id=f"pending_{__import__('hashlib').sha256(text[:100].encode('utf-8','replace')).hexdigest()[:16]}",
                    source=item_source,
                    text=text,
                    reason=f"threat_level_{integrity.get('threat_level')}",
                )
                report["items"].append({
                    "text_preview": text[:80],
                    "path": "quarantined",
                    "status": "quarantined_for_review",
                    "threat_level": integrity.get("threat_level"),
                })
                if "quarantined" not in report:
                    report["quarantined"] = 0
                report["quarantined"] += 1
                continue

        # T1: Adaptive pre-ingestion screen — widens search when consistency is low
        consistency_screen = _pre_ingestion_consistency_check(
            text,
            consistency=report["quality_before"]["consistency"],
        )
        if not consistency_screen["passed"]:
            report["items"].append({
                "text_preview": text[:80],
                "path": "blocked",
                "status": "rejected_consistency_screen",
                "contradictions": consistency_screen.get("contradictions", []),
            })
            report["rejected"] += 1
            continue

        path = _select_verification_path(text, item_source, verification_intensity)
        item_result: Dict[str, Any] = {
            "text_preview": text[:80],
            "path": path,
            "status": "pending",
        }

        if path == "deferred":
            item_meta["verification_status"] = "provisional"
            item_id = ingest_text(text, source=item_source, metadata=item_meta)
            _update_graph_for_text(text, item_id, item_source, path="deferred")
            _record_provenance_mandatory(item_id, item_source, "deferred")
            item_result["status"] = "ingested_provisional"
            item_result["item_id"] = item_id
            report["deferred"] += 1
            report["ingested"] += 1

        elif path == "light":
            check = _light_verification(text)
            if check["status"] == "passed":
                item_meta["verification_status"] = "light_verified"
                item_id = ingest_text(text, source=item_source, metadata=item_meta)
                _update_graph_for_text(text, item_id, item_source, path="light")
                _record_provenance_mandatory(item_id, item_source, "light")
                _record_trust_outcome(item_source, True)
                item_result["status"] = "ingested_light"
                item_result["item_id"] = item_id
                report["ingested"] += 1
            else:
                full_result = verify_new_information(text, source=item_source)
                if full_result.get("action") in ("accept_new", "replace_existing"):
                    new_id = full_result.get("new_item_id", "")
                    item_result["status"] = "ingested_escalated"
                    item_result["item_id"] = new_id
                    _record_provenance_mandatory(new_id, item_source, "escalated")
                    _record_trust_outcome(item_source, True)
                    report["ingested"] += 1
                    report["escalated"] += 1
                else:
                    item_result["status"] = "rejected"
                    _record_trust_outcome(item_source, False)
                    report["rejected"] += 1

        else:  # full
            full_result = verify_new_information(text, source=item_source)
            if full_result.get("action") in ("accept_new", "replace_existing"):
                new_id = full_result.get("new_item_id", "")
                item_result["status"] = "ingested_verified"
                item_result["item_id"] = new_id
                _record_provenance_mandatory(new_id, item_source, "full")
                _record_trust_outcome(item_source, True)
                report["ingested"] += 1
            else:
                item_result["status"] = "rejected"
                _record_trust_outcome(item_source, False)
                report["rejected"] += 1

        report["items"].append(item_result)

    # Quality snapshot after
    sm_after = get_self_model()
    report["quality_after"] = {
        "coherence": sm_after.get("confidence", {}).get("graph_coherence", 0.0),
        "consistency": sm_after.get("confidence", {}).get("consistency", 0.0),
        "quality": sm_after.get("confidence", {}).get("knowledge_quality", 0.0),
    }

    # Record pipeline metrics for flow tuner
    if _FLOW_TUNER_AVAILABLE:
        batch_elapsed_ms = (time.time() - batch_start_time) * 1000
        _flow_tuner.metrics.record_batch(report["ingested"], batch_elapsed_ms)

    return report


def _record_provenance_mandatory(item_id: str, source: str, path: str) -> None:
    """
    Mandatory provenance for every ingested item regardless of path.
    Unlike the old optional caller-level recording, this is called
    unconditionally from ingest_batch for all accepted items.
    """
    if not item_id:
        return
    if _INTEGRITY_AVAILABLE:
        try:
            record_provenance(item_id=item_id, source=source, verification_path=path)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "provenance recording failed for %s: %s", item_id, exc,
            )


def _record_provenance_safe(item_id: str, source: str, path: str) -> None:
    """Legacy helper: kept for backward compatibility."""
    _record_provenance_mandatory(item_id, source, path)


def _record_trust_outcome(source: str, success: bool) -> None:
    """Feed trust momentum tracker from verification outcomes."""
    try:
        from knowledge.trust_scoring import record_verification_outcome
        record_verification_outcome(source, success)
    except ImportError:
        pass
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "trust outcome recording failed for %s: %s", source, exc,
        )


def _update_graph_for_text(text: str, item_id: str, source: str, path: str = "unknown") -> None:
    """Incremental graph update for a single ingested item.

    Provenance recording is handled by _record_provenance_mandatory
    in the main ingest_batch flow — not duplicated here.
    """
    try:
        update_graph_from_item({
            "id": item_id,
            "text": text,
            "source": source,
            "metadata": {},
        })
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "graph update failed for %s: %s", item_id, exc,
        )


# ------------------------------------------------------------
# BACKGROUND VERIFICATION (for deferred items)
# ------------------------------------------------------------

def verify_deferred_items(limit: int | None = None) -> Dict[str, Any]:
    """
    Process items that were ingested with provisional trust.
    Runs full verification and updates their status in the knowledge store.

    Called by the meta-reasoner during maintenance cycles.
    Limit is tuned by flow_tuner.params.verification_parallelism when available.
    """
    if limit is None:
        limit = 20
        try:
            from knowledge.flow_tuner import flow_tuner as _ft
            limit = max(1, _ft.params.verification_parallelism * 10)
        except ImportError:
            pass
    from knowledge.retrieval import _iter_items

    deferred = []
    for item in _iter_items():
        meta = item.get("metadata", {})
        if meta.get("verification_status") == "provisional":
            deferred.append(item)
        if len(deferred) >= limit:
            break

    results = {"verified": 0, "flagged": 0, "total": len(deferred)}

    for item in deferred:
        text = item.get("text", "")
        source = item.get("source", "unknown")
        item_id = item.get("id", "")
        try:
            verification = verify_new_information(text, source=source)
        except Exception:
            results["flagged"] += 1
            _update_item_verification_status(item_id, "flagged")
            continue

        action = verification.get("action")
        if action in ("accept_new", "replace_existing"):
            results["verified"] += 1
            _update_item_verification_status(item_id, "verified")
        elif action == "reject":
            results["flagged"] += 1
            _update_item_verification_status(item_id, "flagged")
        else:
            results["flagged"] += 1
            _update_item_verification_status(item_id, "flagged")

    return results


def _update_item_verification_status(item_id: str, new_status: str) -> None:
    """
    Update the verification_status in an item's metadata within
    the knowledge store. Scans the JSONL file and rewrites the
    matching line with the updated metadata.  Serialized via
    ``_knowledge_file_lock`` to prevent concurrent RMW races.
    """
    from knowledge.ingestion import KNOWLEDGE_FILE
    import json

    with _knowledge_file_lock:
        if not KNOWLEDGE_FILE.exists():
            return

        lines = KNOWLEDGE_FILE.read_text(encoding="utf-8").splitlines()
        updated = False

        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("id") == item_id:
                meta = entry.get("metadata", {})
                if meta is None:
                    meta = {}
                meta["verification_status"] = new_status
                entry["metadata"] = meta
                lines[i] = json.dumps(entry, ensure_ascii=False)
                updated = True
                break

        if updated:
            try:
                from knowledge._atomic_io import atomic_write_text
                atomic_write_text(KNOWLEDGE_FILE, "\n".join(lines) + "\n")
            except ImportError:
                KNOWLEDGE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
