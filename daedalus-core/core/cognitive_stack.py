# core/cognitive_stack.py

from typing import Any, Dict, List, Optional

class CognitiveStack:
    """
    Clean, stable parser layer.
    Handles ONLY the commands we explicitly support:
    - set goal TITLE
    - add step TITLE
    - show goals
    - show plan
    - complete step N
    - block step N because REASON
    - unblock step N
    - rename step N to TITLE
    - move step N to M
    - add note to step N: NOTE

    NO FALLBACK.
    NO OFFLINEREASONER.
    NO HALLUCINATIONS.
    """

    def __init__(self, goal_manager):
        self.goal_manager = goal_manager

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _extract_number(self, text: str) -> Optional[int]:
        words = text.lower().split()
        for w in words:
            if w.isdigit():
                return int(w)
            if w in ("one", "1"): return 1
            if w in ("two", "2"): return 2
            if w in ("three", "3"): return 3
            if w in ("four", "4"): return 4
            if w in ("five", "5"): return 5
        return None

    # ------------------------------------------------------------
    # Main parser
    # ------------------------------------------------------------
    def process(
        self,
        user_input: str,
        history: List[Dict[str, Any]],
        state: Dict[str, Any],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        text = user_input.lower().strip()

        # Ignore empty lines completely
        if not text:
            return []

        # --------------------------------------------------------
        # SET GOAL
        # --------------------------------------------------------
        if text.startswith("set goal"):
            title = user_input[len("set goal"):].strip()
            if title:
                return [{"type": "set_goal", "payload": {"title": title}}]

        # --------------------------------------------------------
        # ADD STEP
        # --------------------------------------------------------
        if text.startswith("add step"):
            title = user_input[len("add step"):].strip()
            if title:
                return [{"type": "add_step", "payload": {"title": title}}]

        # --------------------------------------------------------
        # SHOW GOALS
        # --------------------------------------------------------
        if text in ("show goals", "goals"):
            return [{"type": "show_goals"}]

        # --------------------------------------------------------
        # SHOW PLAN
        # --------------------------------------------------------
        if text in ("show plan", "plan"):
            return [{"type": "show_plan"}]

        # --------------------------------------------------------
        # COMPLETE STEP
        # --------------------------------------------------------
        if text.startswith("complete step") or text.endswith("completed"):
            num = self._extract_number(text)
            if num:
                return [{"type": "complete_step", "payload": {"step_number": num}}]

        # --------------------------------------------------------
        # BLOCK STEP
        # --------------------------------------------------------
        if text.startswith("block step"):
            num = self._extract_number(text)
            if num:
                reason = None
                if "because" in text:
                    reason = text.split("because", 1)[1].strip()
                return [{
                    "type": "block_step",
                    "payload": {"step_number": num, "reason": reason or "blocked"}
                }]

        # --------------------------------------------------------
        # UNBLOCK STEP
        # --------------------------------------------------------
        if text.startswith("unblock step"):
            num = self._extract_number(text)
            if num:
                return [{"type": "unblock_step", "payload": {"step_number": num}}]

        # --------------------------------------------------------
        # RENAME STEP
        # --------------------------------------------------------
        if text.startswith("rename step"):
            num = self._extract_number(text)
            if "to" in text:
                new_title = text.split("to", 1)[1].strip()
                return [{
                    "type": "rename_step",
                    "payload": {"step_number": num, "new_title": new_title}
                }]

        # --------------------------------------------------------
        # MOVE STEP
        # --------------------------------------------------------
        if text.startswith("move step"):
            num = self._extract_number(text)
            if "to" in text:
                after = text.split("to", 1)[1]
                dest = self._extract_number(after)
                return [{
                    "type": "move_step",
                    "payload": {"from_step": num, "to_step": dest}
                }]

        # --------------------------------------------------------
        # ADD NOTE
        # --------------------------------------------------------
        if text.startswith("add note to step"):
            num = self._extract_number(text)
            if ":" in user_input:
                note = user_input.split(":", 1)[1].strip()
                return [{
                    "type": "add_note_to_step",
                    "payload": {"step_number": num, "note": note}
                }]

        # --------------------------------------------------------
        # NO FALLBACK — prevents hallucinations
        # --------------------------------------------------------
        return []
