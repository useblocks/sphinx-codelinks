from pathlib import Path

from sphinx_codelinks.needextend_write import convert_marked_content


def test_convert_marked_content(tmp_path):
    jsonpath = Path(__file__).parent / "data" / "analyse" / "marked_content.json"
    outpath = tmp_path / "needextend.rst"
    convert_marked_content(jsonpath, outpath)

    assert outpath.exists()

    with outpath.open("r") as f:
        content = f.readlines()

    assert content
