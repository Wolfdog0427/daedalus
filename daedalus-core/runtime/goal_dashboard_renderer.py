"""
Goal Dashboard Renderer 2.0

Features:
    - color output
    - progress summaries
    - pretty / compact / tree modes
    - sorting (name, progress, created)
    - filtering (all, active, completed, in_progress, archived)
    - archived marking
    - summary hooks
    - dependency hints (blocked/unblocked)
"""

from typing import List, Dict, Any, Optional


class GoalDashboardRenderer:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[90m"
    RESET = "\033[0m"

    def render_dashboard(
        self,
        goals: List[Dict[str, Any]],
        active_goal_id: Optional[int],
        mode: str = "pretty",
        sort_by: str = "created",
        filter_by: str = "all",
    ) -> str:
        if not goals:
            return "No goals yet."

        goals = self._apply_filter(goals, filter_by)
        if not goals:
            return f"No goals match filter: {filter_by}"

        goals = self._apply_sort(goals, sort_by)

        if mode == "tree":
            return self._render_tree(goals, active_goal_id, sort_by, filter_by)

        if mode == "compact":
            return self._render_compact(goals, active_goal_id, sort_by, filter_by)

        return self._render_pretty(goals, active_goal_id, sort_by, filter_by)

    # ----------------- filtering & sorting -----------------

    def _apply_filter(self, goals, filter_by: str):
        if filter_by == "all":
            return goals

        filtered = []
        for g in goals:
            steps = g.get("steps", [])
            done = sum(1 for s in steps if s.get("done"))
            total = len(steps)
            archived = g.get("archived", False)

            if filter_by == "archived" and archived:
                filtered.append(g)
            elif filter_by == "active" and not archived:
                filtered.append(g)
            elif filter_by == "completed" and total > 0 and done == total and not archived:
                filtered.append(g)
            elif filter_by == "in_progress" and total > 0 and 0 < done < total and not archived:
                filtered.append(g)

        return filtered

    def _apply_sort(self, goals, sort_by: str):
        if sort_by == "name":
            return sorted(goals, key=lambda g: g.get("name", "").lower())

        if sort_by == "progress":
            def key(g):
                steps = g.get("steps", [])
                total = len(steps)
                done = sum(1 for s in steps if s.get("done"))
                pct = (done / total) if total else 0.0
                return -pct
            return sorted(goals, key=key)

        # default: created (assume id is roughly creation order)
        return sorted(goals, key=lambda g: g.get("id", 0))

    # ----------------- shared helpers -----------------

    def _progress_tuple(self, g):
        steps = g.get("steps", [])
        total = len(steps)
        done = sum(1 for s in steps if s.get("done"))
        pct = int((done / total) * 100) if total else 0
        return done, total, pct

    def _status_label(self, g):
        archived = g.get("archived", False)
        done, total, pct = self._progress_tuple(g)

        if archived:
            return f"{self.DIM}archived{self.RESET}"
        if total == 0:
            return f"{self.DIM}empty{self.RESET}"
        if done == total:
            return f"{self.GREEN}completed{self.RESET}"
        if done == 0:
            return f"{self.YELLOW}not started{self.RESET}"
        return f"{self.YELLOW}in progress{self.RESET}"

    def _summary_line(self, g):
        summary = g.get("summary")
        if summary:
            return f"{self.DIM}{summary}{self.RESET}"
        return ""

    def _dependency_hint(self, g):
        # simple hook: if any step has "blocked" flag, show blocked
        steps = g.get("steps", [])
        blocked = any(s.get("blocked") for s in steps)
        if blocked:
            return f"{self.RED} (blocked){self.RESET}"
        return ""

    def _header(self, sort_by: str, filter_by: str, title: str = "Goals Overview"):
        meta = f"{self.DIM}[sort: {sort_by}, filter: {filter_by}]{self.RESET}"
        return f"{self.CYAN}🎯 {title}{self.RESET} {meta}"

    # ----------------- pretty mode -----------------

    def _render_pretty(self, goals, active_goal_id, sort_by, filter_by):
        lines = [self._header(sort_by, filter_by)]

        for g in goals:
            gid = g.get("id")
            name = g.get("name", "(unnamed goal)")
            done, total, pct = self._progress_tuple(g)
            active_mark = f"{self.GREEN}★{self.RESET}" if gid == active_goal_id else " "
            status = self._status_label(g)
            dep = self._dependency_hint(g)
            summary = self._summary_line(g)

            lines.append(
                f"{active_mark} {name}{dep} — "
                f"{self.DIM}{done}/{total} ({pct}%) {status}{self.RESET}"
            )
            if summary:
                lines.append(f"    {summary}")

        return "\n".join(lines)

    # ----------------- compact mode -----------------

    def _render_compact(self, goals, active_goal_id, sort_by, filter_by):
        lines = [self._header(sort_by, filter_by, title="Goals")]

        for g in goals:
            gid = g.get("id")
            name = g.get("name", "(unnamed goal)")
            _, _, pct = self._progress_tuple(g)
            mark = f"{self.GREEN}★{self.RESET}" if gid == active_goal_id else " "
            status = self._status_label(g)
            dep = self._dependency_hint(g)

            lines.append(f"{mark} [{gid}] {name}{dep} — {pct}% {status}")

        return "\n".join(lines)

    # ----------------- tree mode -----------------

    def _render_tree(self, goals, active_goal_id, sort_by, filter_by):
        lines = [self._header(sort_by, filter_by, title="Goals")]

        for i, g in enumerate(goals):
            prefix = "└── " if i == len(goals) - 1 else "├── "
            gid = g.get("id")
            name = g.get("name", "(unnamed goal)")
            _, _, pct = self._progress_tuple(g)
            active = f"{self.GREEN}★{self.RESET}" if gid == active_goal_id else " "
            status = self._status_label(g)
            dep = self._dependency_hint(g)

            lines.append(f"{prefix}{active} {name}{dep} ({pct}%) {status}")

        return "\n".join(lines)
