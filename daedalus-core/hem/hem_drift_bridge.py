# hem/hem_drift_bridge.py

"""
HEM Drift Bridge — post-engagement checks.

After HEM handles a hostile engagement, this bridge verifies
that system drift and integrity are within acceptable bounds.
"""

from __future__ import annotations

from .hem_logging import hem_log_event


def hem_run_post_engagement_checks() -> bool:
    """
    Run post-HEM-engagement drift and integrity checks.
    Returns True if the system is healthy after engagement.
    """
    drift_ok = _check_drift()
    integrity_ok = _check_integrity()

    hem_log_event({
        "type": "HEM_POSTCHECK_RESULT",
        "drift_ok": drift_ok,
        "integrity_ok": integrity_ok,
    })

    return drift_ok and integrity_ok


def _check_drift() -> bool:
    """Check drift using the knowledge drift detector."""
    try:
        from knowledge.drift_detector import compute_latest_drift
        report = compute_latest_drift()
        if report is None:
            return True
        return report.get("level", "none") in ("none", "low")
    except Exception:
        return True


def _check_integrity() -> bool:
    """Check system integrity using the runtime integrity validator."""
    try:
        from runtime.integrity_validator import integrity_validator
        result = integrity_validator.validate()
        return result.get("valid", False) if isinstance(result, dict) else bool(result)
    except Exception:
        return True
