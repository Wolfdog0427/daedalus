# runtime/semantic_firewall.py

from typing import Dict, Any
import difflib


class SemanticFirewall:
    """
    Validates and sanitizes commands after NLU but before execution.

    Now includes conservative fuzzy intent matching:
      - Only matches against SAFE_INTENTS
      - Only accepts high-confidence matches
      - Only accepts unique best matches
      - Logs repairs for debug cockpit
    """

    SAFE_INTENTS = {
        # Core goal/step operations
        "create_goal",
        "add_goal",
        "add_step",
        "complete_step",
        "delete_step",
        "rename_step",
        "switch_goal",
        "show_plan",
        "show_goals",
        "list_goals",
        "archive_goal",
        "unarchive_goal",
        "set_goals_sort",
        "set_goals_filter",

        # Help
        "help",

        # Watchpoints
        "add_watchpoint",
        "remove_watchpoint",
        "list_watchpoints",

        # Checkpoints
        "save_checkpoint",
        "restore_checkpoint",
        "list_checkpoints",

        # Undo/redo
        "undo",
        "redo",

        # Progress navigation (REPL / NLU)
        "next_step",

        # Plan mode
        "set_plan_mode",
        "show_plan_mode",

        # System health / diagnostics (introspection)
        "system_health",
        "health_report",
        "run_doctor",
        "diagnostics",
        "doctor",

        # Governor (introspection only)
        "show_governor",
        "governor_status",
        "show_tier",
        "show_thresholds",
        "governor_report",

        # SHO cycle (introspection / cycle trigger)
        "run_sho",
        "sho_cycle",
        "sho_status",
        "show_sho",
        "sho_report",

        # Debug cockpit
        "debug_state",
        "debug_diff",
        "debug_context",
        "debug_timing",
        "debug_history",
        "debug_context_trace",
        "debug_watch_alerts",
        "debug_goals",
        "debug_steps",
        "debug_raw",
        "debug_last",
        "debug_semantic_contextual",
        "debug_nlu",
    }

    # --------------------------------------------------------
    # Fuzzy intent matching
    # --------------------------------------------------------
    @classmethod
    def _fuzzy_match_intent(cls, intent: str) -> str:
        """
        Attempt to fuzzy-match an unknown intent to a known safe intent.

        Rules:
          - Must be >= 0.85 similarity
          - Must be a unique best match
          - Otherwise return None
        """
        candidates = list(cls.SAFE_INTENTS)
        matches = difflib.get_close_matches(intent, candidates, n=3, cutoff=0.85)

        if not matches:
            return None

        # If multiple matches tie, reject for safety
        if len(matches) > 1:
            return None

        return matches[0]

    # --------------------------------------------------------
    # Main firewall entrypoint
    # --------------------------------------------------------
    @classmethod
    def firewall(cls, cmd: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the command structure and intent.
        Return the sanitized command or raise ValueError.
        """

        if not isinstance(cmd, dict):
            raise ValueError("SemanticFirewall: command must be a dict")

        intent = cmd.get("intent")
        if not intent:
            raise ValueError("SemanticFirewall: missing intent")

        # Exact match allowed
        if intent not in cls.SAFE_INTENTS:
            # Try fuzzy match
            repaired = cls._fuzzy_match_intent(intent)
            if repaired:
                # Log the repair for debug cockpit
                cmd["firewall_repair"] = {
                    "original_intent": intent,
                    "repaired_intent": repaired,
                    "reason": "fuzzy_match",
                }
                intent = repaired
                cmd["intent"] = repaired
            else:
                raise ValueError(f"SemanticFirewall: unknown or unsafe intent '{intent}'")

        # Ensure args is a dict
        args = cmd.get("args")
        if args is None:
            cmd["args"] = {}
        elif not isinstance(args, dict):
            raise ValueError("SemanticFirewall: args must be a dict")

        return cmd
