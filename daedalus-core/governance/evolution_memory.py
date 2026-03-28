from typing import List, Dict, Any


class EvolutionMemory:
    """
    Long-term log of changes, failures, proposals, approvals, rejections.
    """

    _MAX_EVENTS = 1000

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def record(self, event: Dict[str, Any]) -> None:
        self.events.append(dict(event))
        if len(self.events) > self._MAX_EVENTS:
            self.events[:] = self.events[-self._MAX_EVENTS:]

    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [dict(e) for e in self.events]
