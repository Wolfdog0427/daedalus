# knowledge/proposal_action_planner.py

"""
Proposal Action Planner

This module converts a proposal into concrete planned_actions.
It uses safe, template-driven transformations such as:
- replace_snippet
- insert_after
- insert_before

This is the core of autonomous self-healing.
"""

from __future__ import annotations

from typing import Dict, Any, List


def generate_actions_for_proposal(proposal: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given a proposal, return a list of planned_actions.

    Each action is safe, explicit, and template-driven.
    """

    subsystem = proposal.get("subsystem")
    risk = proposal.get("risk_level")
    drift = proposal.get("drift_context", {})
    diag = proposal.get("diagnostics_summary", {})

    actions: List[Dict[str, Any]] = []

    # ---------------------------------------------------------
    # Example rule 1: test_module.py auto-fix
    # ---------------------------------------------------------
    if subsystem == "test_module":
        actions.append({
            "type": "edit_file",
            "path": "test_module.py",
            "transform": {
                "kind": "replace_snippet",
                "old": "OLD",
                "new": "NEW",
            },
        })
        return actions

    # ---------------------------------------------------------
    # Example rule 2: drift-related fix for any subsystem
    # ---------------------------------------------------------
    if drift.get("drift_level") == "high":
        actions.append({
            "type": "edit_file",
            "path": f"{subsystem}.py",
            "transform": {
                "kind": "replace_snippet",
                "old": "TODO",
                "new": "FIXME_HIGH_DRIFT",
            },
        })
        return actions

    # ---------------------------------------------------------
    # Example rule 3: subsystem risk-based fix
    # ---------------------------------------------------------
    if risk == "medium":
        actions.append({
            "type": "edit_file",
            "path": f"{subsystem}.py",
            "transform": {
                "kind": "replace_snippet",
                "old": "pass",
                "new": "print('Auto-heal applied')",
            },
        })
        return actions

    # ---------------------------------------------------------
    # Default: no-op (proposal still valid, but no auto-fix)
    # ---------------------------------------------------------
    return actions
