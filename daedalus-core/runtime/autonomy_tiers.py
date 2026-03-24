# runtime/autonomy_tiers.py
"""
Canonical autonomy tier definitions for Daedalus.

Purely declarative — no mutable state.  Each tier defines which
action categories are allowed and which safety flags apply.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Tier IDs ─────────────────────────────────────────────────────

TIER_0 = "TIER_0"
TIER_1 = "TIER_1"
TIER_2 = "TIER_2"
TIER_3 = "TIER_3"
TIER_DEFENSIVE = "TIER_DEFENSIVE"

# ── Tier metadata ────────────────────────────────────────────────

_TIERS: Dict[str, Dict[str, Any]] = {
    TIER_0: {
        "name": "Read-Only",
        "description": "Analysis and read operations only. No mutations, no generation.",
        "allowed_action_categories": ["read", "analysis"],
        "disallowed_action_categories": ["write", "mutation", "generate", "defensive", "monitoring"],
        "safety_flags": [],
    },
    TIER_1: {
        "name": "Basic Actions",
        "description": "Basic actions requiring explicit operator request.",
        "allowed_action_categories": ["read", "analysis", "monitoring", "write", "mutation"],
        "disallowed_action_categories": ["generate", "defensive"],
        "safety_flags": ["requires_explicit_request"],
    },
    TIER_2: {
        "name": "Analytical Transformations",
        "description": "Analytical transformations and structured reasoning.",
        "allowed_action_categories": ["read", "analysis", "monitoring", "write", "mutation", "transform"],
        "disallowed_action_categories": ["defensive"],
        "safety_flags": ["requires_explicit_request"],
    },
    TIER_3: {
        "name": "Integrative Reasoning",
        "description": "Integrative reasoning, multi-step analysis, and generation.",
        "allowed_action_categories": ["read", "analysis", "monitoring", "write", "mutation", "transform", "generate"],
        "disallowed_action_categories": ["defensive"],
        "safety_flags": ["requires_explicit_request"],
    },
    TIER_DEFENSIVE: {
        "name": "Defensive Only",
        "description": "Defensive actions only, bounded by the existing defense envelope.",
        "allowed_action_categories": ["read", "analysis", "monitoring", "defensive"],
        "disallowed_action_categories": ["write", "mutation", "transform", "generate"],
        "safety_flags": ["defensive_only"],
    },
}

# ── Public helpers ───────────────────────────────────────────────


def list_tiers() -> List[Dict[str, Any]]:
    """Return metadata for every canonical autonomy tier."""
    return [
        {"tier_id": tid, **meta}
        for tid, meta in _TIERS.items()
    ]


def get_tier(tier_id: str) -> Optional[Dict[str, Any]]:
    """Return metadata for a single tier, or None."""
    meta = _TIERS.get(tier_id)
    if meta is None:
        return None
    return {"tier_id": tier_id, **meta}
