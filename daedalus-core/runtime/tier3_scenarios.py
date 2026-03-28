# runtime/tier3_scenarios.py
"""
Tier-3 scenario presets.

A scenario preset is a named, operator-triggered generator that
selects a runbook template, provides sensible default parameters,
and merges any operator-supplied overrides before instantiating a
concrete runbook.  Scenarios never auto-execute the resulting
runbook, never auto-activate profiles, and never bypass governance.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from runtime.tier3_runbook_templates import (
    create_template,
    get_template,
    instantiate_template,
    list_templates,
)


# ------------------------------------------------------------------
# Scenario registry
# ------------------------------------------------------------------

_SCENARIO_REGISTRY: Dict[str, Dict[str, Any]] = {}
_scenario_lock = threading.Lock()


def _register_scenario(
    name: str,
    description: str,
    template_name: str,
    parameter_schema: Dict[str, Any],
    step_blueprints: List[Dict[str, Any]],
    default_parameters: Dict[str, Any],
) -> None:
    """Register a built-in scenario preset (called at module load)."""
    _SCENARIO_REGISTRY[name] = {
        "name": name,
        "description": description,
        "template_name": template_name,
        "parameter_schema": parameter_schema,
        "step_blueprints": step_blueprints,
        "default_parameters": default_parameters,
        "template_id": None,
    }


def list_scenarios() -> List[Dict[str, Any]]:
    return [
        {"name": s["name"], "description": s["description"],
         "template_id": s.get("template_id")}
        for s in _SCENARIO_REGISTRY.values()
    ]


def get_scenario(name: str) -> Optional[Dict[str, Any]]:
    return _SCENARIO_REGISTRY.get(name)


def _ensure_template(scenario: Dict[str, Any]) -> str:
    """Lazily create the backing template the first time a scenario runs."""
    with _scenario_lock:
        if scenario.get("template_id"):
            t = get_template(scenario["template_id"])
            if t is not None:
                return scenario["template_id"]

        t = create_template(
            name=scenario["template_name"],
            description=scenario["description"],
            parameter_schema=scenario["parameter_schema"],
            step_blueprints=scenario["step_blueprints"],
        )
        scenario["template_id"] = t["template_id"]
        return t["template_id"]


def run_scenario(
    name: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Instantiate a runbook from a scenario preset.

    Merges default_parameters with operator-supplied overrides, then
    calls instantiate_template.  The resulting runbook is in draft
    status — execution is always a separate, operator-triggered step.
    """
    scenario = _SCENARIO_REGISTRY.get(name)
    if scenario is None:
        return {"error": True, "reason": f"scenario '{name}' not found"}

    template_id = _ensure_template(scenario)

    merged_params = {**scenario["default_parameters"], **(overrides or {})}

    result = instantiate_template(template_id, merged_params)
    if result.get("error"):
        return result

    result["scenario_origin"] = {
        "scenario_name": name,
        "overrides": overrides or {},
    }
    return result


def clear_tier3_scenarios() -> None:
    """Reset scenario template_id links (for testing only)."""
    for s in _SCENARIO_REGISTRY.values():
        s["template_id"] = None


# ------------------------------------------------------------------
# Built-in scenario presets
# ------------------------------------------------------------------

_register_scenario(
    name="maintenance_window",
    description="Activate a profile, evaluate policies, run adaptive insights, "
                "and prepare a plan for execution.",
    template_name="maintenance_window_template",
    parameter_schema={
        "required": ["profile_id"],
        "properties": {
            "profile_id": {"type": "string", "description": "Profile to activate"},
            "plan_id": {"type": "string", "description": "Plan to execute (optional)",
                        "default": ""},
        },
    },
    step_blueprints=[
        {"type": "set_profile", "profile_id": "${profile_id}"},
        {"type": "evaluate_policies_once"},
        {"type": "generate_adaptive_insights"},
    ],
    default_parameters={},
)


_register_scenario(
    name="policy_refresh",
    description="Evaluate policies, generate adaptive insights, and leave "
                "all artifacts in draft/pending state for operator review.",
    template_name="policy_refresh_template",
    parameter_schema={
        "required": [],
        "properties": {},
    },
    step_blueprints=[
        {"type": "evaluate_policies_once"},
        {"type": "evaluate_policies_scheduled_once"},
        {"type": "generate_adaptive_insights"},
    ],
    default_parameters={},
)


_register_scenario(
    name="migration_review",
    description="Evaluate policies and generate adaptive insights to prepare "
                "migration proposals for operator approval.",
    template_name="migration_review_template",
    parameter_schema={
        "required": [],
        "properties": {},
    },
    step_blueprints=[
        {"type": "evaluate_policies_once"},
        {"type": "generate_adaptive_insights"},
    ],
    default_parameters={},
)
