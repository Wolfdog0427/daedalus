# runtime/tier3_heatmap.py
"""
Governance risk heatmap generators.

Produces structured, non-graphical heatmap data that overlays risk,
drift, readiness, and anomaly density across environments.
All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

_HEATMAP_LOG: List[Dict[str, Any]] = []
_MAX_LOG = 200


def get_heatmap_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_HEATMAP_LOG[-limit:])


def _add_insight(itype: str, summary: str, details: Dict[str, Any],
                 related_ids: List[str] | None = None) -> None:
    try:
        from runtime.tier3_anomaly import _add_insight as _ai
        _ai(itype, summary, details, related_ids)
    except Exception:
        pass


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _heat_level(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "hot"
    if score >= 25:
        return "warm"
    return "cool"


# ------------------------------------------------------------------
# System heatmap
# ------------------------------------------------------------------

def generate_system_heatmap() -> Dict[str, Any]:
    """Generate a heatmap covering all environments."""
    envs = _safe(
        lambda: __import__(
            "runtime.tier3_environments", fromlist=["list_environments"]
        ).list_environments(),
        default=[],
    )

    cells: List[Dict[str, Any]] = []
    for env in envs:
        eid = env.get("env_id", "")
        cell = _build_env_cell(eid, env.get("name", "?"))
        cells.append(cell)

    n_hot = sum(1 for c in cells if c["heat"] in ("hot", "critical"))

    result = {
        "scope": "system",
        "cells": cells,
        "n_environments": len(cells),
        "n_hot": n_hot,
        "timestamp": time.time(),
    }

    _HEATMAP_LOG.append({
        "type": "system", "n_envs": len(cells),
        "n_hot": n_hot, "timestamp": result["timestamp"],
    })
    if len(_HEATMAP_LOG) > _MAX_LOG:
        _HEATMAP_LOG[:] = _HEATMAP_LOG[-_MAX_LOG:]
    _add_insight(
        "heatmap",
        f"system heatmap: {len(cells)} env(s), {n_hot} hot/critical",
        {"n_envs": len(cells), "n_hot": n_hot},
    )

    return result


# ------------------------------------------------------------------
# Environment heatmap
# ------------------------------------------------------------------

def generate_environment_heatmap(env_id: str) -> Dict[str, Any]:
    """Generate a heatmap for a single environment's dimensions."""
    try:
        from runtime.tier3_environments import get_environment
        env = get_environment(env_id)
        if env is None:
            return {"error": True, "reason": f"environment '{env_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read environment"}

    cell = _build_env_cell(env_id, env.get("name", "?"))

    result = {
        "scope": "environment",
        "env_id": env_id,
        "env_name": env.get("name", "?"),
        "dimensions": cell["dimensions"],
        "heat": cell["heat"],
        "risk_score": cell["risk_score"],
        "timestamp": time.time(),
    }

    _HEATMAP_LOG.append({
        "type": "environment", "env_id": env_id,
        "heat": cell["heat"], "risk_score": cell["risk_score"],
        "timestamp": result["timestamp"],
    })
    if len(_HEATMAP_LOG) > _MAX_LOG:
        _HEATMAP_LOG[:] = _HEATMAP_LOG[-_MAX_LOG:]
    _add_insight(
        "heatmap",
        f"env '{env.get('name', '?')}' heatmap: {cell['heat']} "
        f"(risk {cell['risk_score']})",
        {"env_id": env_id, "heat": cell["heat"],
         "risk_score": cell["risk_score"]},
        [env_id],
    )

    return result


# ------------------------------------------------------------------
# Internal: build a heatmap cell for one environment
# ------------------------------------------------------------------

def _build_env_cell(env_id: str, env_name: str) -> Dict[str, Any]:
    """Build a single heatmap cell with per-dimension scores."""
    dimensions: Dict[str, float] = {}

    # Risk
    risk_score = 0.0
    try:
        from runtime.tier3_risk import compute_environment_risk
        rr = compute_environment_risk(env_id)
        if not rr.get("error"):
            risk_score = rr.get("risk_score", 0)
    except Exception:
        pass
    dimensions["risk"] = risk_score

    # Drift (invert stability so higher = worse)
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_r = compute_environment_kpis(env_id)
        if not kpi_r.get("error"):
            kpis = kpi_r.get("kpis", {})
            drift_stability = kpis.get("drift_stability_index", 100.0)
            dimensions["drift"] = max(0.0, min(100.0, round(100 - drift_stability, 1)))
        else:
            dimensions["drift"] = 0.0
    except Exception:
        dimensions["drift"] = 0.0

    # Readiness (invert so higher = worse)
    readiness = 0.0
    try:
        from runtime.tier3_env_health import get_readiness_log
        entries = get_readiness_log(20)
        env_entries = [e for e in entries
                       if e.get("source_env_id") == env_id
                       or e.get("target_env_id") == env_id]
        if env_entries:
            avg = sum(e.get("readiness_score", 0) for e in env_entries) / len(env_entries)
            readiness = max(0.0, min(100.0, round(100 - avg, 1)))
    except Exception:
        pass
    dimensions["readiness_gap"] = readiness

    # Anomaly density
    anomaly_density = 0.0
    try:
        from runtime.tier3_anomaly import get_anomaly_registry
        all_a = get_anomaly_registry(200)
        env_a = [a for a in all_a if env_id in str(a.get("object_id", ""))]
        anomaly_density = min(len(env_a) * 10, 100)
    except Exception:
        pass
    dimensions["anomaly_density"] = anomaly_density

    composite = max(0.0, min(100.0, round(
        risk_score * 0.4
        + dimensions["drift"] * 0.25
        + readiness * 0.20
        + anomaly_density * 0.15,
        1,
    )))
    heat = _heat_level(composite)

    return {
        "env_id": env_id,
        "env_name": env_name,
        "dimensions": dimensions,
        "risk_score": risk_score,
        "composite": composite,
        "heat": heat,
    }
