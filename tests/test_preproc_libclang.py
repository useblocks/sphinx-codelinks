from pathlib import Path

import pytest

clang = pytest.importorskip("clang.cindex")

from sphinx_codelinks.analyse.preproc import libclang_parser, loader


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
    src.write_text("#ifdef OFF\n// inactive\n#endif\n// active\n")
    idx = cx.Index.create()
    tu = idx.parse(str(src), args=["-std=c++17"], options=loader.PARSE_OPTIONS)
    skipped = loader.get_all_skipped_ranges(tu)
    # The #ifdef OFF block is skipped; its range covers line 2.
    assert any(
        sr.start_line <= 2 <= sr.end_line and sr.file == Path(str(src))
        for sr in skipped
    )


FIXTURE = Path(__file__).parent / "data" / "preproc" / "variants_branching.cpp"


def _titles(comments):
    out = []
    for c in comments:
        text = c.text.decode("utf-8")
        if "@" in text:
            out.append(text)
    return out


def test_extract_active_comments_variant_a_active():
    args = [
        "-std=c++17",
        "-DVARIANT_A=1",
        "-DPLATFORM_LINUX=1",
        "-DPROTOCOL_VERSION=3",
    ]
    comments = libclang_parser.extract_active_comments(FIXTURE, args)
    titles = _titles(comments)
    joined = "\n".join(titles)
    assert "IMPL_ALWAYS" in joined
    assert "IMPL_VAR_A" in joined  # active branch
    assert "IMPL_VAR_B" not in joined  # inactive #else -> EXCLUDED
    assert "IMPL_PROTO_3" in joined  # PROTOCOL_VERSION >= 3 active
    assert "IMPL_LINUX_A" in joined  # both defined


def test_extract_active_comments_variant_b_active():
    args = ["-std=c++17", "-DPROTOCOL_VERSION=1"]  # VARIANT_A undefined
    comments = libclang_parser.extract_active_comments(FIXTURE, args)
    joined = "\n".join(_titles(comments))
    assert "IMPL_VAR_B" in joined  # #else branch now active
    assert "IMPL_VAR_A" not in joined  # inactive -> EXCLUDED
    assert "IMPL_PROTO_3" not in joined  # version < 3 -> EXCLUDED
    assert "IMPL_LINUX_A" not in joined  # VARIANT_A undefined -> EXCLUDED
