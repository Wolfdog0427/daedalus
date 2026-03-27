# knowledge/_atomic_io.py

"""
Atomic file I/O for crash-safe persistence.

All JSON persistence paths that do full-file rewrites must use
atomic_write_json() instead of direct write_text(). This prevents
data corruption if the process crashes mid-write: the temp file
gets orphaned but the original is never corrupted.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, **kwargs) -> None:
    """
    Write JSON data atomically: serialize to a temp file in the same
    directory, then os.replace() to the target path. os.replace() is
    atomic on all major OSes (POSIX rename, Windows MoveFileEx).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    content = json.dumps(data, **kwargs)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".atomic_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
