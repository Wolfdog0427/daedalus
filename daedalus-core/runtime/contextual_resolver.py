# runtime/contextual_resolver.py

from typing import Dict, Any, List, Optional


class ContextualResolver:
    """
    Phase‑3 contextual disambiguation layer.

    Responsibilities:
        - Fill missing arguments using:
            * active goal
            * active step
            * last referenced step
            * last referenced goal
            * semantic cues
        - Detect ambiguity
        - Never guess silently
        - Produce a trace for debugging
    """

    def __init__(self):
        self._trace: List[str] = []

    def _log(self, msg: str):
        self._trace.append(msg)

    def get_last_trace(self) -> list:
        return list(self._trace)

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def resolve(self, cmd: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        self._trace = []  # reset trace each call
        self._log(f"Incoming command: {cmd}")

        intent   = cmd.get("intent")
        args     = cmd.get("args", {})
        semantic = cmd.get("semantic", {})

        verb_family   = semantic.get("verb_family")
        object_family = semantic.get("object_family")
        modifiers     = semantic.get("modifiers", [])
        ordinal       = semantic.get("ordinal")
        movement      = semantic.get("movement")
        position      = semantic.get("position")

        active_goal = state.get("active_goal_id")
        last_step   = state.get("last_step_referenced")
        last_goal   = state.get("last_goal_referenced")

        # ------------------------------------------------------------
        # 1. Resolve step references (modifiers take priority)
        # ------------------------------------------------------------
        if intent in ("complete_step", "move_step", "delete_step", "rename_step"):
            if "next" in modifiers and last_step is not None:
                args["step_number"] = last_step + 1
                self._log(f"Using next step after last referenced: {last_step + 1}")
            elif "previous" in modifiers and last_step is not None and last_step > 1:
                args["step_number"] = last_step - 1
                self._log(f"Using previous step before last referenced: {last_step - 1}")
            elif args.get("step_number") is None:
                self._log("Resolving vague step reference...")
                if last_step is not None:
                    args["step_number"] = last_step
                    self._log(f"Using last referenced step: {last_step}")
                else:
                    active_step = state.get("active_step_number")
                    if active_step is not None:
                        args["step_number"] = active_step
                        self._log(f"Using active step: {active_step}")
                    else:
                        self._log("No step reference available; leaving unresolved.")

        # ------------------------------------------------------------
        # 2. Resolve vague goal references
        # ------------------------------------------------------------
        if args.get("goal_id") is None and intent in (
            "switch_goal", "delete_goal", "rename_goal"
        ):
            self._log("Resolving vague goal reference...")

            if last_goal is not None:
                args["goal_id"] = last_goal
                self._log(f"Using last referenced goal: {last_goal}")
            else:
                args["goal_id"] = active_goal
                self._log(f"Using active goal: {active_goal}")

        # ------------------------------------------------------------
        # 3. Ordinal / directional goal references
        # ------------------------------------------------------------
        if intent == "switch_goal" and args.get("goal_id") is None:
            goals = state.get("goals_tree", [])

            if ordinal is not None:
                self._log(f"Resolving ordinal goal reference: ordinal={ordinal}")
                if 0 < ordinal <= len(goals):
                    args["goal_id"] = goals[ordinal - 1]["id"]
                    self._log(f"Resolved ordinal goal → {args['goal_id']}")
                else:
                    self._log("Ordinal goal out of range; ignoring.")

            elif active_goal is not None and goals:
                ids = [g["id"] for g in goals]
                try:
                    idx = ids.index(active_goal)
                except ValueError:
                    idx = None

                if idx is not None and "next" in modifiers:
                    target = idx + 1
                    if target < len(goals):
                        args["goal_id"] = goals[target]["id"]
                        self._log(f"Resolved next goal → {args['goal_id']}")
                    else:
                        self._log("Next goal out of range; ignoring.")

                elif idx is not None and "previous" in modifiers:
                    target = idx - 1
                    if target >= 0:
                        args["goal_id"] = goals[target]["id"]
                        self._log(f"Resolved previous goal → {args['goal_id']}")
                    else:
                        self._log("Previous goal out of range; ignoring.")

        # ------------------------------------------------------------
        # 4. Movement-based step operations ("move it up/down")
        # ------------------------------------------------------------
        if intent == "move_step" and movement is not None:
            self._log(f"Movement detected: {movement}")

            if args.get("step_number") is None:
                if last_step is not None:
                    args["step_number"] = last_step
                    self._log(f"Using last referenced step: {last_step}")
                else:
                    self._log("No step reference available for movement.")

            args["movement"] = movement

        # ------------------------------------------------------------
        # 5. Position-based step operations ("move to top/bottom")
        # ------------------------------------------------------------
        if intent == "move_step" and position is not None:
            args["new_position"] = position
            self._log(f"Position override: {position}")

        # ------------------------------------------------------------
        # 6. Modifier-based meaning ("continue", "another")
        # ------------------------------------------------------------
        if intent == "add_step" and "another" in modifiers:
            args["mode"] = "another"
            self._log("Modifier 'another' detected → mode=another")

        if intent == "continue_goal":
            args["goal_id"] = active_goal
            self._log(f"continue_goal → using active goal {active_goal}")

        # ------------------------------------------------------------
        # 7. Update last referenced items
        # ------------------------------------------------------------
        if "step_number" in args and args["step_number"] is not None:
            state["last_step_referenced"] = args["step_number"]
            self._log(f"Updated last_step_referenced → {args['step_number']}")

        if "goal_id" in args and args["goal_id"] is not None:
            state["last_goal_referenced"] = args["goal_id"]
            self._log(f"Updated last_goal_referenced → {args['goal_id']}")

        self._log(f"Final resolved command: {cmd}")
        return cmd
