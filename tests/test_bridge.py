from pathlib import Path

from sphinx_codelinks.bridge import convert_makred_content


def test_bridge():
    jsonpath = Path(__file__).parent / "data" / "analyse" / "marked_content.json"
    convert_makred_content(jsonpath, outdir=Path(__file__).parent.parent / "output")
