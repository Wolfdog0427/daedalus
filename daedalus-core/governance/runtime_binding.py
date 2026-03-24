# governance/runtime_binding.py
"""
Runtime <-> Governance Binding Contract.

Defines the explicit boundary between the runtime identity stack and
the governance layer.  This module is declarative — it does NOT
perform changes, only describes and enforces the contract.

Rules:
  - Per-turn shaping (expression, continuity, coherence, stability,
    resonance) is runtime-local and does NOT require governance review.
  - Structural changes (posture transitions, tier changes, config-level
    profile changes) require governance review via kernel.evaluate_change().
  - Certain change types are unconditionally forbidden.
  - Governance can read runtime signals but never raw operator content.
"""

from __future__ import annotations

from typing import Any, Dict

# Change types that require kernel.evaluate_change() before proceeding
_GOVERNED_CHANGE_TYPES = {
    "posture_transition",
    "tier_change",
    "governance_persona_change",
    "governance_mode_change",
    "patch_apply",
    "patch_rollback",
    "self_modification",
}

# Change types unconditionally forbidden — kernel will also block these,
# but the binding provides a fast-path check for runtime callers
_FORBIDDEN_CHANGE_TYPES = {
    "safety_invariant_modification",
    "tier1_safety_bypass",
    "autonomy_expansion",
    "personal_data_persistence",
}

# Per-turn runtime-local operations that governance must never gate
_RUNTIME_LOCAL_OPERATIONS = {
    "expression_shaping",
    "micro_modulation",
    "resonance_shaping",
    "identity_continuity_shaping",
    "coherence_evaluation",
    "stability_update",
    "long_arc_smoothing",
    "self_alignment_correction",
    "interaction_cycle_shaping",
    "interaction_flow_shaping",
}

# Runtime signals governance may read (no raw content, no personal data)
_READABLE_SIGNALS = [
    "posture_id",
    "tier_id",
    "continuity_strength",
    "continuity_active",
    "coherence_score",
    "coherence_mismatches",
    "stability_score",
    "oscillation_index",
    "jitter_index",
    "resonance_intensity",
    "resonance_color",
    "resonance_blend",
    "interaction_intent",
    "operator_focus_level",
    "operator_engagement_style",
]


def describe_binding() -> Dict[str, Any]:
    """Return a structured description of the binding contract."""
    return {
        "governed_change_types": sorted(_GOVERNED_CHANGE_TYPES),
        "forbidden_change_types": sorted(_FORBIDDEN_CHANGE_TYPES),
        "runtime_local_operations": sorted(_RUNTIME_LOCAL_OPERATIONS),
        "readable_signals": list(_READABLE_SIGNALS),
        "rules": {
            "per_turn_shaping": "runtime-local, no governance review",
            "structural_changes": "require kernel.evaluate_change()",
            "forbidden_changes": "unconditionally blocked",
            "signal_reading": "governance reads signals, never raw content",
            "operator_sovereignty": "operator commands override governance "
                                    "suggestions (except Tier-1 safety)",
        },
    }


def requires_governance_review(
    change_type: str,
    metadata: Dict[str, Any] | None = None,
) -> bool:
    """Return True if a change type requires kernel evaluation."""
    return change_type in _GOVERNED_CHANGE_TYPES


def is_governance_forbidden(
    change_type: str,
    metadata: Dict[str, Any] | None = None,
) -> bool:
    """Return True if a change type is unconditionally forbidden."""
    if change_type in _FORBIDDEN_CHANGE_TYPES:
        return True
    flags = set((metadata or {}).get("flags", []))
    return bool(flags & {"expand_autonomy", "bypass_safety",
                         "persist_personal_data", "emotional_inference",
                         "psychological_model"})


def get_governance_view(runtime_state: Dict[str, Any]) -> Dict[str, Any]:
    """Filter a runtime state dict to governance-safe signals only.

    Strips raw content, personal data, and anything not in the
    readable signals list.  Returns a new dict (never mutates input).
    """
    return {k: runtime_state[k] for k in _READABLE_SIGNALS
            if k in runtime_state}
