# knowledge/debug_cockpit.py

"""
Debugging Cockpit

Central place to:
- capture pipeline snapshots
- record improvement cycles
- record candidates
- record decisions

Backed by simple JSON logs under data/cockpit/.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional

COCKPIT_DIR = Path("data") / "cockpit"
_SAFE_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _safe(name: str) -> str:
    return _SAFE_RE.sub("_", str(name))[:64]


def _ensure_dir() -> None:
    COCKPIT_DIR.mkdir(parents=True, exist_ok=True)


def _write_json(filename: str, payload: Dict[str, Any]) -> str:
    _ensure_dir()
    path = COCKPIT_DIR / filename
    try:
        from knowledge._atomic_io import atomic_write_json
        atomic_write_json(path, payload)
    except ImportError:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
    return str(path)


