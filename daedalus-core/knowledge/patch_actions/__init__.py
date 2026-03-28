# knowledge/patch_actions/__init__.py

from __future__ import annotations

from typing import Any, Dict, List, Callable

from .subsystem_improvement import (
    sandbox_subsystem_improvement,
    live_subsystem_improvement,
    rollback_subsystem_improvement,
)

SandboxHandler = Callable[[Dict[str, Any], str, Dict[str, Any]], List[str]]
LiveHandler = Callable[[Dict[str, Any], Dict[str, Any]], List[str]]
RollbackHandler = Callable[[Dict[str, Any], Dict[str, Any]], List[str]]

_ALL_PATCH_ACTION_TYPES = (
    "subsystem_improvement",
    "refactor",
    "cleanup",
    "optimize",
    "improve",
    "explore",
    "restructure",
    "enhance",
    "rollback",
    "tighten",
    "repair",
    "verify",
)

SANDBOX_HANDLERS: Dict[str, SandboxHandler] = {
    t: sandbox_subsystem_improvement for t in _ALL_PATCH_ACTION_TYPES
}

LIVE_HANDLERS: Dict[str, LiveHandler] = {
    t: live_subsystem_improvement for t in _ALL_PATCH_ACTION_TYPES
}

ROLLBACK_HANDLERS: Dict[str, RollbackHandler] = {
    t: rollback_subsystem_improvement for t in _ALL_PATCH_ACTION_TYPES
}


def apply_actions_in_sandbox(
    actions: List[Dict[str, Any]],
    sandbox_root: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []

    for action in actions:
        action_type = action.get("type")
        handler = SANDBOX_HANDLERS.get(action_type)
        if handler is None:
            errors.append(f"{action_type}: Unknown action type: {action_type}")
            continue

        errs = handler(action, sandbox_root, context)
        errors.extend(errs)

    return {"errors": errors}


def apply_actions_live(
    actions: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []

    for action in actions:
        action_type = action.get("type")
        handler = LIVE_HANDLERS.get(action_type)
        if handler is None:
            errors.append(f"{action_type}: Unknown action type: {action_type}")
            continue

        errs = handler(action, context)
        errors.extend(errs)

    return {"errors": errors}


def rollback_actions_live(
    actions: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optional, action-specific rollback hooks.
    Central rollback (restoring snapshots) is handled in patch_applier;
    this is for extra cleanup if needed.
    """
    errors: List[str] = []

    for action in actions:
        action_type = action.get("type")
        handler = ROLLBACK_HANDLERS.get(action_type)
        if handler is None:
            continue
        errs = handler(action, context)
        errors.extend(errs)

    return {"errors": errors}
