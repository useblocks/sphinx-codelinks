from lark import UnexpectedInput
import pytest

from sphinx_codelinks.analyse.sn_rst_parser import parse_rst, preprocess_rst


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Minimal directive - only type, no title/options/content
        (
            ".. req::",
            {"type": "req"},
        ),
        # Minimal directive - with trailing space no newline
        (
            ".. req::      ",
            {"type": "req"},
        ),
        # Minimal directive - only type, no title/options/content
        (
            ".. req::\n",
            {"type": "req"},
        ),
        # Simple inline title with trailing spaces without newline
        (
            ".. req:: title1  ",
            {"type": "req", "title": "title1"},
        ),
        # Simple inline title on same line as directive marker
        (
            ".. req:: title1\n",
            {"type": "req", "title": "title1"},
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
        # comment in content
        (
            ".. spec:: comment in content\n   :option: value\n\n   .. commentline\n   Content without blank line.\n",
            {
                "type": "spec",
                "title": "comment in content",
                "options": {"option": "value"},
                "content": ".. commentline\nContent without blank line.",
            },
        ),
        (
            """.. test-case:: test_xyz
   :file: test_reports/abc.xml
   :suite: test_abc
   :case: test_xyz
   :id: SW_TEST_CASE_XYZ
   :release: abc-1.2.3
   :uplink: SW_UNIT_IF_XYZ

   Test case to verify xyz does behavior abc
    """,
            {
                "type": "test-case",
                "title": "comment in content",
                "options": {"option": "value"},
                "content": ".. commentline\nContent without blank line.",
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
        # multiline title not allowed
        (".. req:: Title line one\n   Title line two\n"),
        # non-inline/indented title not allowed
        (".. req:: \n   Title line one\n"),
    ],
)
def test_sn_rst_parser_negative(text: str):
    warning = parse_rst(text)
    assert isinstance(warning, UnexpectedInput)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # No leading chars - text is already properly aligned
        (
            ".. req:: Title\n",
            ".. req:: Title\n",
        ),
        # Single line without newline - adds newline and strips leading/trailing spaces
        (
            ".. req:: Title",
            ".. req:: Title\n",
        ),
        # Single line with 3 leading spaces - strips and adds newline
        (
            "   .. req:: Title",
            ".. req:: Title\n",
        ),
        # Multi-line with consistent indentation - no change
        (
            ".. req:: Title\n   :option: value\n",
            ".. req:: Title\n   :option: value\n",
        ),
        # Text with 3 leading spaces before directive marker
        (
            "   .. req:: 3 leading spaces\n      :option: value\n",
            ".. req:: 3 leading spaces\n   :option: value\n",
        ),
        # Empty string - returns newline (edge case)
        (
            "",
            "",
        ),
        # Only whitespace - strips and adds newline
        (
            "   ",
            "   ",
        ),
        # No directive marker found - returns as-is with newline added if missing
        (
            "This is not a directive",
            "This is not a directive",
        ),
        # Directive marker not at expected position - handles gracefully
        (
            "Some text .. req:: Title\n",
            ".. req:: Title\n",
        ),
        # Multi-line with trailing spaces
        (
            ".. req:: Title   \n   :option: value   \n",
            ".. req:: Title   \n   :option: value\n",
        ),
        # Multi-line with trailing spaces and content
        (
            ".. req:: Title   \n   :option: value   \n\n   This is the content.   \n",
            ".. req:: Title   \n   :option: value   \n\n   This is the content.\n",
        ),
        # Multi-line with trailing and leading spaces and content
        (
            "  .. req:: Title   \n     :option: value     \n\n     This is the content.   \n",
            ".. req:: Title   \n   :option: value     \n\n   This is the content.\n",
        ),
    ],
)
def test_preprocess_rst(text: str, expected: str):
    """Test preprocess_rst function normalizes input for parser."""
    result = preprocess_rst(text)
    assert result == expected
