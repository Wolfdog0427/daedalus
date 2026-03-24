"""
Branching plan generator.

Given a goal, propose multiple possible plan variants.
Currently symbolic and template-based.
"""

from typing import List, Dict, Any
from .stepgen import generate_hierarchical_steps


class BranchingEngine:
    def __init__(self):
        pass

    def generate_branches(self, goal_text: str) -> List[Dict[str, Any]]:
        base = generate_hierarchical_steps(goal_text)

        # For now, we create two simple variants:
        # - "Standard" (as generated)
        # - "Minimal" (fewer steps)
        standard = {
            "name": "Standard plan",
            "steps": base,
        }

        minimal_steps = base[:2] if len(base) > 2 else base
        minimal = {
            "name": "Minimal plan",
            "steps": minimal_steps,
        }

        return [standard, minimal]
