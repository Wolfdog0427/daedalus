class IdentityEngine:
    """
    Defines the assistant's stable communication style and identity.
    """

    def __init__(self):
        self.style = {
            "tone": "calm, precise, focused, reliable, strategic",
            "verbosity": "minimal but complete",
        }

    def apply_identity(self, text: str) -> str:
        """
        For now, this just returns the text unchanged.
        Later, it can enforce tone and style.
        """
        return text
