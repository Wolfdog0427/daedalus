from typing import Any, Dict, List, Optional

from runtime.vpn_control import connect_vpn, disconnect_vpn, vpn_status


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
            state.update({
                "goals_tree": [],
                "active_goal_id": None,
                "next_goal_id": 1,
                "next_step_id": 1,
                "last_step_id": None,
                "last_goal_id": None,
                "last_action": None,
            })
            return "✓ State reset"

        # ----------------------------------------------------
        # CREATE GOAL
        # ----------------------------------------------------
        if intent == "create_goal":
            name = args.get("name")
            if not name:
                return "⚠ create_goal: missing name."

            new_goal_id = self.goal_manager.set_goal(name, state)

            self._update_context(
                state,
                goal_id=new_goal_id,
                action="create_goal",
            )

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

            self._update_context(
                state,
                goal_id=gid,
                action="switch_goal",
            )

            return f"✓ Switched to goal {gid}"

        # ----------------------------------------------------
        # ADD STEP
        # ----------------------------------------------------
        if intent == "add_step":
            desc = args.get("description")
            if not desc:
                return "⚠ add_step: missing description."

            new_step_id = self.goal_manager.add_step(desc, state)

            self._update_context(
                state,
                step_id=new_step_id,
                action="add_step",
            )

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

            self._update_context(
                state,
                step_id=step_id,
                action="complete_step",
            )

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

            self._update_context(
                state,
                step_id=step_id,
                action="delete_step",
            )

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

            self._update_context(
                state,
                step_id=step_id,
                action="rename_step",
            )

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
        # VPN CONTROL (TAILSCALE ANDROID APP)
        # ----------------------------------------------------
        if intent == "vpn_connect":
            self._update_context(state, action="vpn_connect")
            return connect_vpn()

        if intent == "vpn_disconnect":
            self._update_context(state, action="vpn_disconnect")
            return disconnect_vpn()

        if intent == "vpn_status":
            self._update_context(state, action="vpn_status")
            return vpn_status()

        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------
        return f"⚠ Unknown intent: {intent}"
