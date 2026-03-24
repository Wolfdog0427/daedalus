from typing import Dict, Any, List


class TelemetryLogger:
    """
    Logs metrics, cycles, failures, proposals, security events.
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def log(self, record: Dict[str, Any]) -> None:
        self.records.append(record)


_default = TelemetryLogger()


def log_event(record: Dict[str, Any]) -> None:
    _default.log(record)
