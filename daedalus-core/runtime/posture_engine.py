# runtime/posture_engine.py
"""
Central posture engine for Daedalus.

Handles posture activation, deactivation, precedence resolution,
safety checks, and transition logging.  All transitions are explicit
and operator-triggered — no hidden auto-switching.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Tuple

from runtime.posture_registry import (
    COMPANION, DORMANT, NULL, SHROUD, TALON, VEIL,
    get_posture, list_postures,
)
from runtime.posture_state import (
    _set_posture,
    get_current_posture,
    get_posture_history,
    get_previous_posture,
)

_TRANSITION_LOG: List[Dict[str, Any]] = []
_MAX_TRANSITION_LOG = 500
_transition_log_lock = threading.Lock()

_OFFLINE_POSTURES = {NULL, DORMANT}
_HIGH_PRIORITY_OVERRIDES = {NULL, DORMANT, TALON, SHROUD}


def get_transition_log(limit: int = 20) -> List[Dict[str, Any]]:
    n = max(0, int(limit))
    with _transition_log_lock:
        return [dict(e) for e in _TRANSITION_LOG[-n:]] if n > 0 else []


def get_active_posture() -> Dict[str, Any]:
    """Return the currently active posture with full metadata."""
    return get_current_posture()


def can_transition_to(posture_id: str) -> Tuple[bool, str]:
    """
    Check whether a transition to *posture_id* is allowed.

    Returns (allowed, rationale).
    """
    target = get_posture(posture_id)
    if target is None:
        return False, f"unknown posture '{posture_id}'"

    current = get_current_posture()
    cur_id = current["posture_id"]

    if cur_id == posture_id:
        return True, "already in this posture"

    # NULL/DORMANT override everything
    if posture_id in _OFFLINE_POSTURES:
        return True, f"{posture_id} may always be explicitly set"

    # Cannot transition out of NULL/DORMANT except to another explicit request
    # (which is fine — operator explicitly requested it)
    if cur_id in _OFFLINE_POSTURES:
        return True, f"leaving {cur_id} via explicit request"

    # TALON can pre-empt when explicitly requested
    if posture_id == TALON:
        return True, "TALON may be explicitly activated for defensive posture"

    # SHROUD can override expressive postures when explicitly requested
    if posture_id == SHROUD:
        return True, "SHROUD may be explicitly activated for constrained posture"

    # VEIL layers as expression modifier
    if posture_id == VEIL:
        return True, "VEIL may be activated as expression modifier"

    # Standard postures can transition freely among themselves
    return True, "standard posture transition"


def request_posture(
    posture_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Request a posture change.  Goes through precedence and safety checks.

    Returns a structured result with transition details or rejection reason.
    """
    allowed, rationale = can_transition_to(posture_id)

    # Governance binding: structural change requires kernel review
    if allowed:
        try:
            from governance.runtime_binding import (
                is_governance_forbidden, requires_governance_review,
            )
            if is_governance_forbidden("posture_transition"):
                allowed = False
                rationale = "governance: posture transitions are forbidden"
            elif requires_governance_review("posture_transition"):
                from governance.kernel import evaluate_change
                verdict = evaluate_change({
                    "type": "posture_transition",
                    "target": posture_id,
                    "flags": [],
                    "reversible": True,
                })
                if not verdict.get("allowed", False) or verdict.get("needs_approval", False):
                    allowed = False
                    rationale = f"governance: {verdict.get('reason', 'blocked — operator approval required')}"
        except Exception:
            allowed = False
            rationale = "governance: evaluation failed — fail-closed"

    if not allowed:
        result = {
            "success": False,
            "posture_id": posture_id,
            "reason": reason,
            "rationale": rationale,
            "timestamp": time.time(),
        }
        with _transition_log_lock:
            _TRANSITION_LOG.append({**result, "type": "rejected"})
            if len(_TRANSITION_LOG) > _MAX_TRANSITION_LOG:
                _TRANSITION_LOG[:] = _TRANSITION_LOG[-_MAX_TRANSITION_LOG:]
        return result

    record = _set_posture(posture_id, reason, metadata)

    result = {
        "success": True,
        "posture_id": posture_id,
        "reason": reason,
        "rationale": rationale,
        "from_posture": record["from_posture"],
        "to_posture": record["to_posture"],
        "timestamp": record["timestamp"],
    }
    with _transition_log_lock:
        _TRANSITION_LOG.append({**result, "type": "activated"})
        if len(_TRANSITION_LOG) > _MAX_TRANSITION_LOG:
            _TRANSITION_LOG[:] = _TRANSITION_LOG[-_MAX_TRANSITION_LOG:]

    return result


def explain_posture() -> Dict[str, Any]:
    """
    Return a structured explanation of the current posture, including
    expression profile, autonomy profile, and applicable constraints.
    """
    current = get_current_posture()
    pid = current["posture_id"]

    try:
        from runtime.posture_expression import get_expression_profile
        expr = get_expression_profile()
    except Exception:
        expr = {"error": "expression module unavailable"}

    try:
        from runtime.posture_autonomy import get_autonomy_profile
        auto = get_autonomy_profile()
    except Exception:
        auto = {"error": "autonomy module unavailable"}

    return {
        "posture_id": pid,
        "name": current.get("name", "?"),
        "category": current.get("category", "?"),
        "reason": current.get("reason", "?"),
        "expression_level": current.get("allowed_expression_level", "?"),
        "autonomy_level": current.get("allowed_autonomy_level", "?"),
        "safety_flags": current.get("safety_flags", []),
        "expression_profile": expr,
        "autonomy_profile": auto,
        "timestamp": current.get("timestamp"),
    }
