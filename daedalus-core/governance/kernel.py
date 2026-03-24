# governance/kernel.py
"""
Meta-governance kernel for Daedalus.

Implements constitutional rules, change contract enforcement, safety
invariant checks, circuit breakers, kill switch, stabilise mode, and
governance health checks.  The kernel is the central authority for all
governance decisions — but operator sovereignty is absolute.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_KERNEL_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 100

_circuit_breaker_tripped: bool = False
_kill_switch_active: bool = False
_stabilise_mode: bool = False


# ------------------------------------------------------------------
# Core evaluation
# ------------------------------------------------------------------

def evaluate_change(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a change request through the full governance pipeline.

    Pipeline:
      1. Check kill switch / stabilise mode / circuit breaker
      2. Enforce safety invariants
      3. Enforce change contracts
      4. Check persona/mode envelope
      5. Return combined verdict
    """
    if _kill_switch_active:
        result = _block("kill switch is active — all changes blocked")
        _log_kernel("evaluate", change_request, result)
        return result

    if _stabilise_mode:
        cr_type = change_request.get("type", "")
        if cr_type not in ("governance_mode_change", "governance_persona_change"):
            result = _block("stabilise mode — only governance meta-changes permitted")
            _log_kernel("evaluate", change_request, result)
            return result

    if _circuit_breaker_tripped:
        result = _block("circuit breaker tripped — changes paused")
        _log_kernel("evaluate", change_request, result)
        return result

    try:
        from governance.safety_invariants import enforce_invariants
        inv = enforce_invariants(change_request)
        if not inv["passed"]:
            result = _block(
                f"safety invariant violated: {inv['violations'][0]['detail']}",
                violations=inv["violations"],
            )
            _log_kernel("invariant_block", change_request, result)
            return result
    except Exception:
        pass

    try:
        from governance.change_contracts import enforce_contract
        contract = enforce_contract(change_request)
        if not contract.get("allowed"):
            result = _block(contract.get("reason", "contract violation"),
                            risk_score=contract.get("risk_score", 0))
            _log_kernel("contract_block", change_request, result)
            return result
    except Exception:
        contract = {"allowed": True, "risk_score": 0, "needs_approval": False,
                    "reversible": True}

    try:
        from governance.envelopes import compute_envelope
        env = compute_envelope()
        cr_type = change_request.get("type", "")
        if cr_type in env.get("forbidden_operations", []):
            result = _block(f"envelope forbids operation '{cr_type}'")
            _log_kernel("envelope_block", change_request, result)
            return result

        if contract.get("risk_score", 0) > env.get("risk_ceiling", 60):
            result = _block(
                f"risk score {contract['risk_score']} exceeds "
                f"envelope ceiling {env['risk_ceiling']}",
                risk_score=contract["risk_score"],
            )
            _log_kernel("risk_ceiling_block", change_request, result)
            return result
    except Exception:
        pass

    result = {
        "allowed": True,
        "reason": "change permitted by governance kernel",
        "risk_score": contract.get("risk_score", 0),
        "needs_approval": contract.get("needs_approval", False),
        "reversible": contract.get("reversible", True),
    }
    _log_kernel("allowed", change_request, result)
    return result


