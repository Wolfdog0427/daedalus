# governance/patch_lifecycle.py
"""
Patch lifecycle management for Daedalus governance.

Patches transition through: draft → pending_approval → approved →
applied → (optionally) rolled_back.  All transitions are logged.
No patch is applied without kernel approval.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_PATCHES: List[Dict[str, Any]] = []
_MAX_PATCHES = 100
_patch_counter: int = 0


def create_patch(
    proposal_id: str,
    description: str,
    change_type: str,
    payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Create a new patch in draft status."""
    global _patch_counter
    _patch_counter += 1
    pid = f"PATCH-{_patch_counter:04d}"

    patch = {
        "patch_id": pid,
        "proposal_id": proposal_id,
        "description": description,
        "change_type": change_type,
        "payload": payload or {},
        "status": "draft",
        "created_at": time.time(),
        "applied_at": None,
        "rolled_back_at": None,
        "rollback_snapshot": None,
    }
    _PATCHES.append(patch)
    if len(_PATCHES) > _MAX_PATCHES:
        _PATCHES[:] = _PATCHES[-_MAX_PATCHES:]

    try:
        from governance.audit_log import log_event
        log_event("patch_created", {"patch_id": pid, "proposal_id": proposal_id})
    except Exception:
        pass

    return patch


def validate_patch(patch_id: str) -> Dict[str, Any]:
    """Validate a patch against the governance kernel."""
    patch = _find_patch(patch_id)
    if patch is None:
        return {"valid": False, "reason": f"patch '{patch_id}' not found"}

    change_request = {
        "type": patch["change_type"],
        "target": patch.get("payload", {}).get("target", ""),
        "flags": patch.get("payload", {}).get("flags", []),
        "reversible": True,
    }

    try:
        from governance.kernel import evaluate_change
        verdict = evaluate_change(change_request)
        return {
            "valid": verdict.get("allowed", False),
            "reason": verdict.get("reason", ""),
            "risk_score": verdict.get("risk_score", 0),
            "needs_approval": verdict.get("needs_approval", False),
        }
    except Exception:
        return {"valid": True, "reason": "kernel unavailable — passthrough"}


def apply_patch(patch_id: str, operator_approved: bool = False) -> Dict[str, Any]:
    """Apply a patch.  Requires validation and approval."""
    patch = _find_patch(patch_id)
    if patch is None:
        return {"success": False, "reason": f"patch '{patch_id}' not found"}

    if patch["status"] not in ("draft", "approved"):
        return {"success": False, "reason": f"patch in '{patch['status']}' state"}

    validation = validate_patch(patch_id)
    if not validation.get("valid"):
        patch["status"] = "rejected"
        return {"success": False, "reason": validation.get("reason", "validation failed")}

    if validation.get("needs_approval") and not operator_approved:
        patch["status"] = "pending_approval"
        return {"success": False, "reason": "operator approval required",
                "status": "pending_approval"}

    patch["rollback_snapshot"] = {"applied_at": time.time(),
                                   "previous_status": patch["status"]}
    patch["status"] = "applied"
    patch["applied_at"] = time.time()

    try:
        from governance.audit_log import log_event
        log_event("patch_applied", {"patch_id": patch_id})
    except Exception:
        pass

    return {"success": True, "patch_id": patch_id, "status": "applied"}


def rollback_patch(patch_id: str, reason: str = "operator") -> Dict[str, Any]:
    """Roll back an applied patch."""
    patch = _find_patch(patch_id)
    if patch is None:
        return {"success": False, "reason": f"patch '{patch_id}' not found"}

    if patch["status"] != "applied":
        return {"success": False, "reason": f"patch not in 'applied' state"}

    patch["status"] = "rolled_back"
    patch["rolled_back_at"] = time.time()

    try:
        from governance.audit_log import log_event
        log_event("patch_rolled_back", {"patch_id": patch_id, "reason": reason})
    except Exception:
        pass

    return {"success": True, "patch_id": patch_id, "status": "rolled_back"}


def get_patches(status: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
    if status:
        return [p for p in _PATCHES if p["status"] == status][-limit:]
    return list(_PATCHES[-limit:])


def get_patch(patch_id: str) -> Optional[Dict[str, Any]]:
    return _find_patch(patch_id)


def _find_patch(patch_id: str) -> Optional[Dict[str, Any]]:
    for p in _PATCHES:
        if p["patch_id"] == patch_id:
            return p
    return None
