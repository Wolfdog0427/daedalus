# knowledge/entropy/entropy_budget.py

"""
Entropy Budget Layer

Every class of state has a lifetime, owner, and deletion/compaction rule.
This module enforces TTLs, tracks state growth, and provides an entropy
"budget" — a quantifiable measure of how much transient state the system
is accumulating vs. shedding per cycle.

Key design properties:
- 5 tiers: permanent, hot, warm, cold, staging
- State not in the registry is automatically "staging" (review, not purge)
- Provides budget_report() for meta-cognition to monitor entropy pressure
- Integrates with renewal_layer for enforcement
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from knowledge.entropy.canonical_template import load_template, get_state_tier

BUDGET_DIR = Path("data/entropy/budget")
BUDGET_HISTORY = BUDGET_DIR / "history.jsonl"


def _ensure_dir():
    BUDGET_DIR.mkdir(parents=True, exist_ok=True)


def _measure_path_size(path: Path) -> int:
    """Total bytes under a path (file or directory)."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except Exception:
                pass
    return total


def _count_items(path: Path) -> int:
    """Count files under a path."""
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return sum(1 for f in path.rglob("*") if f.is_file())


def compute_entropy_budget(root: Path = Path("data")) -> Dict[str, Any]:
    """
    Compute the current entropy budget: how much state exists per tier,
    how much is expired, and the overall entropy pressure score.
    """
    template = load_template()
    tiers = template.get("state_tiers", {})
    tier_stats: Dict[str, Dict[str, Any]] = {}

    for tier_name in tiers:
        tier_stats[tier_name] = {
            "bytes": 0,
            "items": 0,
            "expired_items": 0,
            "expired_bytes": 0,
        }
    tier_stats["unclassified"] = {
        "bytes": 0,
        "items": 0,
        "expired_items": 0,
        "expired_bytes": 0,
    }

    if not root.exists():
        return _build_report(tier_stats, 0, 0)

    now = time.time()
    total_bytes = 0
    total_items = 0

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        try:
            st = item.stat()
            size = st.st_size
            mtime = st.st_mtime
        except Exception:
            continue

        rel = str(item.relative_to(root.parent)).replace("\\", "/")
        tier_name = get_state_tier(rel)

        total_bytes += size
        total_items += 1

        bucket = tier_stats.get(tier_name, tier_stats["unclassified"])
        bucket["bytes"] += size
        bucket["items"] += 1

        tier_config = tiers.get(tier_name, {})
        ttl_secs = _tier_ttl_seconds(tier_config)
        if ttl_secs is not None and (now - mtime) > ttl_secs:
            bucket["expired_items"] += 1
            bucket["expired_bytes"] += size

    return _build_report(tier_stats, total_bytes, total_items)


def _tier_ttl_seconds(tier_config: Dict[str, Any]) -> Optional[float]:
    if "ttl_hours" in tier_config:
        return tier_config["ttl_hours"] * 3600
    if "ttl_days" in tier_config:
        return tier_config["ttl_days"] * 86400
    return None


def _build_report(
    tier_stats: Dict[str, Dict[str, Any]],
    total_bytes: int,
    total_items: int,
) -> Dict[str, Any]:
    expired_bytes = sum(t["expired_bytes"] for t in tier_stats.values())
    expired_items = sum(t["expired_items"] for t in tier_stats.values())

    if total_bytes > 0:
        entropy_pressure = expired_bytes / total_bytes
    else:
        entropy_pressure = 0.0

    return {
        "timestamp": time.time(),
        "total_bytes": total_bytes,
        "total_items": total_items,
        "expired_bytes": expired_bytes,
        "expired_items": expired_items,
        "entropy_pressure": round(entropy_pressure, 4),
        "tier_breakdown": tier_stats,
        "health": _entropy_health(entropy_pressure),
    }


def _entropy_health(pressure: float) -> str:
    if pressure < 0.05:
        return "excellent"
    if pressure < 0.15:
        return "good"
    if pressure < 0.30:
        return "moderate"
    if pressure < 0.50:
        return "elevated"
    return "critical"


def record_budget_snapshot(budget: Dict[str, Any]) -> None:
    """Append a budget snapshot to history for trend analysis."""
    _ensure_dir()
    import json
    with open(BUDGET_HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": budget["timestamp"],
            "total_bytes": budget["total_bytes"],
            "expired_bytes": budget["expired_bytes"],
            "entropy_pressure": budget["entropy_pressure"],
            "health": budget["health"],
        }) + "\n")


def get_budget_trend(last_n: int = 20) -> List[Dict[str, Any]]:
    """Return recent budget snapshots for trend analysis."""
    import json
    if not BUDGET_HISTORY.exists():
        return []
    try:
        lines = BUDGET_HISTORY.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(line) for line in lines if line.strip()]
        return entries[-last_n:]
    except Exception:
        return []


def classify_new_state(path: str) -> Dict[str, Any]:
    """
    Classify a new piece of state and return its tier assignment.
    If not found in the registry, it's 'staging' and flagged for review.
    """
    tier = get_state_tier(path)
    return {
        "path": path,
        "tier": tier,
        "needs_review": tier == "staging",
    }
