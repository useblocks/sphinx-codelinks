"""Discover, read, and filter compile_commands.json for libclang."""

from __future__ import annotations

import json
from pathlib import Path
import shlex

_DB_NAME = "compile_commands.json"
_BOUNDARY_MARKERS = (".git", "ubproject.toml", "pyproject.toml")

# Flags that take a following value we must also drop.
_DROP_WITH_VALUE = {"-o", "-MF", "-MT", "-MQ"}
# Exact flags to drop.
_DROP_EXACT = {"-c", "-MMD", "-MD", "-MG", "-MP"}
# Minimum length for joined-form flags like -MFdep.d (prefix length = 3)
_MIN_JOINED_FLAG_LEN = 3

# Suffixes a compiler builds as a translation unit. A discovered C/C++ file
# absent from compile_commands.json is skipped only when it is a TU source
# (build-excluded); all other discovered files (headers) are parsed standalone.
TU_SOURCE_SUFFIXES = {".c", ".cpp", ".cc", ".cxx"}


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


def filter_args(argv: list[str], input_file: str) -> list[str]:
    """Keep only flags libclang needs; drop the compiler, -c/-o, depfiles, input."""
    out: list[str] = []
    skip_next = False
    input_names = {input_file, str(Path(input_file).name), str(Path(input_file))}
    for i, arg in enumerate(argv):
        if i == 0:
            continue  # argv[0] == compiler
        if skip_next:
            skip_next = False
            continue
        if arg in _DROP_WITH_VALUE:
            skip_next = True
            continue
        if arg in _DROP_EXACT:
            continue
        if arg.startswith(("-MF", "-MT", "-MQ")) and len(arg) > _MIN_JOINED_FLAG_LEN:
            continue  # joined form, e.g. -MFdep.d
        if arg in input_names:
            continue
        out.append(arg)
    return out


def load_flags_map(db_path: Path) -> dict[Path, list[str]]:
    """Parse compile_commands.json -> {absolute file path: filtered args}."""
    entries = json.loads(db_path.read_text())
    flags: dict[Path, list[str]] = {}
    for entry in entries:
        if "file" not in entry or "directory" not in entry:
            continue  # malformed entry: skip, keep going
        if "arguments" in entry:
            argv = list(entry["arguments"])
        elif "command" in entry:
            argv = shlex.split(entry["command"])
        else:
            continue
        directory = Path(entry["directory"])
        file_field = entry["file"]
        abs_file = (directory / file_field).resolve()
        flags[abs_file] = filter_args(argv, file_field)
    return flags


def defines_to_args(
    defines: list[str], includes: list[Path], std: str = "c++17"
) -> list[str]:
    """Build a global flag list for the manual `defines` fallback."""
    args = [f"-std={std}"]
    args += [f"-D{d}" for d in defines]
    args += [f"-I{inc}" for inc in includes]
    return args


def is_translation_unit_source(path: Path) -> bool:
    """True if ``path`` is a compiled translation-unit source (not a header).

    compile_commands.json lists one entry per compiled TU; headers are never
    entries. So a discovered file absent from the DB is skipped only when it is
    a TU source; header-like files are parsed standalone (see _resolve_preproc_args).
    """
    return path.suffix.lower() in TU_SOURCE_SUFFIXES
