# analytics/delta_accuracy.py

from __future__ import annotations

import math
import os
import json
from typing import Any, Dict, List


DELTA_LOG_PATH = os.path.join("data", "learning", "delta_validation.jsonl")


def _iter_records() -> List[Dict[str, Any]]:
    if not os.path.exists(DELTA_LOG_PATH):
        return []
    records: List[Dict[str, Any]] = []
    with open(DELTA_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(rec, dict):
                records.append(rec)
    return records


_RISK_RANK: Dict[str, int] = {
    "none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4,
}


def compute_delta_accuracy() -> Dict[str, Any]:
    """
    Returns aggregate accuracy metrics for drift/stability/risk deltas.
    """
    records = _iter_records()
    if not records:
        return {
            "count": 0,
            "drift_mae": None,
            "stability_mae": None,
            "risk_match_rate": None,
        }

    drift_errors: List[float] = []
    stab_errors: List[float] = []
    risk_matches = 0
    risk_total = 0

    for r in records:
        pd = r.get("predicted_drift_delta")
        ad = r.get("actual_drift_delta")
        ps = r.get("predicted_stability_delta")
        as_ = r.get("actual_stability_delta")

        if pd is not None and ad is not None:
            try:
                err = abs(float(pd) - float(ad))
                if not math.isnan(err):
                    drift_errors.append(err)
            except (TypeError, ValueError):
                pass
        if ps is not None and as_ is not None:
            try:
                err = abs(float(ps) - float(as_))
                if not math.isnan(err):
                    stab_errors.append(err)
            except (TypeError, ValueError):
                pass

        pb = r.get("predicted_risk_delta")
        rb = r.get("risk_before")
        ra = r.get("risk_after")
        if pb is not None and rb is not None and ra is not None:
            try:
                pb_f = float(pb)
            except (TypeError, ValueError):
                continue
            if math.isnan(pb_f):
                continue
            ra_rank = _RISK_RANK.get(ra, 2)
            rb_rank = _RISK_RANK.get(rb, 2)
            risk_total += 1
            if pb_f < 0 and ra_rank <= rb_rank:
                risk_matches += 1
            elif pb_f > 0 and ra_rank >= rb_rank:
                risk_matches += 1
            elif abs(pb_f) < 1e-9 and ra_rank == rb_rank:
                risk_matches += 1

    def _mae(values: List[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    risk_match_rate = (risk_matches / risk_total) if risk_total else None

    return {
        "count": len(records),
        "drift_mae": _mae(drift_errors),
        "stability_mae": _mae(stab_errors),
        "risk_match_rate": risk_match_rate,
    }
