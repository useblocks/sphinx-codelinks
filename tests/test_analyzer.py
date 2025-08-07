import json
from pathlib import Path

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer


def test_analyzer(tmp_path, snapshot_anchors):
    src_dir = Path(__file__).parent.parent / "tests" / "data"
    anaylzer = SourceAnalyzer(
        src_dir,
        outdir=tmp_path,
        get_need_id_refs=True,
        get_oneline_needs=True,
        markers=["@need-ids:"],
    )
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
