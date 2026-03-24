# runtime/autonomy_cycle_log.py
"""
Append-only, in-memory log of Tier-1 autonomy cycle events.

Each entry records a timestamp, result, and envelope snapshot at
cycle time.  Non-persistent — exists only for the lifetime of the
process.
"""

from __future__ import annotations

from typing import Any, Dict, List

_TIER1_CYCLE_LOG: List[Dict[str, Any]] = []


def log_tier1_cycle(timestamp: float, result: str, envelope: str) -> None:
    """Append a cycle record.  Never raises."""
    _TIER1_CYCLE_LOG.append({
        "timestamp": timestamp,
        "result": result,
        "envelope": envelope,
    })


def get_tier1_cycle_log(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent *limit* entries (oldest-first)."""
    return list(_TIER1_CYCLE_LOG[-limit:])


def clear_tier1_cycle_log() -> None:
    """Reset the log (for testing only)."""
    _TIER1_CYCLE_LOG.clear()


# ------------------------------------------------------------------
# Phase 29: drift analysis (read-only)
# ------------------------------------------------------------------

def _severity(rate: float) -> str:
    if rate < 0.25:
        return "normal"
    if rate < 0.50:
        return "elevated"
    return "critical"


def analyze_skip_rate(log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fraction of cycles with result != 'success'."""
    total = len(log)
    if total == 0:
        return {"skip_count": 0, "total_count": 0, "skip_rate": 0.0, "severity": "normal"}
    skip_count = sum(1 for e in log if e.get("result") != "success")
    rate = skip_count / total
    return {
        "skip_count": skip_count,
        "total_count": total,
        "skip_rate": round(rate, 4),
        "severity": _severity(rate),
    }


def analyze_envelope_stability(log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fraction of cycles where the envelope was not 'pass'."""
    total = len(log)
    if total == 0:
        return {"fail_count": 0, "total_count": 0, "fail_rate": 0.0, "severity": "normal"}
    fail_count = sum(1 for e in log if e.get("envelope") != "pass")
    rate = fail_count / total
    return {
        "fail_count": fail_count,
        "total_count": total,
        "fail_rate": round(rate, 4),
        "severity": _severity(rate),
    }


def analyze_cadence_drift(
    log: List[Dict[str, Any]], expected_seconds: int = 0
) -> Dict[str, Any]:
    """Compare average inter-cycle gap to the expected cadence."""
    if expected_seconds <= 0:
        try:
            from runtime.system_settings import get_setting
            expected_seconds = get_setting("tier1_cadence_seconds")
        except Exception:
            expected_seconds = 300

    if len(log) < 2:
        return {
            "avg_delta": 0.0,
            "expected": expected_seconds,
            "drift": 0.0,
            "severity": "normal",
        }

    deltas = [
        log[i]["timestamp"] - log[i - 1]["timestamp"]
        for i in range(1, len(log))
        if "timestamp" in log[i] and "timestamp" in log[i - 1]
    ]
    if not deltas:
        return {
            "avg_delta": 0.0,
            "expected": expected_seconds,
            "drift": 0.0,
            "severity": "normal",
        }

    avg = sum(deltas) / len(deltas)
    drift = avg - expected_seconds
    drift_ratio = abs(drift) / expected_seconds if expected_seconds else 0.0
    return {
        "avg_delta": round(avg, 2),
        "expected": expected_seconds,
        "drift": round(drift, 2),
        "severity": _severity(drift_ratio),
    }


def get_autonomy_drift_report(limit: int = 20) -> Dict[str, Any]:
    """Compose all drift signals from the most recent cycle log entries."""
    log = get_tier1_cycle_log(limit)
    return {
        "skip_rate": analyze_skip_rate(log),
        "envelope_stability": analyze_envelope_stability(log),
        "cadence_drift": analyze_cadence_drift(log),
    }
