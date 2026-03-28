# governance/proposal_engine.py
"""
Governance proposal engine for Daedalus.

Generates, scores, and classifies governance proposals based on drift
detection, diagnostics, stability signals, coherence signals, and
operator requests.  Never auto-executes — all proposals require
operator review.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import Any, Dict, List, Optional

_PROPOSALS: List[Dict[str, Any]] = []
_MAX_PROPOSALS = 100
_proposal_counter = itertools.count(1)
_proposal_lock = threading.Lock()


def generate_proposal(
    title: str,
    description: str,
    change_type: str,
    target: str = "",
    flags: List[str] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate a new governance proposal.

    Does NOT apply the change — only creates a scored, classified
    proposal for operator review.
    """
    pid = f"GOV-{next(_proposal_counter):04d}"

    safe_flags = list(flags) if flags else []
    safe_meta = dict(metadata) if metadata else {}

    change_request = {
        **safe_meta,
        "type": change_type,
        "target": target,
        "flags": safe_flags,
        "reversible": True,
    }

    risk = score_proposal(change_request)
    classification = classify_risk(risk)
    needs_approval = require_approval(change_request, risk)

    proposal = {
        "proposal_id": pid,
        "title": title,
        "description": description,
        "change_type": change_type,
        "target": target,
        "flags": list(safe_flags),
        "risk_score": risk,
        "risk_class": classification,
        "needs_approval": needs_approval,
        "status": "pending",
        "metadata": dict(safe_meta),
        "created_at": time.time(),
    }

    with _proposal_lock:
        _PROPOSALS.append(proposal)
        if len(_PROPOSALS) > _MAX_PROPOSALS:
            _PROPOSALS[:] = _PROPOSALS[-_MAX_PROPOSALS:]

    try:
        from governance.audit_log import log_event
        log_event("proposal_created", {"proposal_id": pid, "risk_score": risk,
                                        "risk_class": classification})
    except Exception:
        pass

    return dict(proposal)


def score_proposal(change_request: Dict[str, Any]) -> int:
    """Score risk (0-100) for a proposal's underlying change request."""
    try:
        from governance.change_contracts import score_risk
        base = score_risk(change_request)
    except Exception:
        base = 80

    try:
        from governance.modes import get_safety_multiplier
        base = min(100, int(base * get_safety_multiplier()))
    except Exception:
        base = min(100, int(base * 2.0))

    return base


def classify_risk(risk_score: int) -> str:
    if risk_score >= 80:
        return "critical"
    if risk_score >= 60:
        return "high"
    if risk_score >= 35:
        return "medium"
    return "low"


def require_approval(
    change_request: Dict[str, Any],
    risk_score: int | None = None,
) -> bool:
    """Determine whether operator approval is required."""
    if risk_score is None:
        risk_score = score_proposal(change_request)

    if risk_score >= 60:
        return True

    try:
        from governance.envelopes import compute_envelope
        env = compute_envelope()
        threshold = env.get("patch_approval_threshold")
        if threshold in ("operator_required", "blocked", "operator_for_medium_and_above"):
            return True
    except Exception:
        return True

    return change_request.get("type") in ("patch_apply", "self_modification")


def get_proposals(status: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
    n = max(0, int(limit))
    with _proposal_lock:
        if status:
            matches = [dict(p) for p in _PROPOSALS if p["status"] == status]
            return matches[-n:] if n > 0 else []
        return [dict(p) for p in _PROPOSALS[-n:]] if n > 0 else []


def get_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    with _proposal_lock:
        for p in _PROPOSALS:
            if p["proposal_id"] == proposal_id:
                return dict(p)
    return None


def approve_proposal(proposal_id: str, reason: str = "operator") -> Dict[str, Any]:
    with _proposal_lock:
        for p in _PROPOSALS:
            if p["proposal_id"] == proposal_id:
                if p["status"] != "pending":
                    return {"success": False,
                            "reason": f"proposal in '{p['status']}' state, expected 'pending'"}
                p["status"] = "approved"
                p["approved_at"] = time.time()
                p["approved_reason"] = reason
                break
        else:
            return {"success": False, "reason": f"proposal '{proposal_id}' not found"}
    try:
        from governance.audit_log import log_event
        log_event("proposal_approved", {"proposal_id": proposal_id})
    except Exception:
        pass
    return {"success": True, "proposal_id": proposal_id}


def reject_proposal(proposal_id: str, reason: str = "operator") -> Dict[str, Any]:
    with _proposal_lock:
        for p in _PROPOSALS:
            if p["proposal_id"] == proposal_id:
                if p["status"] != "pending":
                    return {"success": False,
                            "reason": f"proposal in '{p['status']}' state, expected 'pending'"}
                p["status"] = "rejected"
                p["rejected_at"] = time.time()
                p["rejected_reason"] = reason
                break
        else:
            return {"success": False, "reason": f"proposal '{proposal_id}' not found"}
    try:
        from governance.audit_log import log_event
        log_event("proposal_rejected", {"proposal_id": proposal_id})
    except Exception:
        pass
    return {"success": True, "proposal_id": proposal_id}
