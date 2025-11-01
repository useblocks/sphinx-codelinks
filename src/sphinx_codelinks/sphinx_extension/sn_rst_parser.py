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
        return str(tok)

    def OPTION_VALUE(self, tok):
        return str(tok).strip()

    def TEXT(self, tok):
        return str(tok)

    def INDENT(self, tok):
        """Return the length of the indent."""
        return len(str(tok))

    def title(self, title):
        return {"title": title}

    def option(self, _indent, name, value=None):
        return (name, value)

    def options_block(self, *options):
        return {"options": dict(options)}

    def content_line(
        self,
        _indent,
        text,
    ):
        return text

    def content_block(self, *lines):
        # items is list of lines
        return {"content": "\n".join(lines)}

    def directive(self, name, *optionals):
        # NAME,, optional title/options/content
        need = {"type": name}
        for item in optionals:
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
        parser="lalr",
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
