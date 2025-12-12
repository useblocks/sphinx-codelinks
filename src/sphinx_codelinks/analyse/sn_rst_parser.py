"""Parse reStructuredText (RST) directives using the Lark parser.

This module provides functionality to parse RST directive blocks and extract their components,
such as directive type, title, options, and content for further use by add_need() in src-trace directive.
"""

# ruff: noqa: N802
# TODO: Not sure Lark is the right tool for this job since it has a few limitations such as lack of support for dynamic indentation levels while extracting leading spaces in content.
# Consider switching to Visitor instead of Transformer to have more control on resolving the tree or implement a custom parser if needed.

from typing import TypedDict

from lark import Lark, Transformer, UnexpectedInput, v_args

from sphinx_codelinks.config import UNIX_NEWLINE


class NeedDirectiveType(TypedDict, total=False):
    type: str
    title: str | None
    options: dict[str, str] | None
    content: str | None


@v_args(inline=True)
class DirectiveTransformer(Transformer):  # type: ignore[type-arg] # disable type-arg due to lark Transformer generic issue
    def NAME(self, tok):
        return str(tok)

    def TEXT_NO_COLUMN(self, tok):
        return str(tok).strip()

    def OPTION_NAME(self, tok):
        return str(tok).replace(":", "").strip()

    def OPTION_VALUE(self, tok):
        return str(tok).strip()

    def TEXT(self, tok):
        return str(tok)

    def INDENT(self, tok):
        """Return the length of the indent."""
        return len(str(tok))

    def NEWLINE_IN_CONTENT(self, tok):
        return str(tok)

    def inline_title(self, text):
        return {"title": text}  # strip leading/trailing whitespace

    def option(self, _indent, name, value=None):
        return (name, value)

    def options_block(self, *options):
        return {"options": dict(options)}

    def content_line(self, *line):
        if not line:
            return ""
        if len(line) == 1:
            # it's a NEWLINE_IN_CONTENT
            return line[0].rstrip()
        else:
            # it's an indented TEXT
            return line[1].rstrip()

    def content_block(self, *lines):
        # items are list of lines
        return {"content": "\n".join(lines)}

    def directive_block(self, *blocks):
        return blocks

    def directive(self, name, *optionals):
        # NAME,, optional title/options/content
        need = {"type": name}
        # flatten optionals
        flatten_optionals: list[dict[str, str]] = []
        for item in optionals:
            if isinstance(item, tuple):
                flatten_optionals.extend(item)
            else:
                flatten_optionals.append(item)
        for item in flatten_optionals:
            if "title" in item:
                need["title"] = item["title"]
            elif "options" in item:
                need["options"] = item["options"]
            elif "content" in item:
                need["content"] = item["content"]

        return need


def parse_rst(text: str, num_spaces: int = 3) -> NeedDirectiveType | UnexpectedInput:
    """Parse the given RST directive text and return the parsed data."""
    # Load the grammar
    grammar = rf"""
start: directive

directive: INDENT_DIRECTIVE? ".." _WS NAME "::" _NEWLINE? directive_block?

directive_block: inline_title _NEWLINE | inline_title _NEWLINE options_block (_NEWLINE content_block)? | inline_title _NEWLINE _NEWLINE content_block | _NEWLINE content_block

inline_title: TEXT_NO_COLUMN

options_block: option+

option: INDENT OPTION_NAME _WS? OPTION_VALUE? _NEWLINE

content_block: content_line+

content_line: INDENT TEXT _NEWLINE | _NEWLINE

INDENT: "{" " * num_spaces}"

OPTION_NAME: /:[a-zA-Z0-9_-]+:/

OPTION_VALUE: /[^\n]+/

NAME: /[a-zA-Z0-9_-]+/

TEXT_NO_COLUMN: /(?!.*:[a-zA-Z0-9_-]+:)[^\r\n]+/

TEXT: /[^\r\n]+/

NEWLINE_IN_CONTENT: /\r?\n/

_NEWLINE: /[ \t]*\r?\n/

_WS: /[ \t]+/

INDENT_DIRECTIVE: /[ \t]+/
"""

    processed_text = preprocess_rst(text)

    parser = Lark(
        grammar,
        start="directive",
        parser="lalr",
        propagate_positions=True,
        maybe_placeholders=False,
    )

    try:
        tree = parser.parse(processed_text)
    except UnexpectedInput as e:
        return e
    transformer = DirectiveTransformer()
    result: NeedDirectiveType = transformer.transform(tree)
    return result


def preprocess_rst(text: str) -> str:
    """Process valid RST directive text before parsing.

    The followings are processed:
    - Strip leading spaces before the directive marker to get relative indentations.
    - Strip trailing spaces at the end
    - Ensure the text ends with a newline.
    """
    if not text:
        # empty string, return as is
        return text
    lines = text.splitlines(keepends=False)
    idx_directive = lines[0].find(
        ".."
    )  # expect the first line is the start of the RST directive
    if idx_directive == -1:
        # do nothing and let parser to handle it
        return text

    # remove leading spaces for the relative indentation
    stripped_lines = [line[idx_directive:] for line in lines]
    stripped_text = UNIX_NEWLINE.join(stripped_lines)
    # remove trailing spaces and make sure it ends with newline
    stripped_text = stripped_text.strip() + "\n"
    return stripped_text
