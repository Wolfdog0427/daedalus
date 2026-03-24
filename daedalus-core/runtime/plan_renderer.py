"""
Plan Renderer 2.0

Adds:
    - ANSI color output
    - pretty mode (default)
    - tree mode
    - compact mode
    - progress summary

Pure presentation layer.
"""

from typing import List, Dict, Any


class PlanRenderer:
    """
    Human-friendly renderer for goals and steps.
    """

    # ------------------------------------------------------------
    # ANSI COLORS
    # ------------------------------------------------------------
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    DIM = "\033[90m"
    RESET = "\033[0m"

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def render_plan(
        self,
        goal: Dict[str, Any],
        steps: List[Dict[str, Any]],
        mode: str = "pretty",
    ) -> str:
        if goal is None:
            return "No active goal."

        if mode == "tree":
            return self._render_tree(goal, steps)

        if mode == "compact":
            return self._render_compact(goal, steps)

        return self._render_pretty(goal, steps)

    # ------------------------------------------------------------
    # PRETTY MODE
    # ------------------------------------------------------------
    def _render_pretty(self, goal: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
        title = goal.get("name", "(unnamed goal)")
        line = "─" * len(title)

        header = f"{self.CYAN}🧭 {title}{self.RESET}\n{self.DIM}{line}{self.RESET}"

        progress = self._render_progress(steps)
        body = self._render_steps_pretty(steps)

        return f"{header}\n{progress}\n{body}"

    def _render_steps_pretty(self, steps: List[Dict[str, Any]]) -> str:
        if not steps:
            return "(no steps yet)"

        lines = []
        for step in steps:
            num = step.get("number", "?")
            desc = step.get("description", "(no description)")
            done = step.get("done", False)

            if done:
                check = f"{self.GREEN}✓{self.RESET}"
                desc_colored = f"{self.GREEN}{desc}{self.RESET}"
            else:
                check = f"{self.YELLOW}•{self.RESET}"
                desc_colored = f"{self.YELLOW}{desc}{self.RESET}"

            lines.append(f"{num}. [{check}] {desc_colored}")

        return "\n".join(lines)

    # ------------------------------------------------------------
    # TREE MODE
    # ------------------------------------------------------------
    def _render_tree(self, goal: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
        title = goal.get("name", "(unnamed goal)")
        header = f"{self.CYAN}{title}{self.RESET}"

        if not steps:
            return f"{header}\n(no steps yet)"

        lines = [header]

        for i, step in enumerate(steps):
            prefix = "└── " if i == len(steps) - 1 else "├── "
            num = step.get("number", "?")
            desc = step.get("description", "(no description)")
            done = step.get("done", False)

            if done:
                desc = f"{self.GREEN}{desc} ✓{self.RESET}"
            else:
                desc = f"{self.YELLOW}{desc}{self.RESET}"

            lines.append(f"{prefix}{num}. {desc}")

        return "\n".join(lines)

    # ------------------------------------------------------------
    # COMPACT MODE
    # ------------------------------------------------------------
    def _render_compact(self, goal: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
        title = goal.get("name", "(unnamed goal)")
        header = f"{self.CYAN}{title}{self.RESET}"

        if not steps:
            return f"{header}\n(no steps yet)"

        lines = [header]

        for step in steps:
            num = step.get("number", "?")
            desc = step.get("description", "(no description)")
            done = step.get("done", False)

            mark = "✓" if done else "•"
            color = self.GREEN if done else self.YELLOW

            lines.append(f"[{num}] {color}{desc}{self.RESET} {mark}")

        return "\n".join(lines)

    # ------------------------------------------------------------
    # PROGRESS SUMMARY
    # ------------------------------------------------------------
    def _render_progress(self, steps: List[Dict[str, Any]]) -> str:
        if not steps:
            return ""

        total = len(steps)
        done = sum(1 for s in steps if s.get("done"))
        pct = int((done / total) * 100)

        return f"{self.DIM}Progress: {done}/{total} steps completed ({pct}%) {self.RESET}"
