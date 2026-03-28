# governance/drift_detector.py
"""
Governance-level drift detection for Daedalus.

Detects drift across behavioral, posture, expression, continuity,
coherence, and stability dimensions.  All detection is read-only
and never mutates system state.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Dict, List

_DRIFT_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 50
_drift_lock = threading.Lock()


def compute_drift_report() -> Dict[str, Any]:
    """Compute a comprehensive drift report across all identity dimensions."""
    dimensions: Dict[str, Dict[str, Any]] = {}

    dimensions["posture"] = _detect_posture_drift()
    dimensions["expression"] = _detect_expression_drift()
    dimensions["continuity"] = _detect_continuity_drift()
    dimensions["coherence"] = _detect_coherence_drift()
    dimensions["stability"] = _detect_stability_drift()

    unavailable_count = sum(
        1 for d in dimensions.values() if d.get("detail") == "unavailable"
    )
    total = sum(d.get("drift_score", 0) for d in dimensions.values())
    total += unavailable_count * 10
    if math.isnan(total) or math.isinf(total):
        total = len(dimensions) * 20.0
    avg = round(total / max(len(dimensions), 1), 2)
    if math.isnan(avg) or math.isinf(avg):
        avg = 100.0

    try:
        from governance.modes import get_drift_sensitivity
        sensitivity = get_drift_sensitivity()
    except Exception:
        sensitivity = 0.7

    report = {
        "dimensions": dimensions,
        "total_drift_score": round(total, 2),
        "average_drift_score": avg,
        "sensitivity": sensitivity,
        "alert": avg * sensitivity > 30,
        "timestamp": time.time(),
    }

    with _drift_lock:
        _DRIFT_LOG.append({
            "total": report["total_drift_score"],
            "average": report["average_drift_score"],
            "alert": report["alert"],
            "timestamp": report["timestamp"],
        })
        if len(_DRIFT_LOG) > _MAX_LOG:
            _DRIFT_LOG[:] = _DRIFT_LOG[-_MAX_LOG:]

    return report


# ------------------------------------------------------------------
# Dimension detectors
# ------------------------------------------------------------------

def _detect_posture_drift() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state
        ss = get_stability_state()
        osc = ss.get("oscillation_index", 0.0)
        return {"drift_score": round(osc * 50, 2), "detail": f"oscillation={osc}"}
    except Exception:
        return {"drift_score": 0, "detail": "unavailable"}


def _detect_expression_drift() -> Dict[str, Any]:
    try:
        from runtime.resonance_engine import resonance_summary
        rs = resonance_summary()
        intensity = rs.get("resonance_intensity", 0)
        blend = rs.get("blend_factor", 1.0)
        drift = round((1.0 - blend) * 20 + (1.0 - intensity) * 10, 2)
        return {"drift_score": drift, "detail": f"blend={blend}, intensity={intensity}"}
    except Exception:
        return {"drift_score": 0, "detail": "unavailable"}


def _detect_continuity_drift() -> Dict[str, Any]:
    try:
        from runtime.session_continuity import get_continuity_state
        cs = get_continuity_state()
        strength = cs.get("continuity_strength", "low")
        score = {"low": 20, "medium": 5, "high": 0}.get(strength, 10)
        return {"drift_score": score, "detail": f"strength={strength}"}
    except Exception:
        return {"drift_score": 0, "detail": "unavailable"}


def _detect_coherence_drift() -> Dict[str, Any]:
    try:
        from runtime.identity_coherence import get_coherence_summary
        cs = get_coherence_summary()
        coh_score = cs.get("coherence_score", 100)
        drift = round(max(0, 100 - coh_score) * 0.5, 2)
        return {"drift_score": drift, "detail": f"coherence={coh_score}"}
    except Exception:
        return {"drift_score": 0, "detail": "unavailable"}


def _detect_stability_drift() -> Dict[str, Any]:
    try:
        from runtime.stability_regulator import get_stability_state
        ss = get_stability_state()
        jitter = ss.get("jitter_index", 0.0)
        stab = ss.get("stability_score", 100.0)
        drift = round(jitter * 30 + max(0, 100 - stab) * 0.2, 2)
        return {"drift_score": drift, "detail": f"jitter={jitter}, stability={stab}"}
    except Exception:
        return {"drift_score": 0, "detail": "unavailable"}
