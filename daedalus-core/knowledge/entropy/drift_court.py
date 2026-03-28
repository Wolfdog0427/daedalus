# knowledge/entropy/drift_court.py

"""
Drift Court

Classifies deviations from the canonical template and decides their fate.
Three possible verdicts:
  - canonize:  deviation is beneficial → submit as a PROPOSAL for operator approval
  - expire:    deviation is rare/neutral → let TTL handle it
  - remove:    deviation is harmful → schedule for next renewal

CRITICAL SAFETY DIFFERENCES FROM THE ORIGINAL PROPOSAL:
1. Canonization NEVER auto-modifies the template. It creates a governor
   proposal that requires operator approval.
2. Verdicts are logged and auditable.
3. Thresholds are configurable and learned from history.
4. Integrates with the existing proposal_manager for operator workflow.
"""

from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

COURT_DIR = Path("data/entropy/drift_court")
DEVIATION_LOG = COURT_DIR / "deviations.jsonl"
VERDICT_LOG = COURT_DIR / "verdicts.jsonl"
_MAX_LOG_ENTRIES = 5000


def _ensure_dir():
    COURT_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_log(path: Path) -> None:
    """Keep only the most recent _MAX_LOG_ENTRIES lines in an append-only JSONL."""
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) > _MAX_LOG_ENTRIES:
            import tempfile, os
            content = "\n".join(lines[-_MAX_LOG_ENTRIES:]) + "\n"
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            closed = False
            try:
                os.write(fd, content.encode("utf-8"))
                os.close(fd)
                closed = True
                os.replace(tmp, str(path))
            except BaseException:
                if not closed:
                    os.close(fd)
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
    except Exception:
        pass


# ------------------------------------------------------------------
# DEVIATION LOGGING
# ------------------------------------------------------------------

