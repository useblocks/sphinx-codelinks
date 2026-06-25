import json
from pathlib import Path

import pytest

pytest.importorskip("clang.cindex")

from sphinx_codelinks.analyse.analyse import SourceAnalyse
from sphinx_codelinks.config import PreprocessorConfig, SourceAnalyseConfig

FIXTURE = Path(__file__).parent / "data" / "preproc" / "variants_branching.cpp"


def _run_get_oneline_ids(defines):
    cfg = SourceAnalyseConfig(
        src_files=[FIXTURE],
        src_dir=FIXTURE.parent,
        get_need_id_refs=False,
        get_oneline_needs=True,
        get_rst=False,
        preprocessor=PreprocessorConfig(defines=defines),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()
    return {n.need["id"] for n in analyse.oneline_needs}


def test_libclang_engine_excludes_inactive_markers():
    ids = _run_get_oneline_ids(["VARIANT_A=1", "PLATFORM_LINUX=1", "PROTOCOL_VERSION=3"])
    assert "IMPL_ALWAYS" in ids
    assert "IMPL_VAR_A" in ids
    assert "IMPL_VAR_B" not in ids  # inactive
    assert "IMPL_PROTO_3" in ids
    assert "IMPL_LINUX_A" in ids


def test_libclang_engine_other_variant():
    ids = _run_get_oneline_ids(["PROTOCOL_VERSION=1"])
    assert "IMPL_ALWAYS" in ids
    assert "IMPL_VAR_B" in ids
    assert "IMPL_VAR_A" not in ids
    assert "IMPL_PROTO_3" not in ids


def test_libclang_engine_via_compile_commands(tmp_path):
    db = tmp_path / "compile_commands.json"
    db.write_text(
        json.dumps(
            [
                {
                    "directory": str(FIXTURE.parent),
                    "arguments": [
                        "clang++", "-std=c++17", "-DVARIANT_A=1",
                        "-DPROTOCOL_VERSION=3", "-c", str(FIXTURE),
                    ],
                    "file": str(FIXTURE),
                }
            ]
        )
    )
    cfg = SourceAnalyseConfig(
        src_files=[FIXTURE],
        src_dir=FIXTURE.parent,
        get_oneline_needs=True,
        preprocessor=PreprocessorConfig(compile_commands=db),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()
    ids = {n.need["id"] for n in analyse.oneline_needs}
    assert "IMPL_VAR_A" in ids
    assert "IMPL_VAR_B" not in ids
    assert "IMPL_PROTO_3" in ids
    assert "IMPL_LINUX_A" not in ids


def test_libclang_resilient_to_broken_code():
    broken = FIXTURE.parent / "variants_broken.cpp"
    cfg = SourceAnalyseConfig(
        src_files=[broken],
        src_dir=broken.parent,
        get_oneline_needs=True,
        preprocessor=PreprocessorConfig(defines=[]),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()
    ids = {n.need["id"] for n in analyse.oneline_needs}
    assert ids == {"IMPL_DESPITE", "IMPL_AFTER_BROKEN"}


def test_libclang_resilient_to_half_typed_code():
    half = FIXTURE.parent / "half_typed.cpp"
    cfg = SourceAnalyseConfig(
        src_files=[half],
        src_dir=half.parent,
        get_oneline_needs=True,
        preprocessor=PreprocessorConfig(defines=[]),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()
    ids = {n.need["id"] for n in analyse.oneline_needs}
    # All 4 markers survive at the token level even though 2 decls don't parse.
    assert {"IMPL_COMPLETE", "IMPL_HALF", "IMPL_AFTER", "IMPL_MID"} <= ids


def test_libclang_active_matches_treesitter_when_all_active():
    """When every branch is active, libclang output == tree-sitter output."""
    # Tree-sitter path (no preprocessor block) sees ALL markers.
    ts_cfg = SourceAnalyseConfig(
        src_files=[FIXTURE], src_dir=FIXTURE.parent, get_oneline_needs=True
    )
    ts = SourceAnalyse(ts_cfg)
    ts.git_remote_url = None
    ts.git_commit_rev = None
    ts.run()
    ts_ids = {n.need["id"] for n in ts.oneline_needs}

    # libclang with both variants' guards satisfied is impossible (#else is
    # mutually exclusive), so compare the union over both variants instead.
    a = _run_get_oneline_ids(["VARIANT_A=1", "PLATFORM_LINUX=1", "PROTOCOL_VERSION=3"])
    b = _run_get_oneline_ids(["PROTOCOL_VERSION=1"])
    assert ts_ids == (a | b)


def test_libclang_skip_file_absent_from_compile_commands(tmp_path):
    """Files absent from a compile DB are skipped (spec §3.3)."""
    # DB contains only FIXTURE; half_typed.cpp is intentionally absent.
    other = FIXTURE.parent / "half_typed.cpp"
    db = tmp_path / "compile_commands.json"
    db.write_text(
        json.dumps(
            [
                {
                    "directory": str(FIXTURE.parent),
                    "arguments": [
                        "clang++", "-std=c++17", "-DVARIANT_A=1",
                        "-DPROTOCOL_VERSION=3", "-c", str(FIXTURE),
                    ],
                    "file": str(FIXTURE),
                }
            ]
        )
    )
    cfg = SourceAnalyseConfig(
        src_files=[FIXTURE, other],
        src_dir=FIXTURE.parent,
        get_oneline_needs=True,
        preprocessor=PreprocessorConfig(compile_commands=db),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()
    ids = {n.need["id"] for n in analyse.oneline_needs}
    # FIXTURE is in the DB — its markers must appear.
    assert "IMPL_VAR_A" in ids
    assert "IMPL_PROTO_3" in ids
    # half_typed.cpp is NOT in the DB — it must be skipped entirely.
    assert "IMPL_COMPLETE" not in ids
    assert "IMPL_HALF" not in ids
    assert "IMPL_AFTER" not in ids
    assert "IMPL_MID" not in ids


def test_libclang_active_matches_golden():
    """Cross-impl parity: Python libclang output matches shared Rust golden."""
    cfg = SourceAnalyseConfig(
        src_files=[FIXTURE],
        src_dir=FIXTURE.parent,
        get_oneline_needs=True,
        preprocessor=PreprocessorConfig(defines=["VARIANT_A=1", "PLATFORM_LINUX=1", "PROTOCOL_VERSION=3"]),
    )
    analyse = SourceAnalyse(cfg)
    analyse.git_remote_url = None
    analyse.git_commit_rev = None
    analyse.run()

    # Project each OneLineNeed to a dict matching the golden schema.
    projected = [
        {
            "id": n.need["id"],
            "title": n.need["title"],
            "type": n.need["type"],
            "links": n.need["links"],
            "line": n.source_map["start"]["row"] + 1,
        }
        for n in analyse.oneline_needs
    ]
    projected.sort(key=lambda x: x["line"])

    # Load the golden and sort by line.
    golden_path = FIXTURE.parent / "variants_branching.expected.json"
    with golden_path.open() as f:
        golden = json.load(f)
    golden.sort(key=lambda x: x["line"])

    assert projected == golden
