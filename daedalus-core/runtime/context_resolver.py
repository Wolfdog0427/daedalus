# runtime/context_resolver.py

from typing import Dict, Any, List, Optional
import difflib
import re


class ContextResolver:
    """
    Phase‑2 resolver:
        - Fills missing arguments using simple, deterministic rules
        - Adds conservative fuzzy resolution for goals and steps
        - Adds pronoun-based and topic-based fuzzy resolution
        - Never guesses silently (only unique, high‑confidence matches)
        - Provides a trace for debugging
        - Ensures arguments are well‑formed before Phase‑3 (ContextualResolver)
    """

    def __init__(self):
        self._trace: List[str] = []

    def _log(self, msg: str):
        self._trace.append(msg)

    def get_last_trace(self) -> str:
        return "\n".join(self._trace)

    # --------------------------------------------------------
    # Helpers: ordinals, pronouns, and fuzzy matching
    # --------------------------------------------------------
    @staticmethod
    def _ordinal_to_index(word: str) -> Optional[int]:
        word = word.lower()
        mapping = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
        }
        return mapping.get(word)

    @staticmethod
    def _get_text(cmd: Dict[str, Any]) -> str:
        return cmd.get("raw") or cmd.get("repaired") or ""

    @staticmethod
    def _contains_pronoun_for_goal(text: str) -> bool:
        t = text.lower()
        return any(p in t for p in ("that goal", "this goal", "the goal"))

    @staticmethod
    def _contains_pronoun_for_step(text: str) -> bool:
        t = text.lower()
        return any(p in t for p in ("that step", "this step", "the step"))

    # --------------------------------------------------------
    # Fuzzy goal resolution
    # --------------------------------------------------------
    def _fuzzy_goal_from_text(self, text: str, state: Dict[str, Any]) -> Optional[int]:
        goals = state.get("goals_tree", [])
        if not goals:
            return None

        text_l = text.lower()

        # Pronoun-based: "that goal", "this goal" → last_goal_referenced
        if self._contains_pronoun_for_goal(text_l):
            last_gid = state.get("last_goal_referenced")
            if last_gid is not None:
                return last_gid

        # Ordinal goals: "first goal", "last goal"
        if "goal" in text_l:
            if "first goal" in text_l and len(goals) >= 1:
                return goals[0]["id"]
            if "last goal" in text_l and len(goals) >= 1:
                return goals[-1]["id"]

        # Topic-based / partial phrase fuzzy match against goal names
        names = [g.get("name", "") for g in goals]
        if not names:
            return None

        matches = difflib.get_close_matches(text_l, [n.lower() for n in names], n=1, cutoff=0.75)
        if not matches:
            return None

        best = matches[0]
        for g in goals:
            if g.get("name", "").lower() == best:
                return g["id"]

        return None

    # --------------------------------------------------------
    # Fuzzy step resolution
    # --------------------------------------------------------
    def _fuzzy_step_from_text(self, text: str, state: Dict[str, Any]) -> Optional[int]:
        goals = state.get("goals_tree", [])
        active_goal_id = state.get("active_goal_id")
        if not goals or active_goal_id is None:
            return None

        goal = next((g for g in goals if g.get("id") == active_goal_id), None)
        if not goal:
            return None

        steps = goal.get("steps", [])
        if not steps:
            return None

        text_l = text.lower()

        # Pronoun-based: "that step", "this step" → last_step_referenced
        if self._contains_pronoun_for_step(text_l):
            last_step = state.get("last_step_referenced")
            if last_step is not None:
                return last_step

        # Ordinal steps: "first step", "second step", "last step"
        m = re.search(r"(first|second|third|fourth|fifth)\s+step", text_l)
        if m:
            idx = self._ordinal_to_index(m.group(1))
            if idx is not None and 1 <= idx <= len(steps):
                return steps[idx - 1]["number"]

        if "last step" in text_l:
            return steps[-1]["number"]

        # Topic-based / partial phrase fuzzy match against step descriptions
        descs = [s.get("description", "") for s in steps]
        if not descs:
            return None

        matches = difflib.get_close_matches(text_l, [d.lower() for d in descs], n=1, cutoff=0.75)
        if not matches:
            return None

        best = matches[0]
        for s in steps:
            if s.get("description", "").lower() == best:
                return s["number"]

        return None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def resolve(self, cmd: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        self._trace = []  # reset trace
        self._log(f"[ContextResolver] Incoming: {cmd}")

        intent = cmd.get("intent")
        args   = cmd.get("args", {})

        active_goal = state.get("active_goal_id")
        active_step = state.get("active_step_number")
        text        = self._get_text(cmd)

        # ------------------------------------------------------------
        # 1. Ensure args is a dict
        # ------------------------------------------------------------
        if not isinstance(args, dict):
            self._log("Args was not a dict → replacing with empty dict.")
            args = {}
            cmd["args"] = args

        # ------------------------------------------------------------
        # 2. Resolve missing goal_id for common intents (with fuzzy)
        # ------------------------------------------------------------
        if intent in (
            "add_step",
            "complete_step",
            "delete_step",
            "rename_step",
            "move_step",
            "show_plan",
            "set_active_goal",
        ):
            if args.get("goal_id") is None:
                gid = self._fuzzy_goal_from_text(text, state)
                if gid is not None:
                    args["goal_id"] = gid
                    self._log(f"goal_id missing → fuzzy resolved goal_id={gid}")
                else:
                    args["goal_id"] = active_goal
                    self._log(f"goal_id missing → using active_goal={active_goal}")

        # ------------------------------------------------------------
        # 3. Resolve missing step_id / step_number (with fuzzy)
        # ------------------------------------------------------------
        if intent in ("complete_step", "delete_step", "rename_step", "move_step"):
            if args.get("step_id") is None and args.get("step_number") is None:
                snum = self._fuzzy_step_from_text(text, state)
                if snum is not None:
                    args["step_number"] = snum
                    self._log(f"step_number missing → fuzzy resolved step_number={snum}")
                elif active_step is not None:
                    args["step_number"] = active_step
                    self._log(f"step_number missing → using active_step={active_step}")
                else:
                    self._log("No active_step available; leaving step unresolved.")

        # ------------------------------------------------------------
        # 4. Normalize step references
        # ------------------------------------------------------------
        if "step_id" in args and args["step_id"] is not None:
            if "step_number" not in args:
                args["step_number"] = args["step_id"]
                self._log(f"Normalized step_id → step_number={args['step_number']}")

        # ------------------------------------------------------------
        # 5. Normalize goal references
        # ------------------------------------------------------------
        if "goal" in args and isinstance(args["goal"], int):
            args["goal_id"] = args["goal"]
            del args["goal"]
            self._log(f"Normalized goal → goal_id={args['goal_id']}")

        # ------------------------------------------------------------
        # 6. Ensure numeric types where expected
        # ------------------------------------------------------------
        for key in ("goal_id", "step_number"):
            if key in args and args[key] is not None:
                try:
                    args[key] = int(args[key])
                    self._log(f"Coerced {key} to int: {args[key]}")
                except Exception:
                    self._log(f"Failed to coerce {key} to int → leaving as-is.")

        # ------------------------------------------------------------
        # 7. Update state references
        # ------------------------------------------------------------
        if args.get("goal_id") is not None:
            state["last_goal_referenced"] = args["goal_id"]
            self._log(f"Updated last_goal_referenced → {args['goal_id']}")

        if args.get("step_number") is not None:
            state["last_step_referenced"] = args["step_number"]
            self._log(f"Updated last_step_referenced → {args['step_number']}")

        self._log(f"[ContextResolver] Final: {cmd}")
        return cmd
