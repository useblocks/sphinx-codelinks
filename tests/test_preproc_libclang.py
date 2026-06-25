from pathlib import Path

import pytest

clang = pytest.importorskip("clang.cindex")

from sphinx_codelinks.analyse.preproc import loader


def test_load_clang_cindex_returns_module():
    mod = loader.load_clang_cindex()
    assert hasattr(mod, "Index")


def test_parse_options_is_combination():
    # INCOMPLETE | SKIP_FUNCTION_BODIES | DETAILED_PROCESSING_RECORD
    import clang.cindex as cx

    expected = (
        cx.TranslationUnit.PARSE_INCOMPLETE
        | cx.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
        | cx.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    assert loader.PARSE_OPTIONS == expected


def test_skipped_ranges_on_simple_ifdef(tmp_path: Path):
    import clang.cindex as cx

    src = tmp_path / "s.cpp"
    src.write_text(
        "#ifdef OFF\n"
        "// inactive\n"
        "#endif\n"
        "// active\n"
    )
    idx = cx.Index.create()
    tu = idx.parse(str(src), args=["-std=c++17"], options=loader.PARSE_OPTIONS)
    skipped = loader.get_all_skipped_ranges(tu)
    # The #ifdef OFF block is skipped; its range covers line 2.
    assert any(
        sr.start_line <= 2 <= sr.end_line and sr.file == Path(str(src))
        for sr in skipped
    )
