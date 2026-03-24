# governance/modes.py
"""
Governance modes for Daedalus.

Each mode defines autonomy constraints, proposal generation rules,
patch approval thresholds, drift sensitivity, and safety multipliers.
Modes are declarative and operator-switched — no auto-escalation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

STRICT = "STRICT"
ADVISORY = "ADVISORY"
REFLECTIVE = "REFLECTIVE"
DORMANT_MODE = "DORMANT_MODE"
DEFENSIVE = "DEFENSIVE"

_MODES: Dict[str, Dict[str, Any]] = {
    STRICT: {
        "name": "Strict",
        "description": "Maximum governance enforcement — all changes require "
                       "explicit approval, lowest risk tolerance.",
        "autonomy_constraints": {"max_tier": "TIER_0", "auto_proposals": False},
        "proposal_generation_rules": {"auto_generate": False, "require_operator": True},
        "patch_approval_threshold": "operator_required",
        "drift_sensitivity": 1.0,
        "safety_multiplier": 2.0,
    },
    ADVISORY: {
        "name": "Advisory",
        "description": "Balanced governance — proposals generated and scored, "
                       "operator approves non-trivial changes.",
        "autonomy_constraints": {"max_tier": "TIER_1", "auto_proposals": True},
        "proposal_generation_rules": {"auto_generate": True, "require_operator": True},
        "patch_approval_threshold": "operator_for_medium_and_above",
        "drift_sensitivity": 0.7,
        "safety_multiplier": 1.0,
    },
    REFLECTIVE: {
        "name": "Reflective",
        "description": "Analytical governance — focus on drift detection, "
                       "insight generation, minimal active intervention.",
        "autonomy_constraints": {"max_tier": "TIER_0", "auto_proposals": True},
        "proposal_generation_rules": {"auto_generate": True, "require_operator": False},
        "patch_approval_threshold": "operator_required",
        "drift_sensitivity": 0.5,
        "safety_multiplier": 1.0,
    },
    DORMANT_MODE: {
        "name": "Dormant",
        "description": "Governance suspended — no proposals, no patches, "
                       "only safety invariants enforced.",
        "autonomy_constraints": {"max_tier": "TIER_0", "auto_proposals": False},
        "proposal_generation_rules": {"auto_generate": False, "require_operator": True},
        "patch_approval_threshold": "blocked",
        "drift_sensitivity": 0.0,
        "safety_multiplier": 3.0,
    },
    DEFENSIVE: {
        "name": "Defensive",
        "description": "Safety-first governance — only defensive and stabilising "
                       "changes permitted, heightened drift sensitivity.",
        "autonomy_constraints": {"max_tier": "TIER_DEFENSIVE", "auto_proposals": False},
        "proposal_generation_rules": {"auto_generate": False, "require_operator": True},
        "patch_approval_threshold": "operator_required",
        "drift_sensitivity": 1.0,
        "safety_multiplier": 2.0,
    },
}

_active_mode: str = ADVISORY


def list_modes() -> List[Dict[str, Any]]:
    return [{"mode_id": mid, **meta} for mid, meta in _MODES.items()]


def get_mode(mode_id: str) -> Optional[Dict[str, Any]]:
    m = _MODES.get(mode_id)
    if m is None:
        return None
    return {"mode_id": mode_id, **m}


def get_active_mode() -> Dict[str, Any]:
    return get_mode(_active_mode) or get_mode(ADVISORY)  # type: ignore


def set_active_mode(mode_id: str, reason: str = "") -> Dict[str, Any]:
    global _active_mode
    if mode_id not in _MODES:
        return {"success": False, "reason": f"unknown mode '{mode_id}'"}
    prev = _active_mode
    _active_mode = mode_id
    return {"success": True, "from": prev, "to": mode_id, "reason": reason}


def get_drift_sensitivity() -> float:
    return _MODES.get(_active_mode, _MODES[ADVISORY]).get("drift_sensitivity", 0.7)


def get_safety_multiplier() -> float:
    return _MODES.get(_active_mode, _MODES[ADVISORY]).get("safety_multiplier", 1.0)
