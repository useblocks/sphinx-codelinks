import json
from pathlib import Path

import pytest

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer
from sphinx_codelinks.analyzer.config import SourceAnalyzerConfig

TEST_DATA_DIR = Path(__file__).parent.parent / "tests" / "data"


@pytest.mark.parametrize(
    ("src_dir", "src_paths"),
    [
        (
            TEST_DATA_DIR,
            [
                TEST_DATA_DIR / "oneline_comment_default" / "default_oneliners.c",
                TEST_DATA_DIR / "need_id_refs" / "dummy_1.cpp",
                TEST_DATA_DIR / "marked_rst" / "dummy_1.cpp",
            ],
        )
    ],
)
def test_analyzer(src_dir, src_paths, tmp_path, snapshot_anchors):
    src_anaylizer_config = SourceAnalyzerConfig(
        src_files=src_paths,
        src_dir=src_dir,
        outdir=tmp_path,
        get_need_id_refs=True,
        get_oneline_needs=True,
        get_rst=True,
    )

    anaylzer = SourceAnalyzer(src_anaylizer_config)
    anaylzer.git_remote_url = None
    anaylzer.git_commit_rev = None
    anaylzer.run()

    dumped_content = tmp_path / "marked_content.json"
    with dumped_content.open("r") as f:
        marked_content = json.load(f)
    # normalize filepath
    for obj in marked_content:
        obj["filepath"] = Path(obj["filepath"]).as_posix()
    assert marked_content == snapshot_anchors
