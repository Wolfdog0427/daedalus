# runtime/system_settings.py
"""
In-memory, non-persistent runtime settings.

Provides safe operator knobs for autonomy cadence and promotion
thresholds.  All values are validated on write.
"""

from __future__ import annotations

from typing import Any, Dict

SYSTEM_SETTINGS: Dict[str, Any] = {
    "tier1_cadence_seconds": 300,
    "tier2_promotion_threshold": 5,
}

_SETTING_TYPES: Dict[str, type] = {
    "tier1_cadence_seconds": int,
    "tier2_promotion_threshold": int,
}


def get_system_settings() -> Dict[str, Any]:
    return dict(SYSTEM_SETTINGS)


def get_setting(key: str) -> Any:
    if key not in SYSTEM_SETTINGS:
        raise KeyError(f"unknown setting: {key}")
    return SYSTEM_SETTINGS[key]


def set_setting(key: str, value: Any) -> Dict[str, Any]:
    """
    Update a single runtime setting after validation.

    Returns a result dict — never raises on bad input.
    """
    if key not in SYSTEM_SETTINGS:
        return {
            "updated": False,
            "reason": f"unknown setting '{key}'",
            "key": key,
            "value": value,
        }

    expected = _SETTING_TYPES.get(key)
    if expected and not isinstance(value, expected):
        return {
            "updated": False,
            "reason": f"'{key}' must be {expected.__name__}, got {type(value).__name__}",
            "key": key,
            "value": value,
        }

    if isinstance(value, (int, float)) and value <= 0:
        return {
            "updated": False,
            "reason": f"'{key}' must be > 0, got {value}",
            "key": key,
            "value": value,
        }

    SYSTEM_SETTINGS[key] = value
    return {
        "updated": True,
        "reason": f"'{key}' set to {value}",
        "key": key,
        "value": value,
    }
