# knowledge/entropy/canonical_template.py

"""
Canonical Organism Template

Defines the immutable, operator-blessed identity of Daedalus.
All nodes periodically verify themselves against this template.
Deviations are logged for the Drift Court, not silently deleted.

Key safety property: the template distinguishes PERMANENT state
(knowledge, graph, trust, provenance — the system's value) from
TRANSIENT state (caches, logs, buffers — operational overhead).
This prevents the renewal layer from destroying learned knowledge.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from knowledge._atomic_io import atomic_write_json

CANONICAL_DIR = Path("data/entropy/canonical")
TEMPLATE_FILE = CANONICAL_DIR / "template.json"


def _default_template() -> Dict[str, Any]:
    return {
        "version": "1.0.0",
        "last_updated": time.time(),
        "updated_by": "system",

        "invariants": [
            "identity.core",
            "governance.tier_system",
            "governance.operator_sovereignty",
            "governance.constitutional_guard",
            "posture.modes",
            "defense.circuit_breaker",
            "defense.regression_detector",
            "defense.coordinator",
            "telemetry.schema",
            "knowledge.verification_pipeline",
            "knowledge.trust_scoring",
            "knowledge.consistency_checker",
        ],

        "permanent_state": [
            "data/knowledge/knowledge_store.jsonl",
            "data/knowledge/index.json",
            "data/knowledge_graph/graph.json",
            "data/knowledge_graph/entities.json",
            "data/knowledge_goals/goals.json",
            "data/governor_state.json",
            "data/governor_proposals.json",
            "data/learning/",
            "data/subsystems/",
            "data/rollback/",
            "data/entropy/",
            "runtime/state.db",
            "config/",
            ".integrity/",
            ".versions/",
        ],

        "state_tiers": {
            "permanent": {
                "ttl": None,
                "action": "preserve",
                "description": "Knowledge, graph, trust, provenance, governor — the system's value",
            },
            "hot": {
                "ttl_hours": 6,
                "action": "delete",
                "description": "Telemetry buffers, transient caches, debug traces",
            },
            "warm": {
                "ttl_days": 7,
                "action": "compact",
                "description": "Cockpit snapshots, notification queues, NLU logs",
            },
            "cold": {
                "ttl_days": 90,
                "action": "archive",
                "description": "Historical metrics, old audit entries, retired artifacts",
            },
            "staging": {
                "ttl_days": 7,
                "action": "review",
                "description": "Newly introduced state awaiting classification",
            },
        },

        "state_registry": {
            "data/knowledge/": "permanent",
            "data/knowledge_graph/": "permanent",
            "data/knowledge_goals/": "permanent",
            "data/governor_state.json": "permanent",
            "data/governor_proposals.json": "permanent",
            "data/learning/": "permanent",
            "data/subsystems/": "permanent",
            "data/rollback/": "warm",
            "data/entropy/": "permanent",
            "data/audit/": "cold",
            "data/cockpit/": "warm",
            "data/logs/": "hot",
            "data/notifications/": "hot",
            "data/patch_history/": "warm",
            "data/versions/": "cold",
            "config/": "permanent",
            "runtime/state.db": "permanent",
        },

        "forbidden_patterns": [
            "*.tmp",
            "*.bak",
            "__pycache__/",
            "*.pyc",
            ".DS_Store",
        ],
    }


def _ensure_dir():
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)


def load_template() -> Dict[str, Any]:
    _ensure_dir()
    if TEMPLATE_FILE.exists():
        try:
            return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    template = _default_template()
    save_template(template)
    return template


def save_template(template: Dict[str, Any]) -> None:
    _ensure_dir()
    template["last_updated"] = time.time()
    atomic_write_json(TEMPLATE_FILE, template, default=str)


def get_state_tier(path: str) -> str:
    """Classify a path into its state tier using the registry."""
    template = load_template()
    registry = template.get("state_registry", {})

    for registered_path, tier in registry.items():
        if path.startswith(registered_path) or path == registered_path:
            return tier

    return "staging"


def is_permanent(path: str) -> bool:
    return get_state_tier(path) == "permanent"


def register_state(path: str, tier: str) -> Dict[str, Any]:
    """Add a new path to the state registry. Returns the updated registry."""
    template = load_template()
    template["state_registry"][path] = tier
    save_template(template)
    return template["state_registry"]


def add_invariant(name: str, updated_by: str = "operator") -> None:
    """Canonize a new invariant (requires operator approval upstream)."""
    template = load_template()
    if name not in template["invariants"]:
        template["invariants"].append(name)
        template["updated_by"] = updated_by
        save_template(template)


def check_invariants() -> Dict[str, Any]:
    """Verify that all canonical invariants are present in the system."""
    template = load_template()
    present = []
    missing = []
    for inv in template["invariants"]:
        module_name = inv.replace(".", "_")
        try:
            __import__(f"knowledge.{module_name}", fromlist=["_"])
            present.append(inv)
        except ImportError:
            missing.append(inv)
    return {
        "total": len(template["invariants"]),
        "present": len(present),
        "missing": missing,
        "version": template["version"],
    }


def get_template_summary() -> Dict[str, Any]:
    template = load_template()
    return {
        "version": template["version"],
        "invariants": len(template["invariants"]),
        "permanent_paths": len(template["permanent_state"]),
        "state_tiers": list(template["state_tiers"].keys()),
        "registry_entries": len(template["state_registry"]),
        "last_updated": template.get("last_updated"),
    }