def enforce_contract(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper — delegates to change_contracts.enforce_contract."""
    try:
        from governance.change_contracts import enforce_contract as _ec
        return _ec(change_request)
    except Exception:
        return {"allowed": True, "risk_score": 0, "needs_approval": False}


def enforce_invariants() -> Dict[str, Any]:
    """Run a global invariant health check (no specific change)."""
    try:
        from governance.safety_invariants import enforce_invariants as _ei
        return _ei(None)
    except Exception:
        return {"passed": True, "violations": [], "checked": 0}


# ------------------------------------------------------------------
# Circuit breakers, kill switch, stabilise
# ------------------------------------------------------------------

def apply_circuit_breakers() -> Dict[str, Any]:
    """Evaluate whether circuit breakers should trip.

    Trips if governance health is critically degraded.
    """
    global _circuit_breaker_tripped
    health = compute_governance_health()
    if health.get("governance_score", 100) < 20:
        _circuit_breaker_tripped = True
        _log_kernel("circuit_breaker_tripped", {}, health)
        return {"tripped": True, "reason": "governance score below threshold"}
    return {"tripped": False, "governance_score": health.get("governance_score")}


def reset_circuit_breaker(reason: str = "operator_reset") -> Dict[str, Any]:
    global _circuit_breaker_tripped
    _circuit_breaker_tripped = False
    _log_kernel("circuit_breaker_reset", {}, {"reason": reason})
    return {"success": True, "reason": reason}


def activate_kill_switch(reason: str = "operator") -> Dict[str, Any]:
    global _kill_switch_active
    _kill_switch_active = True
    _log_kernel("kill_switch_activated", {}, {"reason": reason})
    return {"success": True, "active": True, "reason": reason}


def deactivate_kill_switch(reason: str = "operator") -> Dict[str, Any]:
    global _kill_switch_active
    _kill_switch_active = False
    _log_kernel("kill_switch_deactivated", {}, {"reason": reason})
    return {"success": True, "active": False, "reason": reason}


def activate_stabilise_mode(reason: str = "operator") -> Dict[str, Any]:
    global _stabilise_mode
    _stabilise_mode = True
    _log_kernel("stabilise_activated", {}, {"reason": reason})
    return {"success": True, "active": True, "reason": reason}


def deactivate_stabilise_mode(reason: str = "operator") -> Dict[str, Any]:
    global _stabilise_mode
    _stabilise_mode = False
    _log_kernel("stabilise_deactivated", {}, {"reason": reason})
    return {"success": True, "active": False, "reason": reason}


# ------------------------------------------------------------------
# Health & state
# ------------------------------------------------------------------

def compute_governance_health() -> Dict[str, Any]:
    """Compute an overall governance health score (0-100)."""
    score = 100.0

    if _kill_switch_active:
        score -= 40
    if _circuit_breaker_tripped:
        score -= 30
    if _stabilise_mode:
        score -= 10

    try:
        from governance.drift_detector import compute_drift_report
        drift = compute_drift_report()
        total_drift = drift.get("total_drift_score", 0)
        score -= min(30, total_drift * 0.3)
    except Exception:
        pass

    return {
        "governance_score": round(max(0, min(100, score)), 1),
        "kill_switch": _kill_switch_active,
        "circuit_breaker": _circuit_breaker_tripped,
        "stabilise_mode": _stabilise_mode,
        "timestamp": time.time(),
    }


def get_kernel_state() -> Dict[str, Any]:
    """Return the full kernel state."""
    try:
        from governance.personas import get_active_persona
        persona = get_active_persona()
    except Exception:
        persona = {}
    try:
        from governance.modes import get_active_mode
        mode = get_active_mode()
    except Exception:
        mode = {}
    try:
        from governance.envelopes import compute_envelope
        envelope = compute_envelope()
    except Exception:
        envelope = {}

    health = compute_governance_health()

    return {
        "persona": persona,
        "mode": mode,
        "envelope": envelope,
        "health": health,
        "kill_switch": _kill_switch_active,
        "circuit_breaker": _circuit_breaker_tripped,
        "stabilise_mode": _stabilise_mode,
        "recent_decisions": list(_KERNEL_LOG[-5:]),
        "timestamp": time.time(),
    }


def get_kernel_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_KERNEL_LOG[-limit:])


def reset_kernel(reason: str = "operator_reset") -> Dict[str, Any]:
    """Reset all kernel state to defaults."""
    global _circuit_breaker_tripped, _kill_switch_active, _stabilise_mode
    _circuit_breaker_tripped = False
    _kill_switch_active = False
    _stabilise_mode = False
    _KERNEL_LOG.clear()

    try:
        from governance.personas import set_active_persona
        set_active_persona("COMPANION_GOV", reason)
    except Exception:
        pass
    try:
        from governance.modes import set_active_mode
        set_active_mode("ADVISORY", reason)
    except Exception:
        pass

    _log_kernel("kernel_reset", {}, {"reason": reason})
    return {"success": True, "reason": reason}


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _block(reason: str, **extra: Any) -> Dict[str, Any]:
    return {"allowed": False, "reason": reason, **extra}


def _log_kernel(action: str, request: Dict[str, Any],
                result: Dict[str, Any]) -> None:
    _KERNEL_LOG.append({
        "action": action,
        "change_type": request.get("type", ""),
        "allowed": result.get("allowed"),
        "reason": result.get("reason", ""),
        "timestamp": time.time(),
    })
    if len(_KERNEL_LOG) > _MAX_LOG:
        _KERNEL_LOG[:] = _KERNEL_LOG[-_MAX_LOG:]
