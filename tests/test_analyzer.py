import json
from pathlib import Path

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer
from sphinx_codelinks.analyzer.config import COMMENT_FILETYPE, SourceAnalyzerConfig
from sphinx_codelinks.source_discovery.source_discover import SourceDiscover


def test_analyzer(tmp_path, snapshot_anchors):
    src_dir = Path(__file__).parent.parent / "tests" / "data"
    src_discovery = SourceDiscover(
        src_dir, gitignore=False, file_types=COMMENT_FILETYPE["cpp"]
    )
    src_anaylizer_config = SourceAnalyzerConfig(
        src_files=src_discovery.source_paths,
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
