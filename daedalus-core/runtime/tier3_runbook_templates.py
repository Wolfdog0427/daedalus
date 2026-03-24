# runtime/tier3_runbook_templates.py
"""
Tier-3 runbook templates.

A template is a parameterized blueprint for generating concrete
runbooks.  Templates are read-only until instantiated: the
instantiation process validates parameters, substitutes placeholders,
and registers a new runbook in draft status.  No execution occurs.
"""

from __future__ import annotations

import copy
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional

_TIER3_TEMPLATE_REGISTRY: List[Dict[str, Any]] = []

_INSTANTIATION_LOG: List[Dict[str, Any]] = []


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

def create_template(
    name: str,
    description: str,
    parameter_schema: Dict[str, Any],
    step_blueprints: List[Dict[str, Any]],
) -> Dict[str, Any]:
    template = {
        "template_id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "parameter_schema": parameter_schema,
        "step_blueprints": step_blueprints,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _TIER3_TEMPLATE_REGISTRY.append(template)
    return template


def list_templates() -> List[Dict[str, Any]]:
    return list(_TIER3_TEMPLATE_REGISTRY)


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    for t in _TIER3_TEMPLATE_REGISTRY:
        if t["template_id"] == template_id:
            return t
    return None


def get_instantiation_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_INSTANTIATION_LOG[-limit:])


def clear_tier3_templates() -> None:
    """Reset template registry and log (for testing only)."""
    _TIER3_TEMPLATE_REGISTRY.clear()
    _INSTANTIATION_LOG.clear()


# ------------------------------------------------------------------
# Parameter validation & substitution
# ------------------------------------------------------------------

def _validate_parameters(
    schema: Dict[str, Any],
    parameters: Dict[str, Any],
) -> List[str]:
    """Return a list of validation error strings (empty means valid)."""
    errors: List[str] = []
    required = schema.get("required", [])
    props = schema.get("properties", {})

    for key in required:
        if key not in parameters:
            errors.append(f"missing required parameter '{key}'")

    for key in parameters:
        if key not in props:
            errors.append(f"unknown parameter '{key}'")

    for key, spec in props.items():
        if key not in parameters:
            continue
        expected_type = spec.get("type")
        value = parameters[key]
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"parameter '{key}' must be string, got {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"parameter '{key}' must be number, got {type(value).__name__}")
        elif expected_type == "list" and not isinstance(value, list):
            errors.append(f"parameter '{key}' must be list, got {type(value).__name__}")

    return errors


_PLACEHOLDER_RE = re.compile(r"\$\{(\w+)\}")


def _substitute(obj: Any, parameters: Dict[str, Any]) -> Any:
    """Recursively substitute ${param} placeholders in strings and dicts."""
    if isinstance(obj, str):
        def _replace(m: re.Match) -> str:
            key = m.group(1)
            val = parameters.get(key, m.group(0))
            return str(val) if not isinstance(val, str) else val

        result = _PLACEHOLDER_RE.sub(_replace, obj)
        for key, val in parameters.items():
            if result == str(val) and not isinstance(val, str):
                return val
        return result
    if isinstance(obj, dict):
        return {k: _substitute(v, parameters) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(item, parameters) for item in obj]
    return obj


# ------------------------------------------------------------------
# Instantiation
# ------------------------------------------------------------------

def instantiate_template(
    template_id: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate parameters, substitute placeholders, and register a
    concrete runbook in draft status.  Never executes the runbook.
    """
    parameters = parameters or {}

    try:
        from runtime.tier3_env_guardrails import check_template_instantiation
        gr = check_template_instantiation(template_id)
        if not gr.get("allowed"):
            reasons = gr.get("blocking_reasons", [])
            return {"error": True,
                    "reason": "; ".join(reasons) if reasons
                    else "blocked by guardrail"}
    except Exception:
        pass

    try:
        from runtime.tier3_environments import is_template_allowed
        if not is_template_allowed(template_id):
            return {"error": True,
                    "reason": f"template '{template_id}' not allowed by active environment"}
    except Exception:
        pass

    template = get_template(template_id)
    if template is None:
        return {"error": True, "reason": f"template '{template_id}' not found"}

    schema = template.get("parameter_schema", {})
    defaults = {k: v.get("default") for k, v in schema.get("properties", {}).items()
                if "default" in v}
    merged = {**defaults, **parameters}

    errors = _validate_parameters(schema, merged)
    if errors:
        return {"error": True, "reasons": errors}

    steps = _substitute(copy.deepcopy(template["step_blueprints"]), merged)

    from runtime.tier3_runbooks import create_runbook
    runbook = create_runbook(
        name=f"{template['name']} (from template)",
        description=template["description"],
        steps=steps,
    )

    if runbook.get("error"):
        return {"error": True, "reasons": runbook.get("reasons", [])}

    runbook["template_origin"] = {
        "template_id": template_id,
        "template_name": template["name"],
        "parameters": merged,
    }

    entry = {
        "template_id": template_id,
        "template_name": template["name"],
        "runbook_id": runbook["runbook_id"],
        "parameters": merged,
        "timestamp": time.time(),
    }
    _INSTANTIATION_LOG.append(entry)

    return runbook
