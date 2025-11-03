import pytest

from sphinx_codelinks.sphinx_extension.sn_rst_parser import parse_rst


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            ".. req:: ",
            {"type": "req"},
        ),
        (
            ".. req:: no newline",
            {"type": "req", "title": "no newline"},
        ),
        (
            ".. req:: title1\n",
            {"type": "req", "title": "title1"},
        ),
        (
            ".. req:: multi-line title1\n   still title2\n   still title3\n",
            {"type": "req", "title": "multi-line title1 still title2 still title3"},
        ),
        (
            ".. req:: \n   multi-line title1\n   still title2\n   still title3\n",
            {"type": "req", "title": "multi-line title1 still title2 still title3"},
        ),
        (
            ".. impl:: User Authentication\n   :status: open\n   :priority: high\n",
            {
                "type": "impl",
                "title": "User Authentication",
                "options": {"status": "open", "priority": "high"},
            },
        ),
        (
            ".. impl:: no options but content\n\n   This is the implementation content.\n   It spans multiple lines.\n",
            {
                "type": "impl",
                "title": "no options but content",
                "content": "This is the implementation content.\nIt spans multiple lines.",
            },
        ),
        (
            ".. spec:: API Specification\n   :version: 1.0\n   :author: Dev Team\n\n   This specification defines the REST API endpoints.\n",
            {
                "type": "spec",
                "title": "API Specification",
                "options": {"version": "1.0", "author": "Dev Team"},
                "content": "This specification defines the REST API endpoints.",
            },
        ),
        (
            ".. test:: Test Case\n   :status:\n   :priority: low\n",
            {
                "type": "test",
                "title": "Test Case",
                "options": {"status": None, "priority": "low"},
            },
        ),
        (
            ".. impl:: Feature #123: Export\n   :status: in-progress\n",
            {
                "type": "impl",
                "title": "Feature #123: Export",
                "options": {"status": "in-progress"},
            },
        ),
    ],
)
def test_sn_rst_parser(text: str, expected: dict):
    result = parse_rst(text)
    assert result == expected
