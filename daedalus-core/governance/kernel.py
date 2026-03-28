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
import threading
from typing import Any, Dict, List

_KERNEL_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 100

_kernel_state_lock = threading.RLock()
_circuit_breaker_tripped: bool = False
_kill_switch_active: bool = False
_stabilise_mode: bool = False


# ------------------------------------------------------------------
# Core evaluation
# ------------------------------------------------------------------

def _knowledge_governor_locked() -> bool:
    """Check whether the knowledge-layer autonomy governor has locked
    the system. Bridges the two governance layers.

    - ImportError (module absent): governor doesn't exist, not locked.
    - Other Exception (module broken): fail-closed, assume locked.
    """
    try:
        from governor.state_store import load_state
        state = load_state()
        return state.get("locked", False)
    except ImportError:
        return False
    except Exception:
        return True


def evaluate_change(change_request: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a change request through the full governance pipeline.

    Pipeline:
      0. Check knowledge-layer governor lock state
      1. Check kill switch / stabilise mode / circuit breaker
      2. Enforce safety invariants
      3. Enforce change contracts
      4. Check persona/mode envelope
      5. Return combined verdict
    """
    # Bridge: respect knowledge-layer lock
    if _knowledge_governor_locked():
        result = _block("knowledge governor locked — all changes blocked")
        _log_kernel("evaluate", change_request, result)
        return result

    with _kernel_state_lock:
        ks_active = _kill_switch_active
        stab_mode = _stabilise_mode
        cb_tripped = _circuit_breaker_tripped

    if ks_active:
        result = _block("kill switch is active — all changes blocked")
        _log_kernel("evaluate", change_request, result)
        return result

    if stab_mode:
        cr_type = change_request.get("type", "")
        if cr_type not in ("governance_mode_change", "governance_persona_change"):
            result = _block("stabilise mode — only governance meta-changes permitted")
            _log_kernel("evaluate", change_request, result)
            return result

    if cb_tripped:
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
    except ImportError:
        result = _block("safety invariants module missing — fail-closed")
        _log_kernel("invariant_missing", change_request, result)
        return result
    except Exception:
        result = _block("safety invariant check failed — fail-closed")
        _log_kernel("invariant_error", change_request, result)
        return result

    try:
        from governance.change_contracts import enforce_contract
        contract = enforce_contract(change_request)
        if not contract.get("allowed"):
            result = _block(contract.get("reason", "contract violation"),
                            risk_score=contract.get("risk_score", 0))
            _log_kernel("contract_block", change_request, result)
            return result
    except ImportError:
        result = _block("change contracts module missing — fail-closed",
                        risk_score=100)
        _log_kernel("contract_missing", change_request, result)
        return result
    except Exception:
        result = _block("change contract evaluation failed — fail-closed")
        _log_kernel("contract_error", change_request, result)
        return result

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
    except ImportError:
        result = _block("governance envelopes module missing — fail-closed")
        _log_kernel("envelope_missing", change_request, result)
        return result
    except Exception:
        result = _block("envelope evaluation failed — fail-closed")
        _log_kernel("envelope_error", change_request, result)
        return result

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
    """Convenience wrapper — delegates to change_contracts.enforce_contract.

    Fail-closed: if the module is missing or the call fails, the
    contract is treated as violated.
    """
    try:
        from governance.change_contracts import enforce_contract as _ec
        return _ec(change_request)
    except ImportError:
        return {"allowed": False, "risk_score": 100, "needs_approval": True,
                "reason": "change contracts module missing — fail-closed",
                "reversible": False}
    except Exception:
        return {"allowed": False, "risk_score": 100, "needs_approval": True,
                "reason": "contract evaluation failed — fail-closed",
                "reversible": False}


def enforce_invariants() -> Dict[str, Any]:
    """Run a global invariant health check (no specific change).

    Fail-closed: if the module is missing the check is skipped, but
    if the call fails, invariants are treated as violated.
    """
    try:
        from governance.safety_invariants import enforce_invariants as _ei
        return _ei(None)
    except ImportError:
        return {"passed": False,
                "violations": [{"invariant": "SYSTEM", "detail": "safety_invariants module missing — fail-closed"}],
                "checked": 0}
    except Exception:
        return {"passed": False,
                "violations": [{"invariant": "SYSTEM", "detail": "invariant check failed — fail-closed"}],
                "checked": 0}


# ------------------------------------------------------------------
# Circuit breakers, kill switch, stabilise
# ------------------------------------------------------------------

def apply_circuit_breakers() -> Dict[str, Any]:
    """Evaluate whether circuit breakers should trip.

    Trips if governance health is critically degraded. When tripped,
    notifies the operator with a suggested recovery path. The recovery
    suggestion is marked with an accuracy caveat since the system may
    be in a degraded state when generating it.
    """
    global _circuit_breaker_tripped
    with _kernel_state_lock:
        health = compute_governance_health()
        score = health.get("governance_score", 100)
        if score < 20 and not _circuit_breaker_tripped:
            _circuit_breaker_tripped = True
        else:
            return {
                "tripped": _circuit_breaker_tripped,
                "score": score,
                "governance_score": score,
                "reason": "no action taken",
                "recovery_suggestion": None,
            }

    _log_kernel("circuit_breaker_tripped", {}, health)

    recovery = _suggest_recovery_path(health)

    try:
        from runtime.notification_hooks import (
            notify_escalation_recommended,
        )
        notify_escalation_recommended(
            3,
            f"GOVERNANCE CIRCUIT BREAKER TRIPPED — score {score}/100. "
            f"All changes are paused until operator resets the breaker.\n\n"
            f"Suggested recovery path (CAVEAT: system is in degraded "
            f"state — verify suggestions independently before acting):\n"
            f"{recovery['description']}\n\n"
            f"To reset: use 'reset circuit breaker' command.",
        )
    except (ImportError, Exception):
        pass

    try:
        from runtime.logging_manager import log_event
        log_event(
            "circuit_breaker_tripped",
            f"Governance CB tripped at score {score}/100",
            {"health": health, "recovery": recovery},
        )
    except (ImportError, Exception):
        pass

    return {
        "tripped": True,
        "reason": "governance score below threshold",
        "score": score,
        "governance_score": score,
        "recovery_suggestion": recovery,
    }


def _suggest_recovery_path(health: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a suggested recovery path for the operator.

    WARNING: This runs while the system is degraded. The suggestion
    is best-effort and should be verified by the operator.
    """
    steps: List[str] = []
    confidence = "high"

    if health.get("kill_switch"):
        steps.append(
            "1. Kill switch is active. If intentional, no further action. "
            "If unintentional, deactivate with 'deactivate kill switch'."
        )
        confidence = "medium"

    if health.get("stabilise_mode"):
        steps.append(
            "2. Stabilise mode is active — only governance meta-changes "
            "are permitted. Deactivate with 'deactivate stabilise mode' "
            "once the system is stable."
        )

    # Check drift
    try:
        from governance.drift_detector import compute_drift_report
        drift = compute_drift_report()
        avg_drift = drift.get("average_drift_score", 0)
        if avg_drift > 20:
            steps.append(
                f"3. Identity drift is elevated (avg score: {avg_drift:.1f}). "
                f"Review posture alignment and expression coherence. "
                f"Consider switching to DEFENSIVE mode temporarily."
            )
            confidence = "medium"
    except Exception:
        steps.append(
            "3. Unable to assess drift state — drift_detector unavailable. "
            "Manual inspection of posture and expression state recommended."
        )
        confidence = "low"

    if not steps:
        steps.append(
            "No specific degradation source identified. Try resetting "
            "the circuit breaker with 'reset circuit breaker' and monitor."
        )

    steps.append(
        "Final step: Reset the circuit breaker with 'reset circuit breaker' "
        "once root cause is addressed."
    )

    return {
        "steps": steps,
        "description": "\n".join(steps),
        "confidence": confidence,
        "caveat": (
            "This recovery path was generated while the system was in a "
            "degraded state. Verify each step independently before acting."
        ),
    }


def reset_circuit_breaker(reason: str = "operator_reset") -> Dict[str, Any]:
    global _circuit_breaker_tripped
    with _kernel_state_lock:
        _circuit_breaker_tripped = False
    _log_kernel("circuit_breaker_reset", {}, {"reason": reason})
    return {"success": True, "reason": reason}


def activate_kill_switch(reason: str = "operator") -> Dict[str, Any]:
    global _kill_switch_active
    with _kernel_state_lock:
        _kill_switch_active = True
    _log_kernel("kill_switch_activated", {}, {"reason": reason})

    try:
        from runtime.notification_hooks import notify_system_locked
        notify_system_locked()
    except (ImportError, Exception):
        pass
    try:
        from runtime.notification_hooks import notify_escalation_recommended
        notify_escalation_recommended(
            3,
            f"KILL SWITCH ACTIVATED — reason: {reason}. "
            f"All changes are blocked. Deactivate with "
            f"'deactivate kill switch' when safe.",
        )
    except (ImportError, Exception):
        pass
    try:
        from runtime.logging_manager import log_event
        log_event("kill_switch_activated", f"Kill switch ON: {reason}")
    except (ImportError, Exception):
        pass

    return {"success": True, "active": True, "reason": reason}


def deactivate_kill_switch(reason: str = "operator") -> Dict[str, Any]:
    global _kill_switch_active
    with _kernel_state_lock:
        _kill_switch_active = False
    _log_kernel("kill_switch_deactivated", {}, {"reason": reason})

    try:
        from runtime.notification_hooks import notify_system_unlocked
        notify_system_unlocked()
    except (ImportError, Exception):
        pass
    try:
        from runtime.logging_manager import log_event
        log_event("kill_switch_deactivated", f"Kill switch OFF: {reason}")
    except (ImportError, Exception):
        pass

    return {"success": True, "active": False, "reason": reason}


def activate_stabilise_mode(reason: str = "operator") -> Dict[str, Any]:
    global _stabilise_mode
    with _kernel_state_lock:
        _stabilise_mode = True
    _log_kernel("stabilise_activated", {}, {"reason": reason})
    return {"success": True, "active": True, "reason": reason}


def deactivate_stabilise_mode(reason: str = "operator") -> Dict[str, Any]:
    global _stabilise_mode
    with _kernel_state_lock:
        _stabilise_mode = False
    _log_kernel("stabilise_deactivated", {}, {"reason": reason})
    return {"success": True, "active": False, "reason": reason}


# ------------------------------------------------------------------
# Health & state
# ------------------------------------------------------------------

def compute_governance_health() -> Dict[str, Any]:
    """Compute an overall governance health score (0-100)."""
    with _kernel_state_lock:
        ks = _kill_switch_active
        cb = _circuit_breaker_tripped
        sm = _stabilise_mode

    score = 100.0
    if ks:
        score -= 40
    if cb:
        score -= 30
    if sm:
        score -= 10

    try:
        from governance.drift_detector import compute_drift_report
        drift = compute_drift_report()
        total_drift = drift.get("total_drift_score", 0)
        score -= min(30, total_drift * 0.3)
    except Exception:
        score -= 15

    return {
        "governance_score": round(max(0, min(100, score)), 1),
        "kill_switch": ks,
        "circuit_breaker": cb,
        "stabilise_mode": sm,
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
        "kill_switch": health["kill_switch"],
        "circuit_breaker": health["circuit_breaker"],
        "stabilise_mode": health["stabilise_mode"],
        "recent_decisions": get_kernel_log(5),
        "timestamp": time.time(),
    }


def get_kernel_log(limit: int = 20) -> List[Dict[str, Any]]:
    with _kernel_state_lock:
        return list(_KERNEL_LOG[-limit:])


def reset_kernel(reason: str = "operator_reset") -> Dict[str, Any]:
    """Reset all kernel state to defaults."""
    global _circuit_breaker_tripped, _kill_switch_active, _stabilise_mode
    with _kernel_state_lock:
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
    extra.pop("allowed", None)
    extra.pop("reason", None)
    return {
        "allowed": False,
        "reason": reason,
        "risk_score": extra.pop("risk_score", 100),
        "needs_approval": extra.pop("needs_approval", True),
        "reversible": extra.pop("reversible", False),
        **extra,
    }


def _log_kernel(action: str, request: Dict[str, Any],
                result: Dict[str, Any]) -> None:
    with _kernel_state_lock:
        _KERNEL_LOG.append({
            "action": action,
            "change_type": request.get("type", ""),
            "allowed": result.get("allowed"),
            "reason": result.get("reason", ""),
            "timestamp": time.time(),
        })
        if len(_KERNEL_LOG) > _MAX_LOG:
            _KERNEL_LOG[:] = _KERNEL_LOG[-_MAX_LOG:]
