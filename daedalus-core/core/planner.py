"""
Symbolic planner (STRIPS-lite style).

For now, it:
- Accepts hierarchical steps
- Normalizes them into a flat execution plan
- Leaves room for future dependency logic
"""

from typing import List, Dict, Any


class SymbolicPlanner:
    def __init__(self):
        self.world_state = {}

    def set_world_state(self, state: Dict[str, Any]):
        self.world_state = state or {}

    def plan_from_hierarchical(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Given hierarchical steps:
        [
          {"step": "Identify clutter zones", "substeps": [...]},
          ...
        ]
        Return a flat ordered plan:
        [
          {"label": "Identify clutter zones", "type": "step"},
          {"label": "Desk surface", "type": "substep", "parent": "Identify clutter zones"},
          ...
        ]
        """
        plan: List[Dict[str, Any]] = []
        for s in steps:
            label = s.get("step", "").strip()
            if not label:
                continue
            plan.append({"label": label, "type": "step"})
            for sub in s.get("substeps", []):
                sub_label = str(sub).strip()
                if not sub_label:
                    continue
                plan.append({"label": sub_label, "type": "substep", "parent": label})
        return plan

    def reorder_if_needed(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Placeholder for future dependency-based reordering.
        Currently returns the plan as-is.
        """
        return plan

    def build_execution_plan(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flat = self.plan_from_hierarchical(steps)
        ordered = self.reorder_if_needed(flat)
        return ordered
