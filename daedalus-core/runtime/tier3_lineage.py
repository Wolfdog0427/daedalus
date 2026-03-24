# runtime/tier3_lineage.py
"""
Append-only lineage tracking for Tier-3 governance objects.

Records the origin and derivation of policies, profiles, templates,
and governance packs across environments.  The lineage log is
read-only to all other modules — it can only be appended to, never
mutated or deleted.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

_LINEAGE_LOG: List[Dict[str, Any]] = []

_VALID_OBJECT_TYPES = {"policy", "profile", "template", "pack"}
_VALID_OPERATIONS = {"clone", "promote", "import", "override"}


# ------------------------------------------------------------------
# Append
# ------------------------------------------------------------------

def record_lineage(
    object_type: str,
    object_id: str,
    origin_env_id: str,
    derived_env_id: str,
    operation: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append a lineage record.  Returns the new record."""
    if object_type not in _VALID_OBJECT_TYPES:
        return {"error": True,
                "reason": f"unknown object_type '{object_type}'"}
    if operation not in _VALID_OPERATIONS:
        return {"error": True,
                "reason": f"unknown operation '{operation}'"}

    entry = {
        "lineage_id": str(uuid.uuid4()),
        "object_type": object_type,
        "object_id": object_id,
        "origin_env_id": origin_env_id,
        "derived_env_id": derived_env_id,
        "operation": operation,
        "metadata": metadata or {},
        "timestamp": time.time(),
    }
    _LINEAGE_LOG.append(entry)
    return entry


# ------------------------------------------------------------------
# Query (read-only)
# ------------------------------------------------------------------

def get_lineage(
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return lineage records, optionally filtered by type and/or id."""
    results = _LINEAGE_LOG
    if object_type is not None:
        results = [r for r in results if r["object_type"] == object_type]
    if object_id is not None:
        results = [r for r in results if r["object_id"] == object_id]
    return list(results[-limit:])


def get_lineage_for_env(env_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return lineage records where the environment is origin or derived."""
    results = [
        r for r in _LINEAGE_LOG
        if r["origin_env_id"] == env_id or r["derived_env_id"] == env_id
    ]
    return list(results[-limit:])


def get_lineage_log(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_LINEAGE_LOG[-limit:])


def clear_lineage_log() -> None:
    """Reset log (for testing only)."""
    _LINEAGE_LOG.clear()
