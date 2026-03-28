# knowledge/collaborative_memory.py

"""
Collaborative Memory (Multi-Operator Context)

Carries forward operator preferences, institutional knowledge, and
learned workflows across operator generations. Gen-35 benefits from
what Gen-0 taught the system.

Architecture fit:
- Persists to data/collaborative_memory/ directory
- Integrates with self_model.py (operator_context section)
- Periodic consolidation via meta_reasoner maintenance cycle
- All operator interactions are logged with consent metadata
- Governed through integration_layer

The system operates identically with empty collaborative memory —
this is purely additive intelligence.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from knowledge._atomic_io import atomic_write_json

_profiles_lock = threading.Lock()


# ------------------------------------------------------------
# STORAGE
# ------------------------------------------------------------

MEMORY_DIR = Path("data/collaborative_memory")
PROFILES_FILE = MEMORY_DIR / "operator_profiles.json"
INSTITUTIONAL_FILE = MEMORY_DIR / "institutional_memory.json"
INTERACTIONS_FILE = MEMORY_DIR / "interactions.jsonl"


def _ensure_storage():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILES_FILE.exists():
        atomic_write_json(PROFILES_FILE, {})
    if not INSTITUTIONAL_FILE.exists():
        atomic_write_json(INSTITUTIONAL_FILE, {
            "version": 1,
            "created_at": time.time(),
            "patterns": [],
            "preferences": {},
            "domain_expertise": {},
            "workflow_templates": [],
        })


# ------------------------------------------------------------
# OPERATOR PROFILES
# ------------------------------------------------------------

def _load_profiles() -> Dict[str, Any]:
    _ensure_storage()
    try:
        return json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_profiles(profiles: Dict[str, Any]) -> None:
    _ensure_storage()
    atomic_write_json(PROFILES_FILE, profiles)


def record_interaction(
    operator_id: str,
    interaction_type: str,
    details: Dict[str, Any],
) -> None:
    """
    Log an operator interaction for pattern learning.

    interaction_type: "query", "command", "preference", "feedback",
                      "goal_approval", "rejection", "configuration"
    """
    _ensure_storage()

    entry = {
        "operator_id": operator_id,
        "interaction_type": interaction_type,
        "details": details,
        "timestamp": time.time(),
    }

    with INTERACTIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with _profiles_lock:
        profiles = _load_profiles()
        profile = profiles.get(operator_id, _default_profile(operator_id))

        profile["last_active"] = time.time()
        profile["interaction_count"] = profile.get("interaction_count", 0) + 1

        type_counts = profile.get("interaction_types", {})
        type_counts[interaction_type] = type_counts.get(interaction_type, 0) + 1
        profile["interaction_types"] = type_counts

        if interaction_type == "preference":
            prefs = profile.get("preferences", {})
            prefs.update(details)
            profile["preferences"] = prefs

        profiles[operator_id] = profile
        _save_profiles(profiles)


def _default_profile(operator_id: str) -> Dict[str, Any]:
    return {
        "operator_id": operator_id,
        "created_at": time.time(),
        "last_active": time.time(),
        "interaction_count": 0,
        "interaction_types": {},
        "preferences": {},
        "expertise_areas": [],
        "communication_style": "unknown",
    }


def get_operator_profile(operator_id: str) -> Dict[str, Any]:
    """Get the learned profile for a specific operator."""
    profiles = _load_profiles()
    return profiles.get(operator_id, _default_profile(operator_id))


def list_operators() -> List[Dict[str, Any]]:
    """List all known operators with summary stats."""
    profiles = _load_profiles()
    return [
        {
            "operator_id": k,
            "interaction_count": v.get("interaction_count", 0),
            "last_active": v.get("last_active", 0),
        }
        for k, v in profiles.items()
    ]


# ------------------------------------------------------------
# INSTITUTIONAL MEMORY
# ------------------------------------------------------------

def _load_institutional() -> Dict[str, Any]:
    _ensure_storage()
    try:
        return json.loads(INSTITUTIONAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "patterns": [], "preferences": {},
                "domain_expertise": {}, "workflow_templates": []}


def _save_institutional(data: Dict[str, Any]) -> None:
    _ensure_storage()
    atomic_write_json(INSTITUTIONAL_FILE, data)


def get_institutional_memory() -> Dict[str, Any]:
    """Get the aggregated cross-generation knowledge."""
    return _load_institutional()


def suggest_from_history(
    context: str,
    operator_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Draw on past interactions to suggest relevant actions or knowledge.
    Uses operator profile if available, plus institutional patterns.
    """
    suggestions = []
    institutional = _load_institutional()

    for pattern in (institutional.get("patterns") or [])[-50:]:
        pattern_ctx = (pattern.get("context") or "").lower()
        if any(word in context.lower() for word in pattern_ctx.split()[:3]):
            suggestions.append({
                "type": "institutional_pattern",
                "suggestion": pattern.get("action") or "",
                "source": "institutional_memory",
                "confidence": (pattern.get("frequency") or 0) / 10.0,
            })

    if operator_id:
        profile = get_operator_profile(operator_id)
        prefs = profile.get("preferences", {})
        for key, value in prefs.items():
            if key.lower() in context.lower():
                suggestions.append({
                    "type": "operator_preference",
                    "suggestion": f"{key}: {value}",
                    "source": f"operator:{operator_id}",
                    "confidence": 0.7,
                })

    suggestions.sort(key=lambda s: s.get("confidence", 0), reverse=True)
    return suggestions[:10]


