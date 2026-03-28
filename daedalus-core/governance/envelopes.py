# governance/envelopes.py
"""
Persona/mode governance envelopes.

An envelope is the intersection of a persona and a mode — it defines
the effective allowed operations, risk ceilings, escalation behaviour,
and reversibility requirements for the current governance posture.
Envelopes are computed on demand, never persisted.
"""

from __future__ import annotations

from typing import Any, Dict


def compute_envelope() -> Dict[str, Any]:
    """Compute the active governance envelope from persona + mode."""
    try:
        from governance.personas import get_active_persona
        persona = get_active_persona()
    except Exception:
        persona = {"persona_id": "COMPANION_GOV", "allowed_operations": [],
                   "forbidden_operations": [], "risk_posture": "moderate"}

    try:
        from governance.modes import get_active_mode
        mode = get_active_mode()
    except Exception:
        mode = {"mode_id": "ADVISORY", "drift_sensitivity": 0.7,
                "safety_multiplier": 1.0, "patch_approval_threshold": "operator_required"}

    pid = persona.get("persona_id", "COMPANION_GOV")
    mid = mode.get("mode_id", "ADVISORY")

    allowed = set(persona.get("allowed_operations", []))
    forbidden = set(persona.get("forbidden_operations", []))

    threshold = mode.get("patch_approval_threshold", "operator_required")
    if threshold == "blocked":
        allowed = set()
        forbidden.add("patch_apply")

    risk_posture = persona.get("risk_posture", "moderate")
    safety_mult = max(0.01, mode.get("safety_multiplier", 1.0))

    risk_ceiling = {
        "low": 30, "moderate": 60, "neutral": 50,
    }.get(risk_posture, 60)

    return {
        "persona_id": pid,
        "mode_id": mid,
        "allowed_operations": sorted(allowed - forbidden),
        "forbidden_operations": sorted(forbidden),
        "risk_ceiling": risk_ceiling,
        "escalation_ceiling": "operator_required" if safety_mult > 1.0 else "advisory",
        "reversibility_required": threshold in ("operator_required", "blocked"),
        "patch_approval_threshold": threshold,
        "drift_sensitivity": mode.get("drift_sensitivity", 0.7),
        "safety_multiplier": safety_mult,
    }


def is_operation_allowed_by_envelope(operation: str) -> bool:
    """Check whether *operation* is allowed under the active envelope.

    When the allowlist is empty **and** `patch_approval_threshold` is
    ``"blocked"``, nothing is allowed.  Otherwise an empty allowlist is
    treated as "no restrictions beyond the forbidden set".
    """
    env = compute_envelope()
    if operation in env["forbidden_operations"]:
        return False
    allowed = env["allowed_operations"]
    if not allowed:
        return env.get("patch_approval_threshold") != "blocked"
    return operation in allowed
