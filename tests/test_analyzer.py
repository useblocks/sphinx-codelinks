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


@pytest.mark.parametrize(
    ("code", "result"),
    [
        (
            """
                // @req-id: need_001
                void dummy_func1(){
                }
            """,
            "// @req-id: need_001",
        ),
        (
            """
                void dummy_func1(){
                // @req-id: need_001
                }
            """,
            "// @req-id: need_001",
        ),
        (
            """
                /* @req-id: need_001 */
                void dummy_func1(){
                }
            """,
            "/* @req-id: need_001 */",
        ),
    ],
)
def test_cpp_comment(code, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"], "cpp")
    comments: list[TreeSitterNode] = anaylzer.extract_comments(code.encode("utf-8"))
    assert len(comments) == 1
    assert comments[0].text
    assert comments[0].text.decode("utf-8") == result


@pytest.mark.parametrize(
    ("comment", "result"),
    [
        ("""// @req-id: need_001""", ("@req-id:", ["need_001"], 0)),
        (
            """// @req-id: need_001 need_002""",
            [("@req-id:", ["need_001", "need_002"], 0)],
        ),
        (
            """/*
            * @req-id: need_001 need_002
            */""",
            [("@req-id:", ["need_001", "need_002"], 1)],
        ),
        (
            """/*
            * @req-id: need_001 need_002
            * @req-id: need_003
            */""",
            [("@req-id:", ["need_001", "need_002"], 1), ("@req-id:", ["need_003"], 2)],
        ),
    ],
)
def test_extract_marker(comment, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"])
    for i, (marker, need_ids, row_offset) in enumerate(
        anaylzer.extract_marker(comment)
    ):
        assert (marker, need_ids, row_offset) == result[i]


def test_analyzer():
    src_dir = Path(__file__).parent.parent / "tests" / "data" / "s_core"
    anaylzer = SourceAnalyzer(src_dir, ["@req-id:"])
    anaylzer.create_src_objects()
    anaylzer.extract_markers()

    assert True
