from typing import Dict, Any, List

_MAX_RECORDS = 500


class TelemetryLogger:
    """
    Logs metrics, cycles, failures, proposals, security events.
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def log(self, record: Dict[str, Any]) -> None:
        self.records.append(record)
        if len(self.records) > _MAX_RECORDS:
            self.records = self.records[-_MAX_RECORDS:]


_default = TelemetryLogger()


def log_event(record: Dict[str, Any]) -> None:
    _default.log(record)
