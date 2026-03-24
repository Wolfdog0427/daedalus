# runtime/tier3_comparison.py
"""
Cross-environment governance comparisons.

Compares two live environments or one live environment against a
historical snapshot baseline.  All functions are read-only.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_COMPARISON_LOG: List[Dict[str, Any]] = []


def get_comparison_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_COMPARISON_LOG[-limit:])


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


def _delta(a: float, b: float) -> Dict[str, Any]:
    diff = round(a - b, 2)
    return {"a": a, "b": b, "delta": diff}


# ------------------------------------------------------------------
# Compare two live environments
# ------------------------------------------------------------------

def compare_environments(env_a_id: str, env_b_id: str) -> Dict[str, Any]:
    """Compare KPIs, SLAs, risk, maturity, and heatmap for two environments."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        ka = compute_environment_kpis(env_a_id)
        kb = compute_environment_kpis(env_b_id)
        if ka.get("error"):
            return ka
        if kb.get("error"):
            return kb
    except Exception:
        return {"error": True, "reason": "failed to compute KPIs"}

    kpis_a = ka.get("kpis", {})
    kpis_b = kb.get("kpis", {})

    kpi_deltas: Dict[str, Dict[str, Any]] = {}
    for key in ("drift_stability_index", "health_findings",
                "applied_packs", "policy_coverage"):
        va = kpis_a.get(key, 0)
        vb = kpis_b.get(key, 0)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            kpi_deltas[key] = _delta(va, vb)

    # SLA comparison
    sla_a = _safe(
        lambda: __import__(
            "runtime.tier3_sla", fromlist=["evaluate_environment_sla"]
        ).evaluate_environment_sla(env_a_id),
        default={},
    )
    sla_b = _safe(
        lambda: __import__(
            "runtime.tier3_sla", fromlist=["evaluate_environment_sla"]
        ).evaluate_environment_sla(env_b_id),
        default={},
    )
    sla_deltas = {
        "a_passed": sla_a.get("passed"),
        "b_passed": sla_b.get("passed"),
        "a_failures": sla_a.get("failures", 0),
        "b_failures": sla_b.get("failures", 0),
    }

    # Risk comparison
    risk_a = _safe(
        lambda: __import__(
            "runtime.tier3_risk", fromlist=["compute_environment_risk"]
        ).compute_environment_risk(env_a_id),
        default={},
    )
    risk_b = _safe(
        lambda: __import__(
            "runtime.tier3_risk", fromlist=["compute_environment_risk"]
        ).compute_environment_risk(env_b_id),
        default={},
    )
    risk_deltas = _delta(
        risk_a.get("risk_score", 0),
        risk_b.get("risk_score", 0),
    )

    # Maturity comparison
    mat_a = _safe(
        lambda: __import__(
            "runtime.tier3_maturity", fromlist=["compute_environment_maturity"]
        ).compute_environment_maturity(env_a_id),
        default={},
    )
    mat_b = _safe(
        lambda: __import__(
            "runtime.tier3_maturity", fromlist=["compute_environment_maturity"]
        ).compute_environment_maturity(env_b_id),
        default={},
    )
    maturity_deltas = _delta(
        mat_a.get("maturity_score", 0),
        mat_b.get("maturity_score", 0),
    )

    # Heatmap comparison
    hm_a = _safe(
        lambda: __import__(
            "runtime.tier3_heatmap", fromlist=["generate_environment_heatmap"]
        ).generate_environment_heatmap(env_a_id),
        default={},
    )
    hm_b = _safe(
        lambda: __import__(
            "runtime.tier3_heatmap", fromlist=["generate_environment_heatmap"]
        ).generate_environment_heatmap(env_b_id),
        default={},
    )
    heatmap_deltas: Dict[str, Dict[str, Any]] = {}
    dims_a = hm_a.get("dimensions", {})
    dims_b = hm_b.get("dimensions", {})
    for key in set(dims_a) | set(dims_b):
        heatmap_deltas[key] = _delta(
            dims_a.get(key, 0), dims_b.get(key, 0),
        )

    result = {
        "scope": "environment_comparison",
        "env_a_id": env_a_id,
        "env_a_name": ka.get("env_name", "?"),
        "env_b_id": env_b_id,
        "env_b_name": kb.get("env_name", "?"),
        "kpi_deltas": kpi_deltas,
        "sla_deltas": sla_deltas,
        "risk_deltas": risk_deltas,
        "maturity_deltas": maturity_deltas,
        "heatmap_deltas": heatmap_deltas,
        "timestamp": time.time(),
    }

    _COMPARISON_LOG.append({
        "type": "environment_comparison",
        "env_a": env_a_id, "env_b": env_b_id,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "comparison_report",
        f"env comparison: '{ka.get('env_name', '?')}' vs '{kb.get('env_name', '?')}'",
        {"env_a": env_a_id, "env_b": env_b_id},
        [env_a_id, env_b_id],
    )

    return result


# ------------------------------------------------------------------
# Compare environment to snapshot baseline
# ------------------------------------------------------------------

def compare_environment_to_baseline(
    env_id: str,
    snapshot_id: str,
) -> Dict[str, Any]:
    """Compare current environment state against a snapshot baseline."""
    try:
        from runtime.tier3_kpis import compute_environment_kpis
        kpi_r = compute_environment_kpis(env_id)
        if kpi_r.get("error"):
            return kpi_r
        kpis_now = kpi_r.get("kpis", {})
        env_name = kpi_r.get("env_name", "?")
    except Exception:
        return {"error": True, "reason": "failed to compute env KPIs"}

    try:
        from runtime.tier3_snapshots import get_snapshot_state
        state = get_snapshot_state(snapshot_id)
        if state is None:
            return {"error": True, "reason": f"snapshot '{snapshot_id}' not found"}
    except Exception:
        return {"error": True, "reason": "failed to read snapshot"}

    # Extract baseline environment from snapshot
    snap_envs = state.get("environments", [])
    snap_env = None
    for e in snap_envs:
        if e.get("env_id") == env_id:
            snap_env = e
            break

    kpi_deltas: Dict[str, Dict[str, Any]] = {}
    baseline_note: Optional[str] = None

    if snap_env is None:
        baseline_note = "environment not present in snapshot — comparing current-only"
        for key in ("drift_stability_index", "health_findings",
                     "applied_packs", "policy_coverage"):
            val = kpis_now.get(key, 0)
            if isinstance(val, (int, float)):
                kpi_deltas[key] = _delta(val, 0)
    else:
        snap_pols = len(snap_env.get("allowed_policy_ids", []))
        snap_pols += len(snap_env.get("default_policy_ids", []))
        snap_packs = len(snap_env.get("applied_pack_ids", []))

        for key, snap_val in [
            ("policy_coverage", snap_pols),
            ("applied_packs", snap_packs),
        ]:
            now_val = kpis_now.get(key, 0)
            if isinstance(now_val, (int, float)):
                kpi_deltas[key] = _delta(now_val, snap_val)

        for key in ("drift_stability_index", "health_findings"):
            now_val = kpis_now.get(key, 0)
            if isinstance(now_val, (int, float)):
                kpi_deltas[key] = _delta(now_val, 0)

    result = {
        "scope": "environment_baseline",
        "env_id": env_id,
        "env_name": env_name,
        "snapshot_id": snapshot_id,
        "kpi_deltas": kpi_deltas,
        "baseline_note": baseline_note,
        "timestamp": time.time(),
    }

    _COMPARISON_LOG.append({
        "type": "environment_baseline",
        "env_id": env_id, "snapshot_id": snapshot_id,
        "timestamp": result["timestamp"],
    })
    _add_insight(
        "comparison_report",
        f"env '{env_name}' vs snapshot {snapshot_id[:8]}..",
        {"env_id": env_id, "snapshot_id": snapshot_id},
        [env_id],
    )

    return result
