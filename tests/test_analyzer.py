from pathlib import Path

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer


def test_analyzer():
    src_dir = Path(__file__).parent.parent / "tests" / "data" / "s_core"
    anaylzer = SourceAnalyzer(src_dir)
    anaylzer.extract_comments()

    assert True
