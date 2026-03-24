# runtime/repl_context.py

from typing import Any, Dict

from runtime.background_self_test import run_background_self_test
from runtime.watch_monitor import analyze_last_action_for_watch_anomalies
from runtime.health_dashboard import render_health_dashboard
from runtime.system_doctor import run_system_doctor
from runtime.pretty import (
    pretty_debug_state,
    pretty_debug_goals,
    pretty_debug_steps,
    pretty_debug_raw,
)
from runtime.debug_tools import (
    debug_last,
    debug_state_diff,
    debug_context,
    debug_timing_summary,
    debug_history,
    debug_context_trace,
    debug_watch_alerts,
    debug_semantic_contextual,
)


class REPLContext:
    def __init__(
        self,
        state: Dict[str, Any],
        execution,
        goal_manager,
        store,
        plan_renderer,
        dashboard,
        plan_mode: str,
        dashboard_sort: str,
        dashboard_filter: str,
        debug_state,
        context_resolver,
        contextual_resolver,
    ):
        self.state = state
        self.execution = execution
        self.goal_manager = goal_manager
        self.store = store
        self.plan_renderer = plan_renderer
        self.dashboard = dashboard
        self.plan_mode = plan_mode
        self.dashboard_sort = dashboard_sort
        self.dashboard_filter = dashboard_filter
        self.debug_state = debug_state
        self.context_resolver = context_resolver
        self.contextual_resolver = contextual_resolver

    # ------------------------------------------------------------
    # GOALS / DASHBOARD
    # ------------------------------------------------------------
    def show_goals(self) -> str:
        goals = self.state.get("goals_tree", [])
        active = self.state.get("active_goal_id")
        return self.dashboard.render_dashboard(
            goals,
            active,
            mode=self.plan_mode,
            sort_by=self.dashboard_sort,
            filter_by=self.dashboard_filter,
        )

    # ------------------------------------------------------------
    # PLAN RENDERING
    # ------------------------------------------------------------
    def show_plan(self) -> str:
        active = self.state.get("active_goal_id")
        if not active:
            return "No active goal."

        goals = self.state.get("goals_tree", [])
        steps = self.state.get("steps", [])

        goal = next((g for g in goals if g.get("id") == active), None)
        if not goal:
            return "Active goal not found."

        goal_steps = [s for s in steps if s.get("goal_id") == active]

        return self.plan_renderer.render_plan(
            goal,
            goal_steps,
            mode=self.plan_mode,
        )

    def show_next_step(self) -> str:
        active = self.state.get("active_goal_id")
        if not active:
            return "No active goal."

        steps = self.state.get("steps", [])
        for s in steps:
            if s.get("goal_id") == active and not s.get("done"):
                return f"Next step: [{s['id']}] {s['text']}"

        return "No remaining steps."

    # ------------------------------------------------------------
    # SYSTEM HEALTH / DOCTOR
    # ------------------------------------------------------------
    def system_health(self) -> str:
        return render_health_dashboard()

    def run_doctor(self) -> str:
        lines = run_system_doctor(auto=False)
        return "\n".join(f"[doctor] {line}" for line in lines)

    # ------------------------------------------------------------
    # GOAL ARCHIVING
    # ------------------------------------------------------------
    def archive_goal(self, gid: int) -> str:
        goals = self.state.get("goals_tree", [])
        for g in goals:
            if g.get("id") == gid:
                g["archived"] = True
                break
        else:
            return f"No goal with id {gid}."

        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return f"Goal {gid} archived."

    def unarchive_goal(self, gid: int) -> str:
        goals = self.state.get("goals_tree", [])
        for g in goals:
            if g.get("id") == gid:
                g["archived"] = False
                break
        else:
            return f"No goal with id {gid}."

        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return f"Goal {gid} unarchived."

    # ------------------------------------------------------------
    # GOALS DASHBOARD CONTROLS
    # ------------------------------------------------------------
    def set_goals_sort(self, mode: str) -> str:
        if mode not in ("name", "progress", "created"):
            return "Invalid goals sort. Use: name, progress, or created."
        self.dashboard_sort = mode
        return f"Goals sort set to: {mode}"

    def set_goals_filter(self, flt: str) -> str:
        if flt not in ("all", "active", "completed", "in_progress", "archived"):
            return "Invalid goals filter. Use: all, active, completed, in_progress, archived."
        self.dashboard_filter = flt
        return f"Goals filter set to: {flt}"

    # ------------------------------------------------------------
    # PLAN MODE
    # ------------------------------------------------------------
    def show_plan_mode(self) -> str:
        return f"Current plan mode: {self.plan_mode}"

    def set_plan_mode(self, mode: str) -> str:
        if mode not in ("pretty", "tree", "compact"):
            return "Invalid plan mode. Use: pretty, tree, or compact."
        self.plan_mode = mode
        return f"Plan mode set to: {mode}"

    # ------------------------------------------------------------
    # CHECKPOINTS
    # ------------------------------------------------------------
    def save_checkpoint(self, name: str) -> str:
        msg = self.store.save_checkpoint(name)
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    def restore_checkpoint(self, name: str) -> str:
        msg = self.store.restore_checkpoint(name) or f"No checkpoint named '{name}'."
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    def list_checkpoints(self) -> str:
        cps = self.store.list_checkpoints()
        if not cps:
            return "(no checkpoints)"
        lines = ["Checkpoints:"]
        lines.extend(f"  - {c}" for c in cps)
        return "\n".join(lines)

    # ------------------------------------------------------------
    # WATCHPOINTS
    # ------------------------------------------------------------
    def add_watchpoint(self, path: str) -> str:
        msg = self.store.add_watchpoint(path)
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    def remove_watchpoint(self, path: str) -> str:
        msg = self.store.remove_watchpoint(path)
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    def list_watchpoints(self) -> str:
        wps = self.store.list_watchpoints()
        if not wps:
            return "(no watchpoints)"
        lines = ["Watchpoints:"]
        lines.extend(f"  - {w}" for w in wps)
        return "\n".join(lines)

    # ------------------------------------------------------------
    # UNDO / REDO
    # ------------------------------------------------------------
    def undo(self) -> str:
        msg = self.store.undo() or "Nothing to undo."
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    def redo(self) -> str:
        msg = self.store.redo() or "Nothing to redo."
        self.store.save()
        run_background_self_test()
        analyze_last_action_for_watch_anomalies()
        return msg

    # ------------------------------------------------------------
    # DEBUG COCKPIT
    # ------------------------------------------------------------
    def debug_last(self) -> str:
        last = self.store.history[-1] if self.store.history else None
        return debug_last(last)

    def debug_state_diff(self) -> str:
        if len(self.store.history) < 1:
            return "No history to diff."
        entry = self.store.history[-1]
        return debug_state_diff(entry.get("state_before", {}), entry.get("state", {}))

    def debug_context(self) -> str:
        if len(self.store.history) < 1:
            return "No history."
        entry = self.store.history[-1]
        before = entry.get("command_before", {})
        after = entry.get("command", {})
        return debug_context(before, after)

    def debug_timing(self) -> str:
        if len(self.store.history) < 1:
            return "No timing info."
        entry = self.store.history[-1]
        timing = entry.get("timing", {})
        return debug_timing_summary(timing)

    def debug_history(self) -> str:
        return debug_history(self.store.history)

    def debug_context_trace(self) -> str:
        if len(self.store.history) < 1:
            return "No context trace."
        entry = self.store.history[-1]
        trace = entry.get("context_trace", [])
        return debug_context_trace(trace)

    def debug_watch_alerts(self) -> str:
        last = self.store.history[-1] if self.store.history else None
        return debug_watch_alerts(last)

    def debug_semantic_contextual(self) -> str:
        if not self.store.history:
            return "No history."

        entry = self.store.history[-1]

        nlu_cmd = entry.get("nlu_cmd", {})
        contextual_trace = entry.get("context_trace", [])
        before_cmd = entry.get("command_before", {})
        after_cmd = entry.get("command", {})

        return debug_semantic_contextual(
            nlu_cmd,
            contextual_trace,
            before_cmd,
            after_cmd,
        )

    # ------------------------------------------------------------
    # SIMPLE DEBUG VIEWS
    # ------------------------------------------------------------
    def debug_goals_view(self) -> str:
        return pretty_debug_goals(self.state)

    def debug_steps_view(self) -> str:
        return pretty_debug_steps(self.state)

    def debug_state_view(self) -> str:
        return pretty_debug_state(self.state)

    def debug_raw_view(self) -> str:
        return pretty_debug_raw(self.state)


# ------------------------------------------------------------
# CONTEXT BUILDER (REQUIRED BY REPL)
# ------------------------------------------------------------

def build_context(
    state,
    execution,
    goal_manager,
    store,
    plan_renderer,
    dashboard,
    plan_mode,
    dashboard_sort,
    dashboard_filter,
    debug_state,
    context_resolver,
    contextual_resolver,
):
    """
    Factory function used by the REPL to construct a REPLContext.
    Mirrors the REPLContext constructor exactly.
    """
    return REPLContext(
        state=state,
        execution=execution,
        goal_manager=goal_manager,
        store=store,
        plan_renderer=plan_renderer,
        dashboard=dashboard,
        plan_mode=plan_mode,
        dashboard_sort=dashboard_sort,
        dashboard_filter=dashboard_filter,
        debug_state=debug_state,
        context_resolver=context_resolver,
        contextual_resolver=contextual_resolver,
    )
