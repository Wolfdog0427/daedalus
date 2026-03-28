class SessionReplay:
    """
    Provides replay and summary capabilities on top of HistoryTimeline.

    Supports:
      - replay_all()
      - replay_last(n)
      - replay_for_goal(goal_id)
      - replay_for_step(step_id)
      - summary()
      - summary_last(n)
    """

    def __init__(self, timeline):
        self.timeline = timeline

    # ------------------------------------------------------------
    # BASIC REPLAY
    # ------------------------------------------------------------
    def replay_all(self):
        return self.timeline.get_all()

    def replay_last(self, n):
        events = self.timeline.get_all()
        return events[-n:] if n > 0 else []

    # ------------------------------------------------------------
    # FILTERED REPLAY
    # ------------------------------------------------------------
    def replay_for_goal(self, goal_id):
        events = self.timeline.get_all()
        return [
            e for e in events
            if "goal_id" in e["state"] and e["state"]["goal_id"] == goal_id
        ]

    def replay_for_step(self, step_id):
        events = self.timeline.get_all()
        return [
            e for e in events
            if "step_id" in e["state"] and e["state"]["step_id"] == step_id
        ]

    # ------------------------------------------------------------
    # SUMMARIES
    # ------------------------------------------------------------
    def summary(self):
        events = self.timeline.get_all()
        if not events:
            return "No actions recorded."

        actions = [e["action"] for e in events]
        return f"{len(events)} actions: " + ", ".join(actions)

    def summary_last(self, n):
        events = self.replay_last(n)
        if not events:
            return "No actions recorded."

        actions = [e["action"] for e in events]
        return f"{len(events)} actions: " + ", ".join(actions)