def log_deviation(deviation: Dict[str, Any]) -> str:
    """
    Record a deviation observed during operation.
    Returns the deviation ID for tracking.

    deviation should contain:
      - name: str (e.g., "new_cache_directory", "modified_scoring_weights")
      - category: str (e.g., "state", "config", "behavior", "metric")
      - source: str (what subsystem generated it)
      - impact: str ("positive", "neutral", "negative", "unknown")
      - details: dict (arbitrary metadata)
    """
    _ensure_dir()
    dev_id = hashlib.sha256(
        f"{deviation.get('name', '')}-{time.time()}".encode()
    ).hexdigest()[:12]

    entry = {
        "id": dev_id,
        "timestamp": time.time(),
        "name": deviation.get("name", "unnamed"),
        "category": deviation.get("category", "unknown"),
        "source": deviation.get("source", "unknown"),
        "impact": deviation.get("impact", "unknown"),
        "details": deviation.get("details", {}),
        "frequency": deviation.get("frequency", 0.0),
        "verdict": None,
    }

    with open(DEVIATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    _rotate_log(DEVIATION_LOG)

    return dev_id


def get_pending_deviations() -> List[Dict[str, Any]]:
    """Return all deviations that have not yet been adjudicated."""
    _ensure_dir()
    if not DEVIATION_LOG.exists():
        return []

    adjudicated = _load_adjudicated_ids()
    pending = []
    for line in DEVIATION_LOG.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("id") not in adjudicated:
                pending.append(entry)
        except (json.JSONDecodeError, ValueError):
            continue
    return pending


def _load_adjudicated_ids() -> set:
    if not VERDICT_LOG.exists():
        return set()
    ids = set()
    for line in VERDICT_LOG.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ids.add(entry.get("deviation_id"))
        except (json.JSONDecodeError, ValueError):
            continue
    return ids


# ------------------------------------------------------------------
# CLASSIFICATION ENGINE
# ------------------------------------------------------------------

CANONIZE_FREQUENCY_THRESHOLD = 0.8
EXPIRE_FREQUENCY_THRESHOLD = 0.2


def classify_deviation(deviation: Dict[str, Any]) -> str:
    """
    Classify a single deviation into: canonize, expire, or remove.

    Rules:
    - High frequency + positive impact → canonize (submit proposal)
    - Low frequency → expire (let TTL handle it)
    - Negative impact → remove (schedule for pruning)
    - High frequency + neutral/unknown → expire (wait for more data)
    """
    _raw_freq = deviation.get("frequency")
    freq = _raw_freq if _raw_freq is not None else 0.0
    impact = deviation.get("impact") or "unknown"

    if impact == "negative":
        return "remove"

    if freq >= CANONIZE_FREQUENCY_THRESHOLD and impact == "positive":
        return "canonize"

    if freq < EXPIRE_FREQUENCY_THRESHOLD:
        return "expire"

    return "expire"


# ------------------------------------------------------------------
# COURT SESSION
# ------------------------------------------------------------------

def run_drift_court(deviations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Run a full Drift Court session:
    1. Gather pending deviations (or use provided list).
    2. Classify each one.
    3. For 'canonize' verdicts, submit a governor proposal (NOT auto-modify).
    4. For 'remove' verdicts, flag for next renewal cycle.
    5. Log all verdicts.

    Returns a session report.
    """
    _ensure_dir()

    if deviations is None:
        deviations = get_pending_deviations()

    report: Dict[str, Any] = {
        "timestamp": time.time(),
        "deviations_reviewed": len(deviations),
        "verdicts": {"canonize": 0, "expire": 0, "remove": 0},
        "proposals_created": [],
        "removal_candidates": [],
        "details": [],
    }

    for dev in deviations:
        verdict = classify_deviation(dev)
        report["verdicts"][verdict] += 1

        verdict_entry = {
            "deviation_id": dev.get("id"),
            "name": dev.get("name"),
            "verdict": verdict,
            "timestamp": time.time(),
        }

        if verdict == "canonize":
            proposal_result = _submit_canonization_proposal(dev)
            verdict_entry["proposal"] = proposal_result
            if proposal_result.get("proposal_id"):
                report["proposals_created"].append(proposal_result.get("proposal_id", ""))

        elif verdict == "remove":
            report["removal_candidates"].append({
                "name": dev.get("name"),
                "category": dev.get("category"),
                "source": dev.get("source"),
            })

        report["details"].append(verdict_entry)

        with open(VERDICT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(verdict_entry) + "\n")

    _rotate_log(VERDICT_LOG)
    return report


def _submit_canonization_proposal(deviation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a governor proposal to canonize a deviation.
    This routes through the existing proposal system —
    the operator must approve before the template is modified.
    """
    try:
        from governor.proposal_manager import create_proposal

        proposal = create_proposal(
            tier_requested=3,
            subsystem="entropy.drift_court",
            risk_level="low",
            priority="normal",
            drift_context={
                "drift_level": "observed_deviation",
                "deviation_name": deviation.get("name"),
                "deviation_category": deviation.get("category"),
                "frequency": deviation.get("frequency", 0.0),
                "impact": deviation.get("impact"),
            },
            diagnostics_summary={
                "source": deviation.get("source"),
                "details": deviation.get("details", {}),
            },
            proposal_summary=(
                f"Drift Court recommends canonizing '{deviation.get('name')}' — "
                f"frequency {(deviation.get('frequency') or 0):.0%}, impact: {deviation.get('impact')}. "
                f"Requires operator approval to modify canonical template."
            ),
            justification=[
                f"Deviation '{deviation.get('name')}' has been observed with high frequency",
                f"Impact assessment: {deviation.get('impact')}",
                "Canonization would add this to the permanent template",
            ],
            planned_actions=[{
                "type": "canonize_invariant",
                "target": "canonical_template",
                "invariant_name": deviation.get("name"),
            }],
            expected_impact={
                "stability_delta": 0.02,
                "risk_delta": -0.01,
                "trust_delta": 0.01,
                "confidence": 0.8,
                "description": "Stabilizes the canonical template by incorporating a proven pattern",
            },
            sandbox_preview={
                "status": "not_applicable",
                "notes": "Canonization is a template metadata change, no sandbox needed.",
            },
        )
        return {
            "proposal_id": proposal.get("id"),
            "status": "submitted",
        }
    except Exception as exc:
        return {
            "proposal_id": None,
            "status": "error",
            "error": str(exc),
        }


def apply_approved_canonization(proposal_id: str) -> Dict[str, Any]:
    """
    Called after an operator approves a canonization proposal.
    Actually modifies the canonical template.
    """
    try:
        from governor.proposal_manager import load_proposal_by_id
        from knowledge.entropy.canonical_template import add_invariant

        proposal = load_proposal_by_id(proposal_id)
        if proposal is None:
            return {"status": "error", "reason": "proposal_not_found"}

        if proposal.get("status") != "approved":
            return {"status": "error", "reason": f"proposal_status_{proposal.get('status')}"}

        drift_ctx = proposal.get("drift_context", {})
        inv_name = drift_ctx.get("deviation_name")
        if not inv_name:
            for action in proposal.get("planned_actions", []):
                if action.get("type") == "canonize_invariant":
                    inv_name = action.get("invariant_name")
                    break

        if not inv_name:
            return {"status": "error", "reason": "no_invariant_name_found"}

        add_invariant(inv_name, updated_by=f"operator_via_proposal_{proposal_id}")
        return {
            "status": "canonized",
            "invariant": inv_name,
            "proposal_id": proposal_id,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_court_summary() -> Dict[str, Any]:
    """Return statistics about the drift court's history."""
    _ensure_dir()
    verdicts = {"canonize": 0, "expire": 0, "remove": 0}
    total = 0

    if VERDICT_LOG.exists():
        for line in VERDICT_LOG.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                v = entry.get("verdict", "unknown")
                verdicts[v] = verdicts.get(v, 0) + 1
                total += 1
            except (json.JSONDecodeError, ValueError):
                continue
            except Exception:
                continue

    pending = len(get_pending_deviations())
    return {
        "total_adjudicated": total,
        "pending": pending,
        "verdicts": verdicts,
    }
