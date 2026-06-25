"""Parse a C/C++ TU via libclang and yield ACTIVE comment tokens only."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sphinx_codelinks.analyse.preproc import loader


@dataclass
class _Point:
    row: int


class LibclangComment:
    """Minimal stand-in for a tree-sitter comment node.

    Exposes exactly the two attributes the existing extract_* chain reads:
    ``.text`` (bytes) and ``.start_point.row`` (0-indexed). ``is_libclang``
    lets extract_marked_content skip tree-sitter scope association.
    """

    is_libclang = True

    def __init__(self, text: bytes, row: int) -> None:
        self.text: bytes = text
        self.start_point = _Point(row)


def _is_in_skipped(file_path: str, line: int, skipped) -> bool:  # type: ignore[no-untyped-def]
    for sr in skipped:
        if sr.file is None or str(sr.file) != file_path:
            continue
        if sr.start_line <= line <= sr.end_line:
            return True
    return False


def extract_active_comments(file_path: Path, args: list[str]) -> list[LibclangComment]:
    """Return one LibclangComment per ACTIVE comment token in ``file_path``.

    Comments inside preprocessor-skipped (inactive) ranges are dropped.
    """
    cx = loader.load_clang_cindex()
    index = cx.Index.create()
    tu = index.parse(str(file_path), args=args, options=loader.PARSE_OPTIONS)
    skipped = loader.get_all_skipped_ranges(tu)

    line_count = len(file_path.read_text(encoding="utf-8").splitlines())
    main = tu.get_file(str(file_path))
    extent = cx.SourceRange.from_locations(
        cx.SourceLocation.from_position(tu, main, 1, 1),
        cx.SourceLocation.from_position(tu, main, line_count + 1, 1),
    )

    out: list[LibclangComment] = []
    for tok in tu.get_tokens(extent=extent):
        if tok.kind != cx.TokenKind.COMMENT:
            continue
        loc = tok.location
        if loc.file is None:
            continue
        if _is_in_skipped(str(loc.file.name), loc.line, skipped):
            continue  # inactive branch -> excluded
        spelling = tok.spelling or ""
        out.append(LibclangComment(spelling.encode("utf-8"), loc.line - 1))
    return out
