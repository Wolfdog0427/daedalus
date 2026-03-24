from typing import Dict, Any
from analysis import telemetry_logger

def hem_log_event(event: Dict[str, Any]) -> None:
    telemetry_logger.log_event({"source": "HEM", **event})
