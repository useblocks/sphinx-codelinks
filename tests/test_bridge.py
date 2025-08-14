from pathlib import Path

from sphinx_codelinks.needextend_bridge import convert_marked_content


def test_bridge(tmp_path):
    jsonpath = Path(__file__).parent / "data" / "analyse" / "marked_content.json"
    convert_marked_content(jsonpath, outdir=tmp_path)
    needextend_path = tmp_path / "needextend.rst"

    assert needextend_path.exists()
