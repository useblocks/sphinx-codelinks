from collections.abc import ByteString, Callable
import configparser
import logging
from pathlib import Path
from typing import TypedDict
from urllib.request import pathname2url

from giturlparse import parse  # type: ignore[import-untyped]
from tree_sitter import Language, Parser, Point, Query, QueryCursor
from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.config import UNIX_NEWLINE, CommentCategory
from sphinx_codelinks.source_discover.config import CommentType

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

GIT_HOST_URL_TEMPLATE = {
    "github": "https://github.com/{owner}/{repo}/blob/{rev}/{path}#L{lineno}",
    "gitlab": "https://gitlab.com/{owner}/{repo}/-/blob/{rev}/{path}#L{lineno}",
}

PYTHON_QUERY = """
                ; Match comments
                (comment) @comment

                ; Match docstrings inside modules, functions, or classes
                (module (expression_statement (string)) @comment)
                (function_definition (block (expression_statement (string)) @comment))
                (class_definition (block (expression_statement (string)) @comment))
            """
CPP_QUERY = """(comment) @comment"""


def is_text_file(filepath: Path, sample_size: int = 2048) -> bool:
    """Return True if file is likely text, False if binary."""
    try:
        with filepath.open("rb") as f:
            chunk = f.read(sample_size)
        # Quick binary heuristic: null byte present
        if b"\x00" in chunk:
            return False
        # Try UTF-8 decode on the sample
        chunk.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def init_tree_sitter(comment_type: CommentType) -> tuple[Parser, Query]:
    if comment_type == CommentType.cpp:
        import tree_sitter_cpp  # noqa: PLC0415

        parsed_language = Language(tree_sitter_cpp.language())
        query = Query(parsed_language, CPP_QUERY)
    elif comment_type == CommentType.python:
        import tree_sitter_python  # noqa: PLC0415

        parsed_language = Language(tree_sitter_python.language())
        query = Query(parsed_language, PYTHON_QUERY)
    else:
        raise ValueError(f"Unsupported comment style: {comment_type}")
    parser = Parser(parsed_language)
    return parser, query


def wrap_read_callable_point(
    src_string: ByteString,
) -> Callable[[int, Point], ByteString]:
    def read_callable_byte_offset(byte_offset: int, _: Point) -> ByteString:
        return src_string[byte_offset : byte_offset + 1]

    return read_callable_byte_offset


def extract_comments(
    src_string: ByteString, parser: Parser, query: Query
) -> list[TreeSitterNode] | None:
    """Get all comments from source files by tree-sitter."""
    read_point_fn = wrap_read_callable_point(src_string)
    tree = parser.parse(read_point_fn)
    query_cursor = QueryCursor(query)
    captures: dict[str, list[TreeSitterNode]] = query_cursor.captures(tree.root_node)

    return captures.get("comment")


