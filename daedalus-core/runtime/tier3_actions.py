# runtime/tier3_actions.py
"""
Tier-3 action type definitions.

Each action type describes a class of high-impact operation with:
- required payload fields
- a reversibility flag
- a human-readable description

This module validates payloads against their type schema but never
executes anything.  Execution remains stubbed in tier3_execution.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

TIER3_ACTION_TYPES: Dict[str, Dict[str, Any]] = {
    "update_setting": {
        "description": "Change a runtime setting value",
        "required_fields": ["key", "new_value"],
        "reversible": True,
    },
    "retire_action": {
        "description": "Remove an action from its tier registry",
        "required_fields": ["action_name", "tier"],
        "reversible": True,
    },
    "replace_action": {
        "description": "Replace one action with another in a tier registry",
        "required_fields": ["old_action_name", "new_action", "tier"],
        "reversible": True,
    },
    "apply_migration": {
        "description": "Apply a structural migration to in-memory state",
        "required_fields": ["migration_name", "migration_steps"],
        "reversible": False,
    },
}


def get_tier3_action_types() -> Dict[str, Dict[str, Any]]:
    """Return all registered action type definitions."""
    return dict(TIER3_ACTION_TYPES)


def validate_tier3_payload(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check that *payload* satisfies the schema for *action_type*.

    Returns {"valid": bool, "reason": str, "action_type": str}.
    """
    if action_type not in TIER3_ACTION_TYPES:
        return {
            "valid": False,
            "reason": f"unknown action type '{action_type}'",
            "action_type": action_type,
        }

    spec = TIER3_ACTION_TYPES[action_type]
    missing = [f for f in spec["required_fields"] if f not in payload]
    if missing:
        return {
            "valid": False,
            "reason": f"missing required fields: {missing}",
            "action_type": action_type,
        }

    return {
        "valid": True,
        "reason": "payload valid",
        "action_type": action_type,
        "reversible": spec["reversible"],
    }


def describe_tier3_action(action_type: str, payload: Dict[str, Any]) -> str:
    """Human-readable description of what an action would do."""
    spec = TIER3_ACTION_TYPES.get(action_type)
    if spec is None:
        return f"Unknown action type: {action_type}"

    base = spec["description"]
    details = ", ".join(f"{k}={v}" for k, v in payload.items())
    rev = "reversible" if spec["reversible"] else "irreversible"
    return f"[{action_type}] {base} ({rev}): {details}"
