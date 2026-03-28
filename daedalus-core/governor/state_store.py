# governor/state_store.py

from __future__ import annotations

import contextlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Generator, List

from knowledge._atomic_io import atomic_write_json

_state_file_lock = threading.RLock()

STATE_DIR = Path("data")
STATE_PATH = STATE_DIR / "governor_state.json"
PROPOSALS_PATH = STATE_DIR / "governor_proposals.json"
_LOCK_FILE = STATE_DIR / ".governor_state.lock"


class _FileLock:
    """Cross-process advisory file lock for multi-node safety."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self._path), os.O_CREAT | os.O_RDWR)
        try:
            import msvcrt
            msvcrt.locking(self._fd, msvcrt.LK_LOCK, 1)
        except ImportError:
            import fcntl
            fcntl.flock(self._fd, fcntl.LOCK_EX)

    def release(self) -> None:
        if self._fd is not None:
            try:
                try:
                    import msvcrt
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                except ImportError:
                    import fcntl
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None


def _default_state() -> Dict[str, Any]:
    return {
        "autonomy_mode": "strict",
        "locked": False,
        "current_tier": 1,
        "drift": {},
        "stability": {},
        "patch_history": {
            "total_cycles": 0,
            "successful_patches": 0,
            "failed_patches": 0,
            "reverted_patches": 0,
            "failed_high_level_cycles": 0,
            "failed_tier2_cycles": 0,
            "recent_failures": [],
        },
        "escalation": {},
        "proposals": {
            "pending": [],
            "recent_decisions": [],
        },
    }


def load_state() -> Dict[str, Any]:
    with _state_file_lock:
        if not STATE_PATH.exists():
            return _default_state()
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return _default_state()
        if not isinstance(data, dict):
            return _default_state()
        base = _default_state()
        base.update(data)
        proposals = base.get("proposals")
        if not isinstance(proposals, dict):
            base["proposals"] = {"pending": [], "recent_decisions": []}
        else:
            if not isinstance(proposals.get("pending"), list):
                proposals["pending"] = []
            if not isinstance(proposals.get("recent_decisions"), list):
                proposals["recent_decisions"] = []
        ph = base.get("patch_history")
        if not isinstance(ph, dict):
            base["patch_history"] = _default_state()["patch_history"]
        else:
            defaults = _default_state()["patch_history"]
            for k, v in defaults.items():
                ph.setdefault(k, v)
        return base


def save_state(state: Dict[str, Any]) -> None:
    with _state_file_lock:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_json(STATE_PATH, state)


@contextlib.contextmanager
def mutate_state() -> Generator[Dict[str, Any], None, None]:
    """Atomic read-modify-write for governor state.

    Holds both the in-process thread lock AND a cross-process file lock
    for the entire duration, preventing lost updates in multi-node
    deployments where multiple Daedalus processes share the same data dir.

    Usage::

        with mutate_state() as state:
            state["current_tier"] = 2
        # state is automatically persisted on clean exit
    """
    flock = _FileLock(_LOCK_FILE)
    flock.acquire()
    try:
        with _state_file_lock:
            state = load_state()
            yield state
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            atomic_write_json(STATE_PATH, state)
    finally:
        flock.release()


def load_proposals() -> List[Dict[str, Any]]:
    with _state_file_lock:
        if not PROPOSALS_PATH.exists():
            return []
        try:
            data = json.loads(PROPOSALS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return []
        return data if isinstance(data, list) else []


def save_proposals(proposals: List[Dict[str, Any]]) -> None:
    with _state_file_lock:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_json(PROPOSALS_PATH, proposals)
