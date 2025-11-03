"""Test script for RST directive Lark parser."""

# ruff: noqa: N802
from pathlib import Path

from lark import Lark, Transformer, v_args


@v_args(inline=True)
class DirectiveTransformer(Transformer):
    def NAME(self, tok):
        return str(tok)

    def TITLE(self, tok):
        return str(tok).strip()

    def OPTION_NAME(self, tok):
        return str(tok).replace(":", "").strip()

    def OPTION_VALUE(self, tok):
        return str(tok).strip()

    def TEXT(self, tok):
        return str(tok)

    def TEXT_NO_COLUMN(self, tok):
        return str(tok).strip()

    def INDENT(self, tok):
        """Return the length of the indent."""
        return len(str(tok))

    def NEWLINE_IN_CONTENT(self, tok):
        return str(tok)

    def multi_lines_title(self, *title_line):
        return title_line[1]

    def title_block(self, *titles):
        return {"title": " ".join(titles)}

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
        # items is list of lines
        return {"content": "\n".join(lines)}

    def directive_block(self, *blocks):
        return blocks

    def directive(self, name, *optionals):
        # NAME,, optional title/options/content
        need = {"type": name}
        # flaten optionals
        flatten_optionals = []
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


def get_parser() -> Lark:
    """Get the Lark parser for RST directives."""

    # Load the grammar
    grammar_path = Path(__file__).parent / "sn_rst.lark"
    grammar = grammar_path.read_text()

    parser = Lark(
        grammar,
        start="directive",
        parser="earley",
        propagate_positions=True,
        maybe_placeholders=False,
    )

    return parser


def parse_rst(text: str) -> dict:
    """Parse the given RST directive text and return the parsed data."""
    parser = get_parser()
    tree = parser.parse(text)
    transformer = DirectiveTransformer()
    result = transformer.transform(tree)
    return result
