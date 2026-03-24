# knowledge/system_dashboard.py

"""
System Dashboard
Now displays drift analysis.
"""

import os
import json


def load_recent_improvement():
    cockpit_dir = "data/cockpit"
    if not os.path.exists(cockpit_dir):
        return None

    files = sorted(
        [f for f in os.listdir(cockpit_dir) if f.startswith("decision-")],
        reverse=True,
    )

    if not files:
        return None

    latest = files[0]
    with open(os.path.join(cockpit_dir, latest), "r", encoding="utf-8") as f:
        return json.load(f)


def render_self_healing_panel():
    data = load_recent_improvement()
    if not data:
        return "=== SELF-HEALING ===\nNo improvement cycles recorded.\n"

    best = data.get("best_candidate", {}) or {}
    scores = best.get("scores", {}) or {}
    stability = best.get("stability", {}) or {}
    drift = data.get("drift", {}) or {}

    lines = [
        "=== SELF-HEALING ===",
        f"Cycle:            {data.get('cycle_id')}",
        f"Decision:         {data.get('decision')}",
        f"Candidate Snap:   {data.get('candidate_snapshot_id')}",
        "",
        f"Improvement Score:{scores.get('improvement_score')}",
        f"Risk Score:       {scores.get('risk_score')}",
        f"Trust Score:      {scores.get('trust_score')}",
        f"Stability Score:  {stability.get('stability_score')}",
        f"Stability Risk:   {stability.get('risk')}",
        "",
        "=== DRIFT ===",
        f"Drift Score:      {drift.get('drift_score')}",
        f"Drift Level:      {drift.get('level')}",
        f"Trend:            {drift.get('trend')}",
        "",
        "Metric Deltas:",
        f"  Improvement:    {drift.get('deltas', {}).get('improvement_score')}",
        f"  Trust:          {drift.get('deltas', {}).get('trust_score')}",
        f"  Risk:           {drift.get('deltas', {}).get('risk_score')}",
        f"  Stability:      {drift.get('deltas', {}).get('stability_score')}",
        "",
        f"Cockpit Snapshot: {data.get('cockpit_snapshot_id')}",
        "",
    ]
    return "\n".join(lines)


def render_dashboard():
    return render_self_healing_panel()


def dashboard_summary():
    return render_dashboard()
