class ConversationState:
    """
    Tracks the evolving topic of the conversation.
    Now includes a rolling summary that updates each turn.
    """

    def __init__(self):
        self.current_topic = None
        self.last_topic = None
        self.turns_on_topic = 0
        self.summary = ""

    def update(self, user_input: str):
        text = user_input.strip().lower()

        # Detect topic change
        if self.current_topic is None:
            self.current_topic = text
            self.turns_on_topic = 1
            self._update_summary(text)
            return

        if text == self.current_topic:
            # Same topic, continue
            self.turns_on_topic += 1
            self._update_summary(text)
        else:
            # Topic changed
            self.last_topic = self.current_topic
            self.current_topic = text
            self.turns_on_topic = 1
            self._update_summary(text)

    def _update_summary(self, new_input: str):
        """
        Lightweight symbolic summarization.
        Keeps the summary short and focused.
        """
        if not self.summary:
            self.summary = new_input
        else:
            # Keep only the last ~3 key points
            parts = self.summary.split(" | ")
            parts.append(new_input)
            self.summary = " | ".join(parts[-3:])

    def get_state(self):
        return {
            "current_topic": self.current_topic,
            "last_topic": self.last_topic,
            "turns_on_topic": self.turns_on_topic,
            "summary": self.summary,
        }
