# runtime/feature_flags.py

"""
Minimal feature‑flag system.

The REPL expects:
    - is_enabled(name)
    - safe behavior when called with no args
    - ability to add flags later

This implementation keeps everything OFF by default
unless explicitly enabled.
"""

import threading

_FEATURE_FLAGS = {
    # Example:
    # "background_self_test": True,
}
_ff_lock = threading.Lock()


def is_enabled(name: str = None) -> bool:
    """
    Safe feature‑flag lookup.

    - If called with no name → return False (never crash)
    - If flag not defined → return False
    - If defined → return its value
    """
    if not name:
        return False
    with _ff_lock:
        return _FEATURE_FLAGS.get(name, False)


def enable(name: str) -> None:
    """Enable a feature flag."""
    with _ff_lock:
        _FEATURE_FLAGS[name] = True


def disable(name: str) -> None:
    """Disable a feature flag."""
    with _ff_lock:
        _FEATURE_FLAGS[name] = False