# ------------------------------------------------------------
# OPERATOR TRANSITION
# ------------------------------------------------------------

def transfer_context(
    old_operator: str,
    new_operator: str,
) -> Dict[str, Any]:
    """
    Handoff during operator transition. Carries forward relevant
    preferences and institutional knowledge to the new operator's
    profile, while respecting the new operator's autonomy.
    """
    with _profiles_lock:
        old_profile = get_operator_profile(old_operator)
        new_profile = get_operator_profile(new_operator)

        transferred = {
            "domain_context": old_profile.get("expertise_areas", []),
            "workflow_hints": [],
            "preference_suggestions": {},
        }

        old_prefs = old_profile.get("preferences", {})
        for key, value in old_prefs.items():
            if key not in new_profile.get("preferences", {}):
                transferred["preference_suggestions"][key] = value

        new_profile.setdefault("transferred_from", []).append({
            "operator_id": old_operator,
            "timestamp": time.time(),
            "items_transferred": len(transferred["preference_suggestions"]),
        })

        profiles = _load_profiles()
        profiles[new_operator] = new_profile
        _save_profiles(profiles)

    return {
        "action": "context_transfer",
        "from": old_operator,
        "to": new_operator,
        "preferences_suggested": len(transferred["preference_suggestions"]),
        "domains_transferred": len(transferred["domain_context"]),
    }


# ------------------------------------------------------------
# MEMORY CONSOLIDATION (periodic maintenance)
# ------------------------------------------------------------

def run_memory_consolidation() -> Dict[str, Any]:
    """
    Periodic maintenance: merge short-term interactions into long-term
    institutional patterns. Called by the meta_reasoner during
    maintenance cycles.
    """
    _ensure_storage()

    if not INTERACTIONS_FILE.exists():
        return {"action": "memory_consolidation", "processed": 0}

    interactions = []
    try:
        with INTERACTIONS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        interactions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return {"action": "memory_consolidation", "error": "read_failed"}

    if len(interactions) < 10:
        return {"action": "memory_consolidation", "processed": 0,
                "reason": "insufficient_data"}

    institutional = _load_institutional()
    patterns = institutional.get("patterns", [])

    type_freq: Dict[str, int] = {}
    for interaction in interactions[-500:]:
        itype = interaction.get("interaction_type", "")
        type_freq[itype] = type_freq.get(itype, 0) + 1

    for itype, count in type_freq.items():
        if count >= 5:
            existing = [p for p in patterns if p.get("context") == itype]
            if existing:
                existing[0]["frequency"] = count
            else:
                patterns.append({
                    "context": itype,
                    "action": f"Frequent interaction type: {itype}",
                    "frequency": count,
                    "discovered_at": time.time(),
                })

    if len(patterns) > 200:
        patterns = sorted(patterns, key=lambda p: p.get("frequency", 0),
                         reverse=True)[:200]

    institutional["patterns"] = patterns
    institutional["last_consolidated"] = time.time()
    _save_institutional(institutional)

    return {
        "action": "memory_consolidation",
        "processed": len(interactions),
        "patterns_total": len(patterns),
        "new_patterns": len(type_freq),
    }
