# governance/proposal_engine.py
"""
Governance proposal engine for Daedalus.

Generates, scores, and classifies governance proposals based on drift
detection, diagnostics, stability signals, coherence signals, and
operator requests.  Never auto-executes — all proposals require
operator review.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_PROPOSALS: List[Dict[str, Any]] = []
_MAX_PROPOSALS = 100
_proposal_counter: int = 0


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
    global _proposal_counter
    _proposal_counter += 1
    pid = f"GOV-{_proposal_counter:04d}"

    change_request = {
        "type": change_type,
        "target": target,
        "flags": flags or [],
        "reversible": True,
        **(metadata or {}),
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
        "flags": flags or [],
        "risk_score": risk,
        "risk_class": classification,
        "needs_approval": needs_approval,
        "status": "pending",
        "metadata": metadata or {},
        "created_at": time.time(),
    }

    _PROPOSALS.append(proposal)
    if len(_PROPOSALS) > _MAX_PROPOSALS:
        _PROPOSALS[:] = _PROPOSALS[-_MAX_PROPOSALS:]

    try:
        from governance.audit_log import log_event
        log_event("proposal_created", {"proposal_id": pid, "risk_score": risk,
                                        "risk_class": classification})
    except Exception:
        pass

    return proposal


def score_proposal(change_request: Dict[str, Any]) -> int:
    """Score risk (0-100) for a proposal's underlying change request."""
    try:
        from governance.change_contracts import score_risk
        base = score_risk(change_request)
    except Exception:
        base = 30

    try:
        from governance.modes import get_safety_multiplier
        base = min(100, int(base * get_safety_multiplier()))
    except Exception:
        pass

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
        if env.get("patch_approval_threshold") in ("operator_required", "blocked"):
            return True
    except Exception:
        pass

    return change_request.get("type") in ("patch_apply", "self_modification")


def get_proposals(status: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
    if status:
        return [p for p in _PROPOSALS if p["status"] == status][-limit:]
    return list(_PROPOSALS[-limit:])


def get_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    for p in _PROPOSALS:
        if p["proposal_id"] == proposal_id:
            return dict(p)
    return None


def approve_proposal(proposal_id: str, reason: str = "operator") -> Dict[str, Any]:
    for p in _PROPOSALS:
        if p["proposal_id"] == proposal_id:
            p["status"] = "approved"
            p["approved_at"] = time.time()
            p["approved_reason"] = reason
            try:
                from governance.audit_log import log_event
                log_event("proposal_approved", {"proposal_id": proposal_id})
            except Exception:
                pass
            return {"success": True, "proposal_id": proposal_id}
    return {"success": False, "reason": f"proposal '{proposal_id}' not found"}


def reject_proposal(proposal_id: str, reason: str = "operator") -> Dict[str, Any]:
    for p in _PROPOSALS:
        if p["proposal_id"] == proposal_id:
            p["status"] = "rejected"
            p["rejected_at"] = time.time()
            p["rejected_reason"] = reason
            try:
                from governance.audit_log import log_event
                log_event("proposal_rejected", {"proposal_id": proposal_id})
            except Exception:
                pass
            return {"success": True, "proposal_id": proposal_id}
    return {"success": False, "reason": f"proposal '{proposal_id}' not found"}
