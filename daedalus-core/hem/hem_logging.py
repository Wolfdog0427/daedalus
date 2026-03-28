from typing import Dict, Any

try:
    from analysis import telemetry_logger
except ImportError:
    telemetry_logger = None  # type: ignore[assignment]


def hem_log_event(event: Dict[str, Any]) -> None:
    if telemetry_logger is not None:
        telemetry_logger.log_event({**event, "source": "HEM"})
