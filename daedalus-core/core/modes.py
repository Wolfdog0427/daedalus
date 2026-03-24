class ModeController:
    """
    Neutral mode controller.
    No high_safety mode.
    Only lean and deep based on ambiguity + complexity.
    """

    def select_mode(self, ambiguous: bool, risky: bool, complexity: str) -> str:
        # Ambiguity → deep reasoning
        if ambiguous:
            return "deep"

        # High complexity → deep reasoning
        if complexity == "high":
            return "deep"

        # Default
        return "lean"
