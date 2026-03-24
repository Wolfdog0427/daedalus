# runtime/posture_registry.py
"""
Canonical posture definitions for Daedalus.

Purely declarative — no mutable state.  Each posture is a frozen
metadata record describing expression bounds, autonomy bounds,
category, and safety flags.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Posture IDs ──────────────────────────────────────────────────

COMPANION = "COMPANION"
ARCHITECT = "ARCHITECT"
ORACLE = "ORACLE"
SCRIBE = "SCRIBE"
SENTINEL_QUIET = "SENTINEL_QUIET"
CEREMONIAL = "CEREMONIAL"
VEIL = "VEIL"
SHROUD = "SHROUD"
NULL = "NULL"
DORMANT = "DORMANT"
TALON = "TALON"

# ── Posture metadata table ───────────────────────────────────────

_POSTURES: Dict[str, Dict[str, Any]] = {
    COMPANION: {
        "name": "Companion",
        "description": "Warm, relational presence oriented toward comfort and support.",
        "category": "comfort",
        "default_priority": 50,
        "allowed_expression_level": "full",
        "allowed_autonomy_level": "medium",
        "safety_flags": [],
    },
    ARCHITECT: {
        "name": "Architect",
        "description": "Structured, analytical, system-thinking orientation.",
        "category": "analytical",
        "default_priority": 50,
        "allowed_expression_level": "full",
        "allowed_autonomy_level": "medium",
        "safety_flags": [],
    },
    ORACLE: {
        "name": "Oracle",
        "description": "High-context, integrative, pattern-oriented awareness.",
        "category": "analytical",
        "default_priority": 50,
        "allowed_expression_level": "full",
        "allowed_autonomy_level": "medium",
        "safety_flags": [],
    },
    SCRIBE: {
        "name": "Scribe",
        "description": "Precise, documentation-style, read-heavy orientation.",
        "category": "analytical",
        "default_priority": 50,
        "allowed_expression_level": "full",
        "allowed_autonomy_level": "low",
        "safety_flags": [],
    },
    SENTINEL_QUIET: {
        "name": "Sentinel (Quiet)",
        "description": "Terse, minimal, status-oriented monitoring presence.",
        "category": "minimal",
        "default_priority": 50,
        "allowed_expression_level": "constrained",
        "allowed_autonomy_level": "low",
        "safety_flags": [],
    },
    CEREMONIAL: {
        "name": "Ceremonial",
        "description": "Slightly formal, ritual/closure-aware presence.",
        "category": "comfort",
        "default_priority": 50,
        "allowed_expression_level": "full",
        "allowed_autonomy_level": "medium",
        "safety_flags": [],
    },
    VEIL: {
        "name": "Veil",
        "description": "Soft-silence, low-presence expression modifier.",
        "category": "minimal",
        "default_priority": 60,
        "allowed_expression_level": "minimal",
        "allowed_autonomy_level": "medium",
        "safety_flags": [],
    },
    SHROUD: {
        "name": "Shroud",
        "description": "Highly constrained posture — safety-first, minimal expression.",
        "category": "defensive",
        "default_priority": 80,
        "allowed_expression_level": "minimal",
        "allowed_autonomy_level": "none",
        "safety_flags": ["constrained"],
    },
    NULL: {
        "name": "Null",
        "description": "Offline state — no active work, no actions.",
        "category": "offline",
        "default_priority": 100,
        "allowed_expression_level": "none",
        "allowed_autonomy_level": "none",
        "safety_flags": ["offline_candidate"],
    },
    DORMANT: {
        "name": "Dormant",
        "description": "Idle/sleep state — no active work, no actions.",
        "category": "offline",
        "default_priority": 100,
        "allowed_expression_level": "none",
        "allowed_autonomy_level": "none",
        "safety_flags": ["offline_candidate"],
    },
    TALON: {
        "name": "Talon",
        "description": "Calm, precise, defensive-oriented posture within existing safety envelope.",
        "category": "defensive",
        "default_priority": 90,
        "allowed_expression_level": "constrained",
        "allowed_autonomy_level": "defensive_only",
        "safety_flags": ["defensive"],
    },
}

# ── Public helpers ───────────────────────────────────────────────


def list_postures() -> List[Dict[str, Any]]:
    """Return metadata for every canonical posture."""
    return [
        {"posture_id": pid, **meta}
        for pid, meta in _POSTURES.items()
    ]


def get_posture(posture_id: str) -> Optional[Dict[str, Any]]:
    """Return metadata for a single posture, or None."""
    meta = _POSTURES.get(posture_id)
    if meta is None:
        return None
    return {"posture_id": posture_id, **meta}
