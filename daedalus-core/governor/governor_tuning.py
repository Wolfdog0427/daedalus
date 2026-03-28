# governor/governor_tuning.py

from __future__ import annotations
import json
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from governor.governor_trace import record_governor_event


CONFIG_PATH = "config/governor_thresholds.json"


# ------------------------------------------------------------
# Utility: compute SHA-256 signature of thresholds
# ------------------------------------------------------------
def _compute_signature(thresholds: Dict[str, Any]) -> str:
    encoded = json.dumps(thresholds, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"sha256:{digest}"


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
_VALID_LEVELS = {"low", "medium", "high"}


def _validate_thresholds(th: Dict[str, Any]) -> Optional[str]:
    """
    Returns None if valid, otherwise an error string.
    """

    required = [
        "drift_threshold_escalate",
        "drift_threshold_deescalate",
        "stability_threshold_escalate",
        "stability_threshold_deescalate",
        "readiness_min_for_escalation",
        "readiness_min_for_autonomous",
    ]

    for key in required:
        if key not in th:
            return f"Missing threshold: {key}"

    for key in (
        "drift_threshold_escalate", "drift_threshold_deescalate",
        "stability_threshold_escalate", "stability_threshold_deescalate",
    ):
        if th[key] not in _VALID_LEVELS:
            return f"{key} must be one of {_VALID_LEVELS}, got {th[key]!r}"

    if not isinstance(th["readiness_min_for_escalation"], (int, float)):
        return "readiness_min_for_escalation must be numeric"
    if not (0.0 <= th["readiness_min_for_escalation"] <= 1.0):
        return "readiness_min_for_escalation must be between 0.0 and 1.0"

    if not isinstance(th["readiness_min_for_autonomous"], (int, float)):
        return "readiness_min_for_autonomous must be numeric"
    if not (0.0 <= th["readiness_min_for_autonomous"] <= 1.0):
        return "readiness_min_for_autonomous must be between 0.0 and 1.0"

    return None


# ------------------------------------------------------------
# Apply thresholds at runtime
# ------------------------------------------------------------
def set_thresholds(new_values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update governor thresholds at runtime (not persisted).
    """
    from governor.singleton import governor as _gov

    err = _validate_thresholds(new_values)
    if err:
        return {"ok": False, "error": err}

    with _gov._lock:
        _gov.drift_threshold_escalate = new_values["drift_threshold_escalate"]
        _gov.drift_threshold_deescalate = new_values["drift_threshold_deescalate"]
        _gov.stability_threshold_escalate = new_values["stability_threshold_escalate"]
        _gov.stability_threshold_deescalate = new_values["stability_threshold_deescalate"]
        _gov.readiness_min_for_escalation = new_values["readiness_min_for_escalation"]
        _gov.readiness_min_for_autonomous = new_values["readiness_min_for_autonomous"]

    return {"ok": True, "applied": new_values}


# ------------------------------------------------------------
# Save thresholds to disk (with signature)
# ------------------------------------------------------------
def save_thresholds() -> Dict[str, Any]:
    """
    Persist current governor thresholds to disk.
    """
    from governor.singleton import governor as _gov

    with _gov._lock:
        thresholds = {
            "drift_threshold_escalate": _gov.drift_threshold_escalate,
            "drift_threshold_deescalate": _gov.drift_threshold_deescalate,
            "stability_threshold_escalate": _gov.stability_threshold_escalate,
            "stability_threshold_deescalate": _gov.stability_threshold_deescalate,
            "readiness_min_for_escalation": _gov.readiness_min_for_escalation,
            "readiness_min_for_autonomous": _gov.readiness_min_for_autonomous,
        }

    signature = _compute_signature(thresholds)

    payload = {
        "thresholds": thresholds,
        "metadata": {
            "saved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "saved_by": "user",
            "version": "1.0",
        },
        "signature": signature,
    }

    directory = os.path.dirname(CONFIG_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)

    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(CONFIG_PATH) or ".", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            tmp_fd = -1
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, CONFIG_PATH)
    except BaseException:
        if tmp_fd >= 0:
            os.close(tmp_fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Log persisted change
    record_governor_event("thresholds_persisted", {
        "thresholds": thresholds,
        "signature": signature,
    })

    return {"ok": True, "saved": payload}


# ------------------------------------------------------------
# Load thresholds from disk
# ------------------------------------------------------------
def load_thresholds() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return {"ok": False, "error": "No persisted thresholds found"}

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        return {"ok": False, "error": f"Failed to parse config: {exc}"}

    if not isinstance(payload, dict):
        return {"ok": False, "error": "Config file is not a JSON object"}

    thresholds = payload.get("thresholds", {})
    signature = payload.get("signature")

    # Validate signature
    expected = _compute_signature(thresholds)
    if signature != expected:
        return {
            "ok": False,
            "error": "Signature mismatch — file may be corrupted or tampered",
            "expected": expected,
            "found": signature,
        }

    # Validate thresholds
    err = _validate_thresholds(thresholds)
    if err:
        return {"ok": False, "error": err}

    # Apply to governor
    set_thresholds(thresholds)

    return {"ok": True, "loaded": payload}


# ------------------------------------------------------------
# Silent loader for startup (no prints, no errors)
# ------------------------------------------------------------
def load_thresholds_silent(gov_instance=None) -> None:
    """
    Used by governor/singleton.py at startup.
    Loads persisted thresholds if present.
    Never prints, never raises, never logs.
    """

    if not os.path.exists(CONFIG_PATH):
        return

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        thresholds = payload.get("thresholds", {})
        signature = payload.get("signature")

        if _compute_signature(thresholds) != signature:
            return

        if _validate_thresholds(thresholds) is not None:
            return

        # Apply to provided governor instance or global singleton (lazy import breaks singleton↔tuning cycle)
        if gov_instance is not None:
            target = gov_instance
        else:
            from governor.singleton import governor as _gov

            target = _gov

        with target._lock:
            target.drift_threshold_escalate = thresholds["drift_threshold_escalate"]
            target.drift_threshold_deescalate = thresholds["drift_threshold_deescalate"]
            target.stability_threshold_escalate = thresholds["stability_threshold_escalate"]
            target.stability_threshold_deescalate = thresholds["stability_threshold_deescalate"]
            target.readiness_min_for_escalation = thresholds["readiness_min_for_escalation"]
            target.readiness_min_for_autonomous = thresholds["readiness_min_for_autonomous"]

    except (json.JSONDecodeError, OSError, ValueError):
        return
    except Exception:
        # Silent failure by design
        return


# ------------------------------------------------------------
# Reset to defaults
# ------------------------------------------------------------
def reset_thresholds() -> Dict[str, Any]:
    defaults = {
        "drift_threshold_escalate": "medium",
        "drift_threshold_deescalate": "medium",
        "stability_threshold_escalate": "low",
        "stability_threshold_deescalate": "high",
        "readiness_min_for_escalation": 0.75,
        "readiness_min_for_autonomous": 0.85,
    }

    set_thresholds(defaults)

    return {"ok": True, "reset_to": defaults}
