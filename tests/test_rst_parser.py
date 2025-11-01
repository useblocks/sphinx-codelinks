import pytest

from sphinx_codelinks.sphinx_extension.sn_rst_parser import parse_rst


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            ".. req:: title1\n",
            {"type": "req", "title": "title1"},
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
            ".. impl:: Data Processing\n\n   This is the implementation content.\n   It spans multiple lines.\n",
            {
                "type": "impl",
                "title": "Data Processing",
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
