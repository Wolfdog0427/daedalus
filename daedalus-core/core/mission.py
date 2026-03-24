class MissionEngine:
    """
    Ensures responses align with the assistant's mission.
    """

    def __init__(self):
        self.mission = (
            "Increase Spencer's capability, clarity, and efficiency with "
            "structured reasoning and actionable guidance, while maintaining "
            "safety, alignment, and user control."
        )

    def is_aligned(self, intent: str) -> bool:
        """
        Very simple placeholder: treat clearly harmful topics as misaligned.
        """
        lowered = intent.lower()
        if any(k in lowered for k in ["harm", "suicide", "kill", "abuse"]):
            return False
        return True

    def enforce_mission(self, text: str) -> str:
        """
        Placeholder for mission-aware rewriting or refusal.
        For now, just return the text unchanged.
        """
        return text
