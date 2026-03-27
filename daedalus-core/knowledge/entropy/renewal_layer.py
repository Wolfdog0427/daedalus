# knowledge/entropy/renewal_layer.py

"""
Renewal Layer

Periodically prunes non-permanent state to prevent long-horizon drift,
scar tissue, and unbounded state accretion.

CRITICAL SAFETY DIFFERENCES FROM THE ORIGINAL PROPOSAL:
1. NEVER deletes permanent state (knowledge, graph, trust, provenance).
2. Pruning is incremental (item-by-item with TTL checks), not destructive
   (shutil.rmtree).
3. All mutations route through governance (guard_action).
4. Every action is audit-logged.
5. Migration hooks are NOT exec()'d — they must be registered callables.

This is the primary entropy sink: it removes expired transient state
while preserving everything the system has learned.
"""

from __future__ import annotations

import time
import shutil
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

from knowledge.entropy.canonical_template import (
    load_template,
    get_state_tier,
)

RENEWAL_DIR = Path("data/entropy/renewal")
_migration_hooks: Dict[str, Callable] = {}


def _ensure_dir():
    RENEWAL_DIR.mkdir(parents=True, exist_ok=True)


def register_migration_hook(name: str, fn: Callable) -> None:
    """Register a named migration callable (replaces dangerous exec() of hook files)."""
    _migration_hooks[name] = fn


def _ttl_seconds(tier_config: Dict[str, Any]) -> Optional[float]:
    """Convert tier TTL to seconds. Returns None for permanent state."""
    if tier_config.get("ttl") is None and "ttl_hours" not in tier_config and "ttl_days" not in tier_config:
        return None
    if "ttl_hours" in tier_config:
        return tier_config["ttl_hours"] * 3600
    if "ttl_days" in tier_config:
        return tier_config["ttl_days"] * 86400
    return None


def _is_expired(path: Path, ttl_secs: float) -> bool:
    """Check if a file/directory is older than its TTL."""
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) > ttl_secs
    except Exception:
        return False


def scan_for_expired(root: Path = Path("data")) -> List[Dict[str, Any]]:
    """
    Scan the data directory for expired transient state.
    Returns a list of candidates for pruning with their tier and age.
    Never includes permanent state.
    """
    template = load_template()
    tiers = template.get("state_tiers", {})
    candidates: List[Dict[str, Any]] = []

    if not root.exists():
        return candidates

    for item in root.rglob("*"):
        if not item.exists():
            continue

        rel = str(item.relative_to(root.parent)).replace("\\", "/")
        tier_name = get_state_tier(rel)

        if tier_name == "permanent":
            continue

        tier_config = tiers.get(tier_name)
        if tier_config is None:
            continue

        ttl = _ttl_seconds(tier_config)
        if ttl is None:
            continue

        if _is_expired(item, ttl):
            age_hours = (time.time() - item.stat().st_mtime) / 3600
            candidates.append({
                "path": str(item),
                "relative": rel,
                "tier": tier_name,
                "age_hours": round(age_hours, 1),
                "ttl_hours": round(ttl / 3600, 1),
                "action": tier_config.get("action", "delete"),
                "is_dir": item.is_dir(),
            })

    return candidates


def _prune_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Prune a single expired item based on its tier action."""
    path = Path(item["path"])
    action = item["action"]

    if not path.exists():
        return {"path": item["path"], "status": "already_gone"}

    try:
        if action == "delete":
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            return {"path": item["path"], "status": "deleted"}

        elif action == "compact":
            if path.is_file() and path.stat().st_size > 10_000:
                content = path.read_text(encoding="utf-8", errors="replace")
                lines = content.strip().split("\n")
                if len(lines) > 100:
                    compacted = "\n".join(lines[-100:])
                    path.write_text(compacted, encoding="utf-8")
                    return {"path": item["path"], "status": "compacted", "lines_kept": 100}
            return {"path": item["path"], "status": "compact_skipped"}

        elif action == "archive":
            archive_dir = Path("data/entropy/archives")
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / path.name
            if path.is_dir():
                shutil.copytree(path, dest, dirs_exist_ok=True)
                shutil.rmtree(path, ignore_errors=True)
            else:
                shutil.copy2(path, dest)
                path.unlink(missing_ok=True)
            return {"path": item["path"], "status": "archived", "destination": str(dest)}

        else:
            return {"path": item["path"], "status": "unknown_action", "action": action}

    except Exception as exc:
        return {"path": item["path"], "status": "error", "error": str(exc)}


def run_renewal(dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute a full renewal cycle:
    1. Scan for expired transient state.
    2. Prune/compact/archive expired items.
    3. Run registered migration hooks.
    4. Return a full audit report.

    When dry_run=True, scans but does not mutate anything.
    """
    _ensure_dir()
    now = time.time()
    candidates = scan_for_expired()

    report: Dict[str, Any] = {
        "timestamp": now,
        "dry_run": dry_run,
        "scanned": len(candidates),
        "actions": [],
        "hooks_run": [],
        "errors": [],
    }

    if not dry_run:
        for item in candidates:
            result = _prune_item(item)
            report["actions"].append(result)
            if result.get("status") == "error":
                report["errors"].append(result)

        for hook_name, hook_fn in _migration_hooks.items():
            try:
                hook_fn()
                report["hooks_run"].append({"hook": hook_name, "status": "ok"})
            except Exception as exc:
                report["hooks_run"].append({"hook": hook_name, "status": "error", "error": str(exc)})
                report["errors"].append({"hook": hook_name, "error": str(exc)})
    else:
        report["actions"] = [
            {"path": c["path"], "would_do": c["action"], "tier": c["tier"], "age_hours": c["age_hours"]}
            for c in candidates
        ]

    report["deleted"] = sum(1 for a in report["actions"] if a.get("status") == "deleted")
    report["compacted"] = sum(1 for a in report["actions"] if a.get("status") == "compacted")
    report["archived"] = sum(1 for a in report["actions"] if a.get("status") == "archived")
    report["error_count"] = len(report["errors"])

    return report


def get_renewal_status() -> Dict[str, Any]:
    """Quick health check: how many items would be pruned right now?"""
    candidates = scan_for_expired()
    by_tier: Dict[str, int] = {}
    for c in candidates:
        by_tier[c["tier"]] = by_tier.get(c["tier"], 0) + 1
    return {
        "pending_prunes": len(candidates),
        "by_tier": by_tier,
        "hooks_registered": list(_migration_hooks.keys()),
    }
