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
    assert "IMPL_VAR_B" in ids
    assert "IMPL_VAR_A" not in ids
    assert "IMPL_PROTO_3" not in ids
