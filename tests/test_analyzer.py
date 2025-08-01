from pathlib import Path

import pytest
from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer


@pytest.mark.parametrize(
    ("code", "result"),
    [
        (
            """
                # @req-id: need_001
                def dummy_func1():
                    pass
            """,
            "# @req-id: need_001",
        ),
        (
            """
                def dummy_func1():
                    # @req-id: need_001
                    pass
            """,
            "# @req-id: need_001",
        ),
        (
            """
                def dummy_func1():
                    '''
                    @req-id: need_001
                    '''
                    pass
            """,
            "'''\n                    @req-id: need_001\n                    '''",
        ),
        (
            """
                def dummy_func1():
                    text = '''@req-id: need_001, need_002, this docstring shall not be extracted as comment'''
                    # @req-id: need_001
                    pass
            """,
            "# @req-id: need_001",
        ),
    ],
)
def test_python_comment(code, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"], "python")
    comments: list[TreeSitterNode] = anaylzer.extract_comments(code.encode("utf-8"))
    assert len(comments) == 1
    assert comments[0].text
    assert comments[0].text.decode("utf-8") == result


def test_analyzer():
    src_dir = Path(__file__).parent.parent / "tests" / "data" / "s_core"
    anaylzer = SourceAnalyzer(src_dir, ["@req-id:"])
    anaylzer.create_src_objects()
    anaylzer.extract_markers()

    assert True
