# knowledge/patch_applier.py

from __future__ import annotations

from typing import Any, Dict, List
import os
import json
from datetime import datetime

from knowledge.patch_actions import (
    apply_actions_in_sandbox,
    apply_actions_live,
    rollback_actions_live,
)
from knowledge.rollback_manager import (
    begin_transaction,
    snapshot_file,
    write_rollback_log,
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def apply_patch_in_sandbox(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run planned actions in a sandbox directory.
    Does NOT modify live code or configs.
    """
    tier = plan.get("tier")
    cycle_id = plan.get("cycle_id")
    proposal_id = plan.get("proposal_id")
    actions: List[Dict[str, Any]] = plan.get("planned_actions", [])

    sandbox_root = os.path.join(
        "/data/data/com.termux/files/usr/tmp",
        f"sho_sandbox_{cycle_id or 'unknown'}",
    )
    _ensure_dir(sandbox_root)

    result = apply_actions_in_sandbox(
        actions=actions,
        sandbox_root=sandbox_root,
        context={
            "tier": tier,
            "cycle_id": cycle_id,
            "proposal_id": proposal_id,
        },
    )

    report_path = os.path.join(sandbox_root, "sandbox_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": _now_iso(),
                "plan": plan,
                "result": result,
            },
            f,
            indent=2,
        )

    status = "success" if not result.get("errors") else "failed"

    return {
        "status": status,
        "details": {
            "sandbox_dir": sandbox_root,
            "errors": result.get("errors", []),
        },
    }


# ---------------------------------------------------------
# Post-Patch Validation Layer
# ---------------------------------------------------------

def validate_patch(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the effects of a successful live patch.

    Returns:
        {
            "status": "passed" | "failed",
            "errors": [...],
            "details": {...}
        }
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    # 1. Subsystem config integrity
    for action in plan.get("planned_actions", []):
        subsystem = action.get("target")
        if not subsystem:
            continue

        config_path = os.path.join("data", "subsystems", f"{subsystem}.json")
        if not os.path.exists(config_path):
            errors.append(f"{subsystem}: config missing after patch")
            continue

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            errors.append(f"{subsystem}: config unreadable after patch: {e}")
            continue

        if "tuning" not in config:
            errors.append(f"{subsystem}: missing tuning block after patch")

        details[subsystem] = {"config_ok": True}

    # 2. Subsystem import test
    for action in plan.get("planned_actions", []):
        subsystem = action.get("target")
        if not subsystem:
            continue

        try:
            __import__(subsystem)
        except Exception as e:
            errors.append(f"{subsystem}: import failed after patch: {e}")

    # 3. Drift/Stability sanity check (placeholder)
    drift = plan.get("drift", {})
    stability = plan.get("stability", {})

    if drift.get("score") is not None and drift["score"] < 0:
        errors.append("drift score became negative after patch")

    if stability.get("score") is not None and stability["score"] < 0:
        errors.append("stability score became negative after patch")

    if errors:
        return {
            "status": "failed",
            "errors": errors,
            "details": details,
        }

    return {
        "status": "passed",
        "errors": [],
        "details": details,
    }


# ---------------------------------------------------------
# Rollback helpers
# ---------------------------------------------------------

def _snapshot_subsystems_before(actions: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    For each target subsystem, create a rollback transaction directory
    and snapshot its current config (if any).
    Returns a mapping: subsystem -> rollback_path
    """
    subsystems = list({a.get("target") for a in actions if a.get("target")})
    rollback_paths: Dict[str, str] = {}

    for subsystem in subsystems:
        path = begin_transaction(subsystem)
        rollback_paths[subsystem] = path

        config_path = os.path.join("data", "subsystems", f"{subsystem}.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                snapshot_file(path, "before", json.load(f))
        else:
            snapshot_file(path, "before", {})

    return rollback_paths


def _snapshot_subsystems_after(rollback_paths: Dict[str, str]) -> None:
    """
    After a successful patch, snapshot the 'after' state for each subsystem.
    """
    for subsystem, path in rollback_paths.items():
        config_path = os.path.join("data", "subsystems", f"{subsystem}.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                snapshot_file(path, "after", json.load(f))


def _restore_from_snapshots(rollback_paths: Dict[str, str]) -> List[str]:
    """
    Restore each subsystem's config from its 'before' snapshot.
    Returns a list of rollback errors (if any).
    """
    errors: List[str] = []

    for subsystem, path in rollback_paths.items():
        before_path = os.path.join(path, "before.json")
        if not os.path.exists(before_path):
            errors.append(f"{subsystem}: missing before snapshot for rollback")
            continue

        try:
            with open(before_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            config_path = os.path.join("data", "subsystems", f"{subsystem}.json")
            _ensure_dir(os.path.dirname(config_path))
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            errors.append(f"{subsystem}: rollback failed: {e}")

    return errors


def apply_patch_live(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply actions to the live environment with rollback + validation.
    - Snapshots pre-patch state per subsystem
    - Applies actions
    - On failure, restores snapshots and logs rollback
    - On success, snapshots post-patch state, validates, and may rollback
    """
    actions: List[Dict[str, Any]] = plan.get("planned_actions", [])
    cycle_id = plan.get("cycle_id")
    proposal_id = plan.get("proposal_id")

    # 1) Snapshot before state
    rollback_paths = _snapshot_subsystems_before(actions)

    # 2) Apply live actions
    live_result = apply_actions_live(actions=actions, context=plan)
    live_errors = live_result.get("errors", [])

    if live_errors:
        # 3a) Restore from snapshots
        restore_errors = _restore_from_snapshots(rollback_paths)

        # 3b) Let action-specific rollback hooks run (if any)
        rollback_result = rollback_actions_live(actions=actions, context=plan)
        rollback_hook_errors = rollback_result.get("errors", [])

        all_errors = live_errors + restore_errors + rollback_hook_errors

        # 3c) Log rollback
        any_path = next(iter(rollback_paths.values()), None)
        if any_path:
            write_rollback_log(
                any_path,
                {
                    "timestamp": _now_iso(),
                    "cycle_id": cycle_id,
                    "proposal_id": proposal_id,
                    "errors": all_errors,
                    "rolled_back": True,
                    "validation_failed": False,
                },
            )

        return {
            "status": "failed",
            "details": {
                "phase": "live",
                "rolled_back": True,
                "errors": all_errors,
            },
        }

    # 3) Success path: snapshot after state
    _snapshot_subsystems_after(rollback_paths)

    # 4) Post-patch validation
    validation = validate_patch(plan)

    if validation["status"] == "failed":
        # Validation failed → rollback
        restore_errors = _restore_from_snapshots(rollback_paths)
        rollback_result = rollback_actions_live(actions=actions, context=plan)
        rollback_hook_errors = rollback_result.get("errors", [])

        all_errors = (
            validation["errors"]
            + restore_errors
            + rollback_hook_errors
        )

        any_path = next(iter(rollback_paths.values()), None)
        if any_path:
            write_rollback_log(
                any_path,
                {
                    "timestamp": _now_iso(),
                    "cycle_id": cycle_id,
                    "proposal_id": proposal_id,
                    "errors": all_errors,
                    "rolled_back": True,
                    "validation_failed": True,
                },
            )

        return {
            "status": "failed",
            "details": {
                "phase": "validation",
                "validation": validation,
                "rolled_back": True,
                "errors": all_errors,
            },
        }

    # 5) Log success (no rollback)
    for path in rollback_paths.values():
        write_rollback_log(
            path,
            {
                "timestamp": _now_iso(),
                "cycle_id": cycle_id,
                "proposal_id": proposal_id,
                "rolled_back": False,
                "validation_failed": False,
            },
        )

    return {
        "status": "success",
        "details": {
            "rolled_back": False,
            "validation": validation,
        },
    }


# Historical API name (orchestrator / SHO cycle callers using live apply)
apply_patch = apply_patch_live
