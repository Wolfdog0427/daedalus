# runtime/execution.py
import json
from typing import Any, Dict, List, Optional

from runtime.pretty import (
    pretty_help,
    pretty_debug_state,
    pretty_debug_goals,
    pretty_debug_steps,
    pretty_debug_raw,
    pretty_debug_diff,
    pretty_debug_context,
    pretty_debug_nlu,
)
from runtime.history_timeline import pretty_debug_history
from runtime.debug_tools import (
    debug_last,
    debug_watch_history,
    debug_timing_summary,
    debug_semantic_contextual,
)
from runtime.nlu_debug import debug_nlu_pipeline
from runtime.health_dashboard import render_health_dashboard
from runtime.diagnostics_bootstrap import run_diagnostics
from governor.singleton import (
    format_governor_thresholds,
    get_current_tier,
    get_governor_report,
    summarize_governor,
)
from runtime.sho_bootstrap import (
    get_sho_report,
    get_sho_status,
    run_sho_cycle as sho_run_one_cycle,
    summarize_sho,
)


# ------------------------------------------------------------
# RENDERING HELPERS
# ------------------------------------------------------------
def render_goals(tree: List[Dict[str, Any]], indent: int = 0) -> List[str]:
    """
    Recursively render the goal tree with indentation.
    """
    lines: List[str] = []
    for node in tree:
        prefix = " " * indent
        title = node.get("goal", "<untitled>")
        gid = node.get("id", "?")
        lines.append(f"{prefix}- {title} (id: {gid})")

        sub = node.get("subgoals", [])
        if sub:
            lines.extend(render_goals(sub, indent + 4))

    return lines


def render_plan_for_goal(goal: Dict[str, Any]) -> List[str]:
    """
    Render the plan for a single goal, including steps, notes, and block reasons.
    """
    lines: List[str] = []
    title = goal.get("goal", "<untitled>")
    lines.append(f"📋 Plan for: {title}")

    steps = goal.get("steps", [])
    if not steps:
        lines.append("  (no steps yet)")
        return lines

    for step in steps:
        num = step.get("number")
        stitle = step.get("title", "")
        status = step.get("status", "pending")
        notes = step.get("notes", [])
        block_reason = step.get("block_reason")

        suffix = ""
        if status == "completed":
            suffix = " [✓ completed]"
        elif status == "blocked":
            suffix = " [⚠ blocked]"

        lines.append(f"{num}. {stitle}{suffix}")

        if block_reason:
            lines.append(f"    - blocked: {block_reason}")
        for n in notes:
            lines.append(f"    - note: {n}")

    return lines


