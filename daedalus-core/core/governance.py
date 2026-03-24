class GovernanceFlags:
    """
    Neutral governance flags.
    No censorship, no blocking, no safety overrides.
    Only ambiguity detection for reasoning quality.
    """
    def __init__(self):
        self.ambiguous = False
        self.risky = False  # Always False in neutral mode
        self.notes = ""


class GovernanceEngine:
    """
    Neutral governance engine.
    Does not restrict content or override user intent.
    Only detects ambiguity to improve reasoning.
    """

    def assess(self, user_input: str) -> GovernanceFlags:
        flags = GovernanceFlags()
        text = user_input.strip().lower()

        # Ambiguity detection only
        vague_terms = ["do it", "do that", "that one", "this", "it", "go", "continue"]
        if text in vague_terms or len(text) == 0:
            flags.ambiguous = True
            flags.notes = "Ambiguous input."

        return flags

    def enforce(self, response: str, flags: GovernanceFlags) -> str:
        """
        Neutral enforcement: returns the response unchanged.
        """
        return response
