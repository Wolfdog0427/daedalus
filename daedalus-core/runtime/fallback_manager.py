# runtime/fallback_manager.py

"""
Fallback manager

Tracks subsystem health and enables/disables features when they misbehave.
Fully verbose: logs every change in fallback state.
"""

from typing import Dict, Any

_fallback_state: Dict[str, Dict[str, Any]] = {
    # name -> {enabled: bool, reason: str}
    "fuzzy_repair": {"enabled": True, "reason": ""},
    "debug_cockpit": {"enabled": True, "reason": ""},
    "watch_monitor": {"enabled": True, "reason": ""},
}


def mark_subsystem_failed(name: str, reason: str) -> None:
    if name not in _fallback_state:
        _fallback_state[name] = {"enabled": False, "reason": reason}
    else:
        _fallback_state[name]["enabled"] = False
        _fallback_state[name]["reason"] = reason
    print(f"[fallback] DISABLED '{name}' — {reason}")


def mark_subsystem_ok(name: str) -> None:
    if name not in _fallback_state:
        _fallback_state[name] = {"enabled": True, "reason": ""}
    else:
        if not _fallback_state[name]["enabled"]:
            print(f"[fallback] RE-ENABLED '{name}'")
        _fallback_state[name]["enabled"] = True
        _fallback_state[name]["reason"] = ""


def is_enabled(name: str = None) -> bool:
    """
    Safe feature check.

    - If called with no name → return False
    - If subsystem not registered → return False
    - Otherwise → return its enabled state
    """
    if not name:
        return False

    info = _fallback_state.get(name)
    if info is None:
        return False

    return bool(info["enabled"])


def get_fallback_snapshot() -> Dict[str, Dict[str, Any]]:
    return {k: dict(v) for k, v in _fallback_state.items()}
