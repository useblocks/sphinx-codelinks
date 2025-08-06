import json
from pathlib import Path

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer


def test_analyzer(tmp_path, snapshot_anchors):
    src_dir = Path(__file__).parent.parent / "tests" / "data" / "anchors"
    anaylzer = SourceAnalyzer(src_dir, ["@req-id:"], outdir=tmp_path)
    anaylzer.git_remote_url = None
    anaylzer.git_commit_rev = None
    anaylzer.run()

    dumped_anchors = tmp_path / "anchors.json"
    with dumped_anchors.open("r") as f:
        anchors = json.load(f)
    # normalize filepath
    for anchor in anchors:
        anchor["filepath"] = Path(anchor["filepath"]).as_posix()
    assert anchors == snapshot_anchors
