from typing import Any, Dict, List, Optional

# ------------------------------------------------------------
# HEM imports (Option C deep integration)
# ------------------------------------------------------------
from hem.hem_state_machine import (
    hem_maybe_enter,
    hem_transition_to_postcheck,
    hem_run_post_engagement_checks,
)


class OfflineReasoner:
    """
    Stage 5 Offline Reasoner

    Responsibilities:
    - Interpret natural-language commands into structured actions
    - Preserve full fuzzy reference phrases (never truncate to "the")
    - Extract reasons, notes, and titles cleanly
    - Route fuzzy references to GoalManager for resolution
    - Provide consistent, predictable behavior for ExecutionEngine

    HEM Integration:
    - Enter HEM when offline reasoning is invoked (hostile text boundary)
    - Run post-engagement checks after interpretation
    """

    # ------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------
    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------
    # Utility: Build fuzzy action payload
    # ------------------------------------------------------------
    def _build_fuzzy_action(
        self,
        action_type: str,
        ref_phrase: str,
        state: Dict[str, Any],
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build a fuzzy action dictionary.

        - ref_phrase: the full natural-language phrase (e.g., "the step about roof")
        - resolved_step_number: resolved by GoalManager (may be None)
        """
        from runtime.goal_manager import GoalManager
        gm = GoalManager()

        resolved = gm.resolve_step_phrase(ref_phrase, state)

        payload = {
            "ref_phrase": ref_phrase,
            "resolved_step_number": resolved,
        }

        if extra_payload:
            payload.update(extra_payload)

        return {
            "type": action_type,
            "payload": payload,
        }

    # ------------------------------------------------------------
    # Utility: Extract block reason cleanly
    # ------------------------------------------------------------
    def _extract_block_reason(self, original: str) -> str:
        """
        Extract the reason for blocking a step.

        Example:
            "block the step about roof until delivery arrives"
            → reason = "until delivery arrives"

        We look for the first occurrence of " until " or " because ".
        """
        lower = original.lower()

        # Preferred separators
        for sep in [" until ", " because ", " due to "]:
            if sep in lower:
                idx = lower.index(sep)
                return original[idx + len(sep):].strip()

        # Fallback: no explicit reason separator
        return "blocked"

    # ------------------------------------------------------------
    # Main entry point: interpret natural-language command
    # ------------------------------------------------------------
    def interpret(self, text: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert a natural-language command into a structured action.

        This is the heart of the OfflineReasoner.

        HEM:
        - Enter HEM for offline natural-language interpretation
        - Run post-engagement checks after interpretation
        """

        # ------------------------------------------------------------
        # HEM: Enter hostile engagement mode for offline reasoning
        # ------------------------------------------------------------
        hem_maybe_enter(
            trigger_reason="offline_reasoner_interpret",
            metadata={"input_preview": text[:80]},
        )

        t = text.lower().strip()

        # --------------------------------------------------------
        # SET GOAL
        # --------------------------------------------------------
        if t.startswith("set goal "):
            title = text[len("set goal "):].strip()
            result = [{
                "type": "set_goal",
                "payload": {"title": title},
            }]

            # HEM post-check
            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # ADD STEP
        # --------------------------------------------------------
        if t.startswith("add step "):
            title = text[len("add step "):].strip()
            result = [{
                "type": "add_step",
                "payload": {"title": title},
            }]

            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # COMPLETE STEP (fuzzy)
        # --------------------------------------------------------
        if t.startswith("complete "):
            ref = text[len("complete "):].strip()
            result = [ self._build_fuzzy_action("complete_step", ref, state) ]

            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # BLOCK STEP (fuzzy + reason)
        # --------------------------------------------------------
        if t.startswith("block "):
            # Extract fuzzy reference
            after_block = text[len("block "):].strip()

            # Extract reason
            reason = self._extract_block_reason(text)

            # Remove reason from fuzzy phrase
            lower = after_block.lower()
            for sep in [" until ", " because ", " due to "]:
                if sep in lower:
                    idx = lower.index(sep)
                    fuzzy = after_block[:idx].strip()
                    break
            else:
                fuzzy = after_block

            result = [ self._build_fuzzy_action(
                "block_step",
                fuzzy,
                state,
                {"reason": reason},
            ) ]

            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # UNBLOCK STEP (fuzzy)
        # --------------------------------------------------------
        if t.startswith("unblock "):
            ref = text[len("unblock "):].strip()
            result = [ self._build_fuzzy_action("unblock_step", ref, state) ]

            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # RENAME STEP (fuzzy)
        # --------------------------------------------------------
        if t.startswith("rename "):
            # Pattern: rename <fuzzy> to <new title>
            if " to " in t:
                before, after = text.split(" to ", 1)
                fuzzy = before[len("rename "):].strip()
                new_title = after.strip()
                result = [ self._build_fuzzy_action(
                    "rename_step",
                    fuzzy,
                    state,
                    {"new_title": new_title},
                ) ]

                hem_transition_to_postcheck()
                hem_run_post_engagement_checks()
                return result

        # --------------------------------------------------------
        # ADD NOTE (fuzzy)
        # --------------------------------------------------------
        if t.startswith("note "):
            # Pattern: note <fuzzy> <note text>
            parts = text.split(" ", 2)
            if len(parts) >= 3:
                fuzzy = parts[1].strip()
                note = parts[2].strip()
                result = [ self._build_fuzzy_action(
                    "add_note",
                    fuzzy,
                    state,
                    {"note": note},
                ) ]

                hem_transition_to_postcheck()
                hem_run_post_engagement_checks()
                return result

        # --------------------------------------------------------
        # MOVE STEP
        # --------------------------------------------------------
        if t.startswith("move step "):
            # Pattern: move step X to Y
            try:
                rest = t[len("move step "):].strip()
                if " to " in rest:
                    a, b = rest.split(" to ", 1)
                    from_num = int(a.strip())
                    to_num = int(b.strip())
                    result = [{
                        "type": "move_step",
                        "payload": {
                            "from_num": from_num,
                            "to_num": to_num,
                        },
                    }]

                    hem_transition_to_postcheck()
                    hem_run_post_engagement_checks()
                    return result
            except:
                pass

        # --------------------------------------------------------
        # SWITCH GOAL
        # --------------------------------------------------------
        if t.startswith("switch to "):
            title = text[len("switch to "):].strip()
            result = [{
                "type": "switch_goal",
                "payload": {"title": title},
            }]

            hem_transition_to_postcheck()
            hem_run_post_engagement_checks()
            return result

        # --------------------------------------------------------
        # FALLBACK: unknown command
        # --------------------------------------------------------
        result = [{
            "type": "unknown",
            "payload": {"text": text},
        }]

        hem_transition_to_postcheck()
        hem_run_post_engagement_checks()
        return result
