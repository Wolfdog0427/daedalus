# runtime/posture_autonomy.py
"""
Posture-bounded autonomy helpers.

Provides per-posture autonomy profiles that may further *restrict*
allowed actions but never *expand* them beyond existing global
safety/autonomy rules.

Phase 63: integrates with autonomy_engine for tier-aware constraints.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from runtime.posture_registry import (
    ARCHITECT, CEREMONIAL, COMPANION, DORMANT, NULL,
    ORACLE, SCRIBE, SENTINEL_QUIET, SHROUD, TALON, VEIL,
)

# ── Autonomy profiles ───────────────────────────────────────────

_PROFILES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "allowed_categories": {"read", "write", "analysis", "mutation", "monitoring"},
        "notes": "Normal allowed actions within existing envelope.",
    },
    ARCHITECT: {
        "allowed_categories": {"read", "analysis", "monitoring", "mutation"},
        "notes": "Normal analytical actions, no extra mutation beyond envelope.",
    },
    ORACLE: {
        "allowed_categories": {"read", "analysis", "monitoring"},
        "notes": "Normal analytical actions, no extra mutation.",
    },
    SCRIBE: {
        "allowed_categories": {"read", "analysis", "monitoring"},
        "notes": "Read-heavy; write only where explicitly requested.",
    },
    SENTINEL_QUIET: {
        "allowed_categories": {"read", "monitoring", "analysis"},
        "notes": "Minimal actions — mostly monitoring and analysis.",
    },
    CEREMONIAL: {
        "allowed_categories": {"read", "write", "analysis", "mutation", "monitoring"},
        "notes": "Normal actions, emphasis on closure/summary.",
    },
    VEIL: {
        "allowed_categories": {"read", "write", "analysis", "mutation", "monitoring"},
        "notes": "No change to autonomy — only expression affected.",
    },
    SHROUD: {
        "allowed_categories": {"read", "analysis"},
        "notes": "Restricts to safest subset: read-only and analysis.",
    },
    TALON: {
        "allowed_categories": {"read", "analysis", "monitoring", "defensive"},
        "notes": "Defensive actions only within existing defense envelope.",
    },
    NULL: {
        "allowed_categories": set(),
        "notes": "No actions — offline.",
    },
    DORMANT: {
        "allowed_categories": set(),
        "notes": "No actions — dormant.",
    },
}

_DEFAULT_PROFILE: Dict[str, Any] = {
    "allowed_categories": {"read", "analysis", "monitoring"},
    "notes": "Default — conservative subset.",
}


def _get_posture_id() -> str:
    try:
        from runtime.posture_state import get_current_posture
        return get_current_posture().get("posture_id", COMPANION)
    except ImportError:
        return COMPANION
    except Exception:
        return COMPANION


def get_autonomy_profile() -> Dict[str, Any]:
    """Return the autonomy profile for the active posture.

    Includes tier-aware constraints when the autonomy engine is available.
    """
    pid = _get_posture_id()
    profile = _PROFILES.get(pid, _DEFAULT_PROFILE)

    result = {
        "posture_id": pid,
        "allowed_categories": sorted(profile["allowed_categories"]),
        "notes": profile["notes"],
    }

    try:
        from runtime.autonomy_engine import get_effective_tier
        tier = get_effective_tier()
        result["effective_tier"] = tier.get("tier_id", "?")
        result["tier_allowed"] = tier.get("allowed_action_categories", [])
    except Exception:
        pass

    return result


def _is_posture_allowed(
    action_type: str,
    context: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    """Posture-only check (no tier consultation).

    Used internally by autonomy_engine to avoid circular calls.
    """
    pid = _get_posture_id()
    profile = _PROFILES.get(pid, _DEFAULT_PROFILE)
    allowed_cats = set(profile["allowed_categories"])

    if not allowed_cats:
        return False, f"posture {pid} does not allow any actions"

    if action_type in allowed_cats:
        return True, f"action '{action_type}' is allowed under posture {pid}"

    return (
        False,
        f"action '{action_type}' is not in allowed categories "
        f"{sorted(allowed_cats)} for posture {pid}",
    )


def is_action_allowed(
    action_type: str,
    context: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    """Check whether *action_type* is permitted.

    Consults the autonomy engine (tier + posture) when available;
    falls back to posture-only check otherwise.
    """
    try:
        from runtime.autonomy_engine import can_perform
        return can_perform(action_type, context)
    except ImportError:
        return _is_posture_allowed(action_type, context)
    except Exception:
        return False, f"autonomy check failed for '{action_type}' — fail-closed"