def find_enclosing_scope(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find the enclosing scope of a comment."""
    current: TreeSitterNode = node
    while current:
        if current.type in {"function_definition", "class_definition"}:
            return current
        current: TreeSitterNode | None = current.parent  # type: ignore[no-redef]  # required for node traversal
    return None


def find_next_scope(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find the next scope of a comment."""
    current: TreeSitterNode = node
    while current:
        if current.type in {"function_definition", "class_definition"}:
            return current
        current: TreeSitterNode | None = current.next_named_sibling  # type: ignore[no-redef]  # required for node traversal
        if current and current.type == "block":
            for child in current.named_children:
                if child.type in {"function_definition", "class_definition"}:
                    return child
    return None


def find_associated_scope(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find the associated scope of a comment."""
    if node.type == CommentCategory.docstring:
        # Only for python's docstring
        return find_enclosing_scope(node)
    # General comments regardless of comment types
    associated_scope = find_next_scope(node)
    if not associated_scope:
        associated_scope = find_enclosing_scope(node)
    return associated_scope


def locate_git_root(src_dir: Path) -> Path | None:
    """Traverse upwards to find git root."""
    current = src_dir.resolve()
    parents = list(current.parents)
    parents.append(current)
    for parent in parents:
        if (parent / ".git").exists() and (parent / ".git").is_dir():
            return parent
    logger.warning(f"git root is not found in the parent of {src_dir}")
    return None


def get_remote_url(git_root: Path, remote_name: str = "origin") -> str | None:
    """Get remote url from .git/config."""
    config_path = git_root / ".git" / "config"
    if not config_path.exists():
        logging.warning(f"{config_path} does not exist")
        return None

    config = configparser.ConfigParser(allow_no_value=True, strict=False)
    config.read(config_path)
    section = f'remote "{remote_name}"'
    if section in config and "url" in config[section]:
        url: str = config[section]["url"]
        return url
    logger.warning(f"remote-url is not found in {config_path}")
    return None


def get_current_rev(git_root: Path) -> str | None:
    """Get current commit rev from .git/HEAD."""
    head_path = git_root / ".git" / "HEAD"
    if not head_path.exists():
        logging.warning(f"{head_path} does not exist")
        return None
    head_content = head_path.read_text().strip()
    if not head_content.startswith("ref: "):
        logging.warning(f"Expect starting with 'ref: ' in {head_path}")
        return None

    ref_path = git_root / ".git" / head_content.split(":", 1)[1].strip()
    if not ref_path.exists():
        logging.warning(f"{ref_path} does not exist")
        return None
    return ref_path.read_text().strip()


def form_https_url(
    git_url: str, rev: str, project_path: Path, filepath: Path, lineno: int
) -> str | None:
    parsed_url = parse(git_url)
    template = GIT_HOST_URL_TEMPLATE.get(parsed_url.platform)
    if not template:
        logging.warning(f"Unsupported Git host: {parsed_url.platform}")
        return git_url
    https_url = template.format(
        owner=parsed_url.owner,
        repo=parsed_url.repo,
        rev=rev,
        path=pathname2url(str(filepath.absolute().relative_to(project_path))),
        lineno=str(lineno),
    )
    return https_url


def remove_leading_sequences(text: str, leading_sequences: list[str]) -> str:
    lines = text.splitlines(keepends=True)
    no_comment_lines = []
    for line in lines:
        leading_sequence_exist = False
        for leading_sequence in leading_sequences:
            leading_sequence_idx = line.find(leading_sequence)
            if leading_sequence_idx == -1:
                continue
            no_comment_lines.append(
                line[leading_sequence_idx + len(leading_sequence) :]
            )
            leading_sequence_exist = True
            break

        if not leading_sequence_exist:
            no_comment_lines.append(line)

    return "".join(no_comment_lines)


class ExtractedRstType(TypedDict):
    rst_text: str
    row_offset: int
    start_idx: int
    end_idx: int


def extract_rst(
    text: str, start_marker: str, end_marker: str
) -> ExtractedRstType | None:
    """Extract rst from a comment.

    Two use cases:
    1. Start_marker and end_marker one the same line.

    The rst text is wrapped by start and the end markers on the same line,
    so, there is no need to remove the leading chars.ArithmeticError
    E.g.
    @rst  .. admonition:: title here @endrst

    2. Start_marker and end_marker in different lines.

    The rst text is expected to start from the next line of the start_marker
    and ends at he previous line of the end_marker.
    E.g.
    @rst
    .. admonition:: title here
      :collapsible: open

      This example is collapsible, and initially open.
    @endrst
    """
    start_idx = text.find(start_marker)
    end_idx = text.rfind(end_marker)
    if start_idx == -1 or end_idx == -1:
        return None
    rst_text = text[start_idx + len(start_marker) : end_idx]
    row_offset = len(text[:start_idx].splitlines())
    if not rst_text.strip():
        # empty string is out of the interest
        return None
    if UNIX_NEWLINE not in rst_text:
        # single line rst text
        oneline_rst: ExtractedRstType = {
            "rst_text": rst_text,
            "row_offset": row_offset,
            "start_idx": start_idx + len(start_marker),
            "end_idx": end_idx,
        }
        return oneline_rst

    # multiline rst text

    first_newline_idx = rst_text.find(UNIX_NEWLINE)
    rst_text = rst_text[first_newline_idx + len(UNIX_NEWLINE) :]
    multiline_rst: ExtractedRstType = {
        "rst_text": rst_text,
        "row_offset": row_offset,
        "start_idx": start_idx
        + len(start_marker)
        + first_newline_idx
        + len(UNIX_NEWLINE),
        "end_idx": end_idx,
    }

    return multiline_rst
