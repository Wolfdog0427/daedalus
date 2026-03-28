# runtime/autonomy_engine.py
"""
Central autonomy engine for Daedalus.

Evaluates whether an action is allowed at the current autonomy tier,
taking posture restrictions into account.  All transitions are explicit
and operator-triggered — no automatic tier escalation.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Tuple

from runtime.autonomy_tiers import (
    TIER_0, TIER_1, TIER_DEFENSIVE,
    get_tier, list_tiers,
)
from runtime.autonomy_state import (
    _set_tier,
    get_current_tier,
    get_tier_history,
)

_TRANSITION_LOG: List[Dict[str, Any]] = []
_MAX_TRANSITION_LOG = 500
_transition_log_lock = threading.Lock()

# Postures that force a specific tier unless the operator overrides
_POSTURE_FORCED_TIERS: Dict[str, str] = {
    "SHROUD": TIER_0,
    "NULL": TIER_0,
    "DORMANT": TIER_0,
    "TALON": TIER_DEFENSIVE,
}


def get_transition_log(limit: int = 20) -> List[Dict[str, Any]]:
    n = max(0, int(limit))
    with _transition_log_lock:
        return [dict(e) for e in _TRANSITION_LOG[-n:]] if n > 0 else []


def _get_posture_id() -> str:
    try:
        from runtime.posture_state import get_current_posture
        return get_current_posture().get("posture_id", "COMPANION")
    except Exception:
        return "COMPANION"


def _get_posture_forced_tier() -> str | None:
    """Return the tier forced by the current posture, or None."""
    pid = _get_posture_id()
    return _POSTURE_FORCED_TIERS.get(pid)


def get_effective_tier() -> Dict[str, Any]:
    """Return the effective tier, considering posture overrides.

    Posture-forced tiers apply unless the operator has explicitly set
    the tier *after* the posture change (indicated by the tier's
    metadata containing ``operator_override=True``).
    """
    current = get_current_tier()
    forced = _get_posture_forced_tier()

    if forced is None:
        return current

    if current.get("metadata", {}).get("operator_override"):
        return current

    forced_info = get_tier(forced) or {}
    return {
        "tier_id": forced,
        "reason": f"forced by posture {_get_posture_id()}",
        "metadata": {"posture_forced": True},
        "timestamp": current.get("timestamp", time.time()),
        **forced_info,
    }


def request_tier(
    tier_id: str,
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Request a tier change.  Returns a structured result."""
    # Governance binding: structural change requires kernel review
    try:
        from governance.runtime_binding import (
            is_governance_forbidden, requires_governance_review,
        )
        if is_governance_forbidden("tier_change"):
            return {
                "success": False, "tier_id": tier_id, "reason": reason,
                "rationale": "governance: tier changes are forbidden",
                "timestamp": time.time(),
            }
        if requires_governance_review("tier_change"):
            from governance.kernel import evaluate_change as _gov_eval
            verdict = _gov_eval({
                "type": "tier_change",
                "target": tier_id,
                "flags": [],
                "reversible": True,
            })
            if not verdict.get("allowed", False) or verdict.get("needs_approval", False):
                return {
                    "success": False, "tier_id": tier_id, "reason": reason,
                    "rationale": f"governance: {verdict.get('reason', 'blocked — operator approval required')}",
                    "timestamp": time.time(),
                }
    except Exception:
        return {
            "success": False, "tier_id": tier_id, "reason": reason,
            "rationale": "governance: evaluation failed — fail-closed",
            "timestamp": time.time(),
        }

    target = get_tier(tier_id)
    if target is None:
        result = {
            "success": False,
            "tier_id": tier_id,
            "reason": reason,
            "rationale": f"unknown tier '{tier_id}'",
            "timestamp": time.time(),
        }
        with _transition_log_lock:
            _TRANSITION_LOG.append({**result, "type": "rejected"})
            if len(_TRANSITION_LOG) > _MAX_TRANSITION_LOG:
                _TRANSITION_LOG[:] = _TRANSITION_LOG[-_MAX_TRANSITION_LOG:]
        return result

    meta = dict(metadata or {})
    meta["operator_override"] = True

    record = _set_tier(tier_id, reason, meta)

    result = {
        "success": True,
        "tier_id": tier_id,
        "reason": reason,
        "rationale": "tier set by operator",
        "from_tier": record["from_tier"],
        "to_tier": record["to_tier"],
        "timestamp": record["timestamp"],
    }
    with _transition_log_lock:
        _TRANSITION_LOG.append({**result, "type": "activated"})
        if len(_TRANSITION_LOG) > _MAX_TRANSITION_LOG:
            _TRANSITION_LOG[:] = _TRANSITION_LOG[-_MAX_TRANSITION_LOG:]
    return result


def can_perform(
    action_type: str,
    context: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    """Check whether *action_type* is allowed at the effective tier.

    Also consults posture autonomy — both must agree for the action
    to be permitted.  This never expands beyond existing global rules.
    """
    effective = get_effective_tier()
    tid = effective.get("tier_id", TIER_1)
    allowed = set(effective.get("allowed_action_categories", []))
    disallowed = set(effective.get("disallowed_action_categories", []))

    if action_type in disallowed:
        return (
            False,
            f"action '{action_type}' is disallowed at tier {tid}",
        )

    if allowed and action_type not in allowed:
        return (
            False,
            f"action '{action_type}' is not in allowed categories "
            f"{sorted(allowed)} at tier {tid}",
        )

    try:
        from runtime.posture_autonomy import _is_posture_allowed
        posture_ok, posture_reason = _is_posture_allowed(action_type, context)
        if not posture_ok:
            return False, f"tier {tid} allows, but posture restricts: {posture_reason}"
    except ImportError:
        return False, f"posture_autonomy module unavailable — fail-closed for '{action_type}'"
    except Exception:
        return False, f"posture check unavailable for '{action_type}' at tier {tid}"

    return True, f"action '{action_type}' is allowed at tier {tid}"


def explain_tier() -> Dict[str, Any]:
    """Return a structured explanation of the effective tier."""
    effective = get_effective_tier()
    posture_forced = _get_posture_forced_tier()

    try:
        from runtime.posture_autonomy import get_autonomy_profile
        posture_profile = get_autonomy_profile()
    except Exception:
        posture_profile = {"error": "posture autonomy unavailable"}

    return {
        "tier_id": effective.get("tier_id"),
        "tier_name": effective.get("name", "?"),
        "reason": effective.get("reason", "?"),
        "allowed_action_categories": effective.get("allowed_action_categories", []),
        "disallowed_action_categories": effective.get("disallowed_action_categories", []),
        "safety_flags": effective.get("safety_flags", []),
        "posture_forced_tier": posture_forced,
        "posture_id": _get_posture_id(),
        "posture_profile": posture_profile,
        "operator_override": effective.get("metadata", {}).get("operator_override", False),
        "timestamp": effective.get("timestamp"),
    }
