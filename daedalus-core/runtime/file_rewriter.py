# runtime/file_rewriter.py

from __future__ import annotations

from typing import Callable
import os
import shutil
import tempfile


def rewrite_file_atomic(path: str, transform: Callable[[str], str]) -> None:
    """
    Safely rewrite a file:
    - Read original
    - Apply transform(text) -> new_text
    - Write to temp file
    - Atomically replace original
    """

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    new_text = transform(original)

    dir_name = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".rewrite_", suffix=".tmp")
    os.close(fd)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        shutil.move(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