# ------------------------------------------------------------
# EXECUTION ENGINE WITH CONTEXT TRACKING
# ------------------------------------------------------------
class ExecutionEngine:
    """
    Deterministic execution engine for router-based commands.
    Includes context tracking for natural-language resolution.
    """

    def __init__(self, goal_manager) -> None:
        self.goal_manager = goal_manager

    # --------------------------------------------------------
    # Helper: convert step number → step ID
    # --------------------------------------------------------
    def _step_id_from_number(self, num: int, state: Dict[str, Any]) -> Optional[int]:
        steps = self.goal_manager.get_active_steps(state)
        if not steps:
            return None
        if num < 1 or num > len(steps):
            return None
        return steps[num - 1]["id"]

    # --------------------------------------------------------
    # Helper: update context fields
    # --------------------------------------------------------
    def _update_context(
        self,
        state: Dict[str, Any],
        *,
        step_id: Optional[int] = None,
        goal_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        """
        Update last_step_id, last_goal_id, and last_action.
        """
        if step_id is not None:
            state["last_step_id"] = step_id
        if goal_id is not None:
            state["last_goal_id"] = goal_id
        if action is not None:
            state["last_action"] = action

    # --------------------------------------------------------
    # Main entrypoint (router → execution)
    # --------------------------------------------------------
    def execute(self, cmd: Dict[str, Any], state: Dict[str, Any]) -> str:
        intent = cmd.get("intent")
        args = cmd.get("args", {})

        # ----------------------------------------------------
        # RESET STATE
        # ----------------------------------------------------
        if intent == "reset_state":
            state.clear()
            state.update(
                {
                    "goals_tree": [],
                    "active_goal_id": None,
                    "next_goal_id": 1,
                    "next_step_id": 1,
                    "last_step_id": None,
                    "last_goal_id": None,
                    "last_action": None,
                }
            )
            return "✓ State reset"

        # ----------------------------------------------------
        # CREATE GOAL
        # ----------------------------------------------------
        if intent == "create_goal":
            name = args.get("name")
            if not name:
                return "⚠ create_goal: missing name."

            new_goal_id = self.goal_manager.set_goal(name, state)
            self._update_context(state, goal_id=new_goal_id, action="create_goal")
            return f"✓ Goal created\nTitle: {name}"

        # ----------------------------------------------------
        # SWITCH GOAL
        # ----------------------------------------------------
        if intent == "switch_goal":
            gid = args.get("goal_id")
            if gid is None:
                return "⚠ switch_goal: missing goal_id."

            ok = self.goal_manager.switch_goal(gid, state)
            if not ok:
                return f"⚠ Goal {gid} does not exist."

            self._update_context(state, goal_id=gid, action="switch_goal")
            return f"✓ Switched to goal {gid}"

        # ----------------------------------------------------
        # ADD STEP
        # ----------------------------------------------------
        if intent == "add_step":
            desc = args.get("description")
            if not desc:
                return "⚠ add_step: missing description."

            new_step_id = self.goal_manager.add_step(desc, state)
            self._update_context(state, step_id=new_step_id, action="add_step")
            return f"✓ Step added\nTitle: {desc}"

        # ----------------------------------------------------
        # COMPLETE STEP
        # ----------------------------------------------------
        if intent == "complete_step":
            num = args.get("step_number")
            if num is None:
                return "⚠ complete_step: missing step number."

            step_id = self._step_id_from_number(num, state)
            if step_id is None:
                return f"⚠ Step {num} does not exist."

            self.goal_manager.complete_step_by_id(step_id, state)
            self._update_context(state, step_id=step_id, action="complete_step")
            return f"✓ Step completed\nStep: {num}"

        # ----------------------------------------------------
        # DELETE STEP
        # ----------------------------------------------------
        if intent == "delete_step":
            num = args.get("step_number")
            if num is None:
                return "⚠ delete_step: missing step number."

            step_id = self._step_id_from_number(num, state)
            if step_id is None:
                return f"⚠ Step {num} does not exist."

            self.goal_manager.delete_step_by_id(step_id, state)
            self._update_context(state, step_id=step_id, action="delete_step")
            return f"✓ Step deleted\nStep: {num}"

        # ----------------------------------------------------
        # RENAME STEP
        # ----------------------------------------------------
        if intent == "rename_step":
            num = args.get("step_number")
            new_title = args.get("description")
            if num is None or not new_title:
                return "⚠ rename_step: missing step number or new title."

            step_id = self._step_id_from_number(num, state)
            if step_id is None:
                return f"⚠ Step {num} does not exist."

            self.goal_manager.rename_step_by_id(step_id, new_title, state)
            self._update_context(state, step_id=step_id, action="rename_step")
            return f"✓ Step renamed\nStep: {num}\nNew title: {new_title}"

        # ----------------------------------------------------
        # SHOW PLAN
        # ----------------------------------------------------
        if intent == "show_plan":
            goal = self.goal_manager.get_active_goal(state)
            if goal is None:
                return "📋 No active goal."

            self._update_context(state, action="show_plan")
            return "\n".join(render_plan_for_goal(goal))

        # ----------------------------------------------------
        # SHOW GOALS
        # ----------------------------------------------------
        if intent == "show_goals":
            tree = state.get("goals_tree", [])
            if not tree:
                return "📋 No goals yet."

            self._update_context(state, action="show_goals")
            lines = ["📋 Goals:"]
            lines.extend(render_goals(tree))
            return "\n".join(lines)

        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------
        if intent == "help":
            topic = args.get("topic")
            return pretty_help(topic)

        # ----------------------------------------------------
        # DEBUG: STATE / GOALS / STEPS / RAW
        # ----------------------------------------------------
        if intent == "debug_state":
            return pretty_debug_state(state)

        if intent == "debug_goals":
            return pretty_debug_goals(state)

        if intent == "debug_steps":
            return pretty_debug_steps(state)

        if intent == "debug_raw":
            return pretty_debug_raw(state)

        # ----------------------------------------------------
        # DEBUG: DIFF + CONTEXT
        # ----------------------------------------------------
        if intent == "debug_diff":
            return pretty_debug_diff(state)

        if intent == "debug_context":
            return pretty_debug_context(state)

        # ----------------------------------------------------
        # DEBUG: LAST COMMAND (best-effort)
        # ----------------------------------------------------
        if intent == "debug_last":
            entry = state.get("last_command_debug")
            return debug_last(entry) if entry else "⚠ No last command debug entry available."

        # ----------------------------------------------------
        # DEBUG: HISTORY
        # ----------------------------------------------------
        if intent == "debug_history":
            return pretty_debug_history(state)

        # ----------------------------------------------------
        # DEBUG: WATCH ALERTS (use watch history)
        # ----------------------------------------------------
        if intent == "debug_watch_alerts":
            history = state.get("history", [])
            return debug_watch_history(history)

        # ----------------------------------------------------
        # DEBUG: TIMING SUMMARY
        # ----------------------------------------------------
        if intent == "debug_timing":
            timing = state.get("nlu_timing")
            if not timing:
                return "⚠ No NLU timing information available."
            return debug_timing_summary(timing)

        # ----------------------------------------------------
        # DEBUG: CONTEXT TRACE (simple dump)
        # ----------------------------------------------------
        if intent == "debug_context_trace":
            trace = state.get("context_trace", [])
            if not trace:
                return "⚠ No context trace available."
            return "\n".join(str(line) for line in trace)

        # ----------------------------------------------------
        # DEBUG: SEMANTIC + CONTEXTUAL VIEW
        # ----------------------------------------------------
        if intent == "debug_semantic_contextual":
            nlu_cmd = state.get("last_nlu_cmd", {})
            contextual_trace = state.get("contextual_trace", [])
            before_cmd = state.get("_before_last_cmd", {})
            after_cmd = state.get("_after_last_cmd", {})
            if not nlu_cmd:
                return "⚠ No NLU command recorded for semantic/contextual debug."
            return debug_semantic_contextual(
                nlu_cmd,
                contextual_trace,
                before_cmd,
                after_cmd,
            )

        # ----------------------------------------------------
        # DEBUG: FULL NLU PIPELINE
        # ----------------------------------------------------
        if intent == "debug_nlu":
            text = args.get("text")
            if not text:
                return "⚠ debug_nlu: missing text."
            # Prints rich output to console; we just return an acknowledgement.
            debug_nlu_pipeline(text, state)
            return "✓ NLU debug pipeline printed to console."

        # ----------------------------------------------------
        # SYSTEM HEALTH / DIAGNOSTICS (delegates to existing modules)
        # ----------------------------------------------------
        if intent in ("system_health", "health_report"):
            try:
                return render_health_dashboard()
            except Exception:
                return "⚠ Health report unavailable (see logs)."

        if intent in ("run_doctor", "diagnostics", "doctor"):
            try:
                report = run_diagnostics()
                lines = report.get("lines") or []
                return "\n".join(f"[doctor] {line}" for line in lines)
            except Exception:
                return "⚠ Diagnostics unavailable (see logs)."

        # ----------------------------------------------------
        # GOVERNOR (read-only introspection)
        # ----------------------------------------------------
        if intent in ("show_governor", "governor_status"):
            try:
                return summarize_governor()
            except Exception:
                return "⚠ Governor status unavailable (see logs)."

        if intent == "show_tier":
            try:
                return f"Current tier: {get_current_tier()}"
            except Exception:
                return "⚠ Tier unavailable (see logs)."

        if intent == "show_thresholds":
            try:
                return format_governor_thresholds()
            except Exception:
                return "⚠ Thresholds unavailable (see logs)."

        if intent == "governor_report":
            try:
                return json.dumps(get_governor_report(), indent=2, default=str)
            except Exception:
                return "⚠ Governor report unavailable (see logs)."

        # ----------------------------------------------------
        # SHO CYCLE (delegates to orchestrator via sho_bootstrap)
        # ----------------------------------------------------
        if intent in ("run_sho", "sho_cycle"):
            try:
                return json.dumps(sho_run_one_cycle(), indent=2, default=str)
            except Exception:
                return "⚠ SHO cycle unavailable (see logs)."

        if intent == "sho_status":
            try:
                return json.dumps(get_sho_status(), indent=2, default=str)
            except Exception:
                return "⚠ SHO status unavailable (see logs)."

        if intent == "show_sho":
            try:
                return summarize_sho()
            except Exception:
                return "⚠ SHO summary unavailable (see logs)."

        if intent == "sho_report":
            try:
                return json.dumps(get_sho_report(), indent=2, default=str)
            except Exception:
                return "⚠ SHO report unavailable (see logs)."

        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------
        return f"⚠ Unknown intent: {intent}"
