class Router:
    """
    Simple deterministic intent → command router.

    Input:
        {"intent": str, "args": dict}

    Output:
        {"command": str, "args": dict}
    """

    def __init__(self):
        # Map intents to execution engine commands
        self.intent_map = {
            "create_goal": "create_goal",
            "add_step": "add_step",
            "complete_step": "complete_step",
            "delete_step": "delete_step",
            "rename_step": "rename_step",
            "switch_goal": "switch_goal",
            "show_goals": "show_goals",
            "show_plan": "show_plan",
        }

    def route(self, parsed: dict) -> dict:
        """
        Convert NLU output into an execution command.
        """
        intent = parsed.get("intent")
        args = parsed.get("args", {})

        # Unknown intent fallback
        if intent not in self.intent_map:
            return {"command": "unknown_intent", "args": args}

        return {
            "command": self.intent_map[intent],
            "args": args
        }
