# governor/governor_tuning.py

from __future__ import annotations
import json
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

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

    if not isinstance(th["readiness_min_for_escalation"], (int, float)):
        return "readiness_min_for_escalation must be numeric"

    if not isinstance(th["readiness_min_for_autonomous"], (int, float)):
        return "readiness_min_for_autonomous must be numeric"

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

    # Apply to governor
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
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "saved_by": "user",
            "version": "1.0",
        },
        "signature": signature,
    }

    # Ensure directory exists
    directory = os.path.dirname(CONFIG_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

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

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

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

        target.drift_threshold_escalate = thresholds["drift_threshold_escalate"]
        target.drift_threshold_deescalate = thresholds["drift_threshold_deescalate"]
        target.stability_threshold_escalate = thresholds["stability_threshold_escalate"]
        target.stability_threshold_deescalate = thresholds["stability_threshold_deescalate"]
        target.readiness_min_for_escalation = thresholds["readiness_min_for_escalation"]
        target.readiness_min_for_autonomous = thresholds["readiness_min_for_autonomous"]

    except Exception:
        # Silent failure by design
        return


# ------------------------------------------------------------
# Reset to defaults
# ------------------------------------------------------------
def reset_thresholds() -> Dict[str, Any]:
    defaults = {
        "drift_threshold_escalate": "low",
        "drift_threshold_deescalate": "medium",
        "stability_threshold_escalate": "low",
        "stability_threshold_deescalate": "high",
        "readiness_min_for_escalation": 0.75,
        "readiness_min_for_autonomous": 0.85,
    }

    set_thresholds(defaults)

    return {"ok": True, "reset_to": defaults}
