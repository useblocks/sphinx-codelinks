from lark import UnexpectedInput
import pytest

from sphinx_codelinks.analyse.sn_rst_parser import parse_rst


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Minimal directive - only type, no title/options/content
        (
            ".. req::\n",
            {"type": "req"},
        ),
        # Simple inline title on same line as directive marker
        (
            ".. req:: title1\n",
            {"type": "req", "title": "title1"},
        ),
        # Inline title + indented continuation lines (TEXT_NO_COLUMN concatenates multi-line titles)
        (
            ".. req:: multi-line title1\n   still title2\n   still title3\n",
            {"type": "req", "title": "multi-line title1 still title2 still title3"},
        ),
        # Title entirely on indented lines (title_block alternative: _NEWLINE multi_lines_title+)
        (
            ".. req:: \n   multi-line title1\n   still title2\n   still title3\n",
            {"type": "req", "title": "multi-line title1 still title2 still title3"},
        ),
        # Indented title stops at option line (TEXT_NO_COLUMN rejects :option: pattern)
        (
            ".. req:: \n   multi-line title1\n   still title2\n   :option:\n",
            {
                "type": "req",
                "title": "multi-line title1 still title2",
                "options": {"option": None},
            },
        ),
        # Title + content block with blank line separator (directive_block content path)
        (
            ".. impl:: no options but content\n\n   This is the implementation content.\n   It spans multiple lines.\n",
            {
                "type": "impl",
                "title": "no options but content",
                "content": "This is the implementation content.\nIt spans multiple lines.",
            },
        ),
        # Title + options + content (complete directive_block: options_block + _NEWLINE content_block)
        (
            ".. spec:: API Specification\n   :version: 1.0\n   :author: Dev Team\n\n   This specification defines the REST API endpoints.\n",
            {
                "type": "spec",
                "title": "API Specification",
                "options": {"version": "1.0", "author": "Dev Team"},
                "content": "This specification defines the REST API endpoints.",
            },
        ),
        # Empty option values (OPTION_VALUE? optional in option rule)
        (
            ".. test:: Test Case\n   :status:\n   :priority: low\n",
            {
                "type": "test",
                "title": "Test Case",
                "options": {"status": None, "priority": "low"},
            },
        ),
        # Title with special characters - single colons allowed (only :word: pattern forbidden)
        (
            ".. impl:: Feature #123: Export\n   :status: in-progress\n",
            {
                "type": "impl",
                "title": "Feature #123: Export",
                "options": {"status": "in-progress"},
            },
        ),
        # Trailing spaces in title trimmed (_NEWLINE: /[ \t]*\r?\n/ consumes whitespace)
        (
            ".. req:: title with spaces   \n",
            {"type": "req", "title": "title with spaces"},
        ),
        # Inline title continuation + options (multi_lines_title* stops at :option: line)
        (
            ".. impl:: Initial title\n   continuation of title\n   :status: active\n",
            {
                "type": "impl",
                "title": "Initial title continuation of title",
                "options": {"status": "active"},
            },
        ),
        # Multiple options with empty values (option+ with multiple OPTION_VALUE? None)
        (
            ".. test:: Test\n   :tag1:\n   :tag2:\n   :tag3:\n",
            {
                "type": "test",
                "title": "Test",
                "options": {"tag1": None, "tag2": None, "tag3": None},
            },
        ),
        # Option value with special chars (OPTION_VALUE: /[^\n]+/ accepts URLs, commas, hyphens)
        (
            ".. impl:: Feature\n   :link: https://example.com/issue#123\n   :tags: feature,ui,high-priority\n",
            {
                "type": "impl",
                "title": "Feature",
                "options": {
                    "link": "https://example.com/issue#123",
                    "tags": "feature,ui,high-priority",
                },
            },
        ),
        # Option value containing colons (colons inside OPTION_VALUE are allowed)
        (
            ".. req:: Requirement\n   :time: 10:30 AM\n",
            {
                "type": "req",
                "title": "Requirement",
                "options": {"time": "10:30 AM"},
            },
        ),
        # Unicode characters in title (NAME, TITLE, TEXT_NO_COLUMN handle non-ASCII)
        (
            ".. req:: Función de exportación 导出功能\n",
            {"type": "req", "title": "Función de exportación 导出功能"},
        ),
        # Content with blank lines between paragraphs (multiple newlines in content block)
        (
            ".. impl:: Feature\n\n   First paragraph.\n   Still first paragraph.\n\n   Second paragraph here.\n   Still second paragraph.\n",
            {
                "type": "impl",
                "title": "Feature",
                "content": "First paragraph.\nStill first paragraph.\n\nSecond paragraph here.\nStill second paragraph.",
            },
        ),
        # Complex case: inline title + continuation + options + content (all grammar paths)
        (
            ".. spec:: Main Title\n   Title continuation\n   :version: 2.0\n   :author: Team\n\n   Content paragraph one.\n   Content paragraph two.\n",
            {
                "type": "spec",
                "title": "Main Title Title continuation",
                "options": {"version": "2.0", "author": "Team"},
                "content": "Content paragraph one.\nContent paragraph two.",
            },
        ),
    ],
)
def test_sn_rst_parser_positive(text: str, expected: dict):
    result = parse_rst(text)
    assert result == expected


@pytest.mark.parametrize(
    ("text"),
    [
        # Missing directive type
        (".. :: Missing type\n"),
        # Improper indentation (option line not indented)
        (".. impl:: Title\n:option: value\n"),
        # Content without blank line separator
        (".. spec:: Title\n   :option: value\n   Content without blank line.\n"),
        # Invalid characters in directive type
        (".. re@q:: Invalid type\n"),
        # Title line that looks like an option
        (".. req:: :notanoption:\n"),
        # Content block without proper indentation
        (".. impl:: Title\nContent not indented properly.\n"),
    ],
)
def test_sn_rst_parser_negative(text: str):
    warning = parse_rst(text)
    assert isinstance(warning, UnexpectedInput)
