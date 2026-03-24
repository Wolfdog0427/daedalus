from knowledge import drift_detector
from runtime import integrity_validator
from .hem_logging import hem_log_event

def hem_run_post_engagement_checks() -> bool:
    drift_ok = drift_detector.check_drift()
    integrity_ok = integrity_validator.verify_integrity()

    hem_log_event({
        "type": "HEM_POSTCHECK_RESULT",
        "drift_ok": drift_ok,
        "integrity_ok": integrity_ok,
    })

    return drift_ok and integrity_ok
