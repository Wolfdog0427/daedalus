from typing import List, Dict, Any


class EvolutionMemory:
    """
    Long-term log of changes, failures, proposals, approvals, rejections.
    """

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def record(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # TODO: implement filtering
        return self.events
