"""Discover, read, and filter compile_commands.json for libclang."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

_DB_NAME = "compile_commands.json"
_BOUNDARY_MARKERS = (".git", "ubproject.toml", "pyproject.toml")


def find_compile_db(start: Path, project_root: Path | None = None) -> Path | None:
    """Walk up from ``start`` looking for compile_commands.json.

    Stops at (inclusive) the directory that contains the db, or at
    ``project_root`` / a directory containing a boundary marker / fs root.
    """
    current = start if start.is_dir() else start.parent
    current = current.resolve()
    root = project_root.resolve() if project_root else None
    while True:
        candidate = current / _DB_NAME
        if candidate.is_file():
            return candidate
        if root is not None and current == root:
            return None
        if any((current / m).exists() for m in _BOUNDARY_MARKERS):
            return None
        if current.parent == current:  # filesystem root
            return None
        current = current.parent
