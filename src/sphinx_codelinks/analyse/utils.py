from collections.abc import ByteString, Callable
import configparser
import logging
from pathlib import Path
import re
from typing import TypedDict
from urllib.request import pathname2url

from giturlparse import parse  # type: ignore[import-untyped]
from tree_sitter import Language, Parser, Point, Query, QueryCursor
from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.config import UNIX_NEWLINE, CommentCategory
from sphinx_codelinks.source_discover.config import CommentType

# Language-specific node types for scope detection
SCOPE_NODE_TYPES = {
    # @Python Scope Node Types, IMPL_PY_2, impl, [FE_PY]
    CommentType.python: {"function_definition", "class_definition"},
    # @C and C++ Scope Node Types, IMPL_C_2, impl, [FE_C_SUPPORT, FE_CPP]
    CommentType.cpp: {"function_definition", "class_definition"},
    CommentType.cs: {"method_declaration", "class_declaration", "property_declaration"},
    CommentType.yaml: {"block_mapping_pair", "block_sequence_item", "document"},
    # @Rust Scope Node Types, IMPL_RUST_2, impl, [FE_RUST];
    CommentType.rust: {
        "function_item",
        "struct_item",
        "enum_item",
        "impl_item",
        "trait_item",
        "mod_item",
    },
}

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
C_SHARP_QUERY = """(comment) @comment"""
YAML_QUERY = """(comment) @comment"""
RUST_QUERY = """
    (line_comment) @comment
    (block_comment) @comment
"""


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


# @Tree-sitter parser initialization for multiple languages, IMPL_LANG_1, impl, [FE_C_SUPPORT, FE_CPP, FE_PY, FE_YAML, FE_RUST]
def init_tree_sitter(comment_type: CommentType) -> tuple[Parser, Query]:
    if comment_type == CommentType.cpp:
        import tree_sitter_cpp  # noqa: PLC0415

        parsed_language = Language(tree_sitter_cpp.language())
        query = Query(parsed_language, CPP_QUERY)
    elif comment_type == CommentType.python:
        import tree_sitter_python  # noqa: PLC0415

        parsed_language = Language(tree_sitter_python.language())
        query = Query(parsed_language, PYTHON_QUERY)
    elif comment_type == CommentType.cs:
        import tree_sitter_c_sharp  # noqa: PLC0415

        parsed_language = Language(tree_sitter_c_sharp.language())
        query = Query(parsed_language, C_SHARP_QUERY)
    elif comment_type == CommentType.yaml:
        import tree_sitter_yaml  # noqa: PLC0415

        parsed_language = Language(tree_sitter_yaml.language())
        query = Query(parsed_language, YAML_QUERY)
    elif comment_type == CommentType.rust:
        import tree_sitter_rust  # noqa: PLC0415

        parsed_language = Language(tree_sitter_rust.language())
        query = Query(parsed_language, RUST_QUERY)
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


# @Comment extraction from source code using tree-sitter, IMPL_EXTR_1, impl, [FE_DEF]
def extract_comments(
    src_string: ByteString, parser: Parser, query: Query
) -> list[TreeSitterNode] | None:
    """Get all comments from source files by tree-sitter."""
    read_point_fn = wrap_read_callable_point(src_string)
    tree = parser.parse(read_point_fn)
    query_cursor = QueryCursor(query)
    captures: dict[str, list[TreeSitterNode]] = query_cursor.captures(tree.root_node)

    return captures.get("comment")


def find_enclosing_scope(
    node: TreeSitterNode, comment_type: CommentType = CommentType.cpp
) -> TreeSitterNode | None:
    """Find the enclosing scope of a comment."""
    scope_types = SCOPE_NODE_TYPES.get(comment_type, SCOPE_NODE_TYPES[CommentType.cpp])
    current: TreeSitterNode = node
    while current:
        if current.type in scope_types:
            return current
        current: TreeSitterNode | None = current.parent  # type: ignore[no-redef]  # required for node traversal
    return None


def find_next_scope(
    node: TreeSitterNode, comment_type: CommentType = CommentType.cpp
) -> TreeSitterNode | None:
    """Find the next scope of a comment."""
    scope_types = SCOPE_NODE_TYPES.get(comment_type, SCOPE_NODE_TYPES[CommentType.cpp])
    current: TreeSitterNode = node
    while current:
        if current.type in scope_types:
            return current
        current: TreeSitterNode | None = current.next_named_sibling  # type: ignore[no-redef]  # required for node traversal
        if current and current.type == "block":
            for child in current.named_children:
                if child.type in scope_types:
                    return child
    return None


def _find_yaml_structure_in_block_node(
    block_node: TreeSitterNode,
) -> TreeSitterNode | None:
    """Find YAML structure elements within a block_node."""
    for grandchild in block_node.named_children:
        if grandchild.type == "block_mapping":
            for ggchild in grandchild.named_children:
                if ggchild.type == "block_mapping_pair":
                    return ggchild
        elif grandchild.type == "block_sequence":
            for ggchild in grandchild.named_children:
                if ggchild.type == "block_sequence_item":
                    return ggchild
    return None


def find_yaml_next_structure(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find the next YAML structure element after the comment node."""
    current = node.next_named_sibling
    while current:
        if current.type in {
            "block_mapping_pair",
            "block_sequence_item",
            "flow_mapping",
            "flow_sequence",
        }:
            return current
        if current.type == "document":
            for child in current.named_children:
                if child.type == "block_node":
                    result = _find_yaml_structure_in_block_node(child)
                    if result:
                        return result
        if current.type == "block_node":
            result = _find_yaml_structure_in_block_node(current)
            if result:
                return result
        current = current.next_named_sibling
    return None


def find_yaml_prev_sibling_on_same_row(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find a previous named sibling that is on the same row as the comment."""
    comment_row = node.start_point.row
    current = node.prev_named_sibling

    while current:
        # Check if this sibling ends on the same row as the comment starts
        # This indicates it's an inline comment
        if current.end_point.row == comment_row:
            return current
        # If we find a sibling that ends before the comment row, we can stop
        # as we won't find any siblings on the same row going backwards
        if current.end_point.row < comment_row:
            break
        current = current.prev_named_sibling

    return None


def find_yaml_associated_structure(node: TreeSitterNode) -> TreeSitterNode | None:
    """Find the YAML structure (key-value pair, list item, etc.) associated with a comment."""
    # First, check if this is an inline comment by looking for a previous sibling on the same row
    prev_sibling_same_row = find_yaml_prev_sibling_on_same_row(node)
    if prev_sibling_same_row:
        return prev_sibling_same_row

    # If no previous sibling on same row, try to find the next named sibling (structure after the comment)
    structure = find_yaml_next_structure(node)
    if structure:
        return structure

    # If no next sibling found, traverse up to find parent structure
    parent = node.parent
    while parent:
        if parent.type in {"block_mapping_pair", "block_sequence_item"}:
            return parent
        parent = parent.parent

    return None


def find_associated_scope(
    node: TreeSitterNode, comment_type: CommentType = CommentType.cpp
) -> TreeSitterNode | None:
    """Find the associated scope of a comment."""
    if comment_type == CommentType.yaml:
        # YAML uses different structure association logic
        return find_yaml_associated_structure(node)

    if node.type == CommentCategory.docstring:
        # Only for python's docstring
        return find_enclosing_scope(node, comment_type)
    # General comments regardless of comment types
    associated_scope = find_next_scope(node, comment_type)
    if not associated_scope:
        associated_scope = find_enclosing_scope(node, comment_type)
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


class ParsedDirective(TypedDict):
    """A single parsed RST directive."""

    name: str
    argument: str
    options: dict[str, str]
    content: str
    has_extra_content: bool
    directive_line_offset: int
    """0-based line index of the ``.. name::`` line within the input text."""
    content_line_offset: int | None
    """0-based line index where the directive content starts within the input text.

    ``None`` if the directive has no content body.
    """


_RE_DIRECTIVE = re.compile(r"^(\s*)\.\.\s+([\w:.+-]+)\s*::\s*(.*)")
_RE_OPTION = re.compile(r"^\s+:([^:]+):\s*(.*)")


def _parse_options(body_lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse field-list options from the start of directive body lines.

    Supports multi-line option values: continuation lines must be indented
    and are joined with a single space.

    :return: Tuple of (options dict, content_start index into body_lines).
    """
    options: dict[str, str] = {}
    content_start = 0
    current_key: str | None = None
    for j, line in enumerate(body_lines):
        if not line.strip():
            # Blank line ends the option block.
            content_start = j + 1
            current_key = None
            break
        opt_match = _RE_OPTION.match(line)
        if opt_match:
            current_key = opt_match.group(1).strip()
            options[current_key] = opt_match.group(2).strip()
            content_start = j + 1
        elif current_key is not None and line[:1] == " ":
            # Continuation line for the previous option value.
            # NOTE: In standard RST (docutils),
            # continuation indent is measured relative to the field body
            # start.  Here any leading space is accepted, which is looser
            # but correct within a directive body where all lines are
            # already indented past the directive marker.
            prev = options[current_key]
            continuation = line.strip()
            options[current_key] = f"{prev} {continuation}" if prev else continuation
            content_start = j + 1
        else:
            content_start = j
            break
    else:
        content_start = len(body_lines)
    return options, content_start


def _extract_content(
    body_lines: list[str], content_start: int
) -> tuple[list[str], int]:
    """Extract and dedent the content portion of a directive body.

    :return: Tuple of (dedented content lines, number of leading blank lines removed).
    """
    content_lines = body_lines[content_start:]
    content_blanks_removed = 0
    while content_lines and not content_lines[0].strip():
        content_lines.pop(0)
        content_blanks_removed += 1
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()
    if content_lines:
        min_indent = min(
            len(cl) - len(cl.lstrip()) for cl in content_lines if cl.strip()
        )
        content_lines = [cl[min_indent:] if cl.strip() else "" for cl in content_lines]
    return content_lines, content_blanks_removed


def parse_single_directive(rst_text: str) -> ParsedDirective | None:
    """Parse a single RST directive from text.

    Expects text whose first non-blank line is a directive, e.g.::

        .. need-type:: argument
           :option: value

           Content body here.

    :param rst_text: The RST text to parse.
    :return: Parsed directive, or ``None`` if the first non-blank line
        is not a directive.
    """
    lines = rst_text.splitlines()

    # Find directive on the first non-blank line
    dir_idx: int | None = None
    dir_match: re.Match[str] | None = None
    for i, line in enumerate(lines):
        if line.strip():
            dir_match = _RE_DIRECTIVE.match(line)
            if dir_match:
                dir_idx = i
            break

    if dir_idx is None or dir_match is None:
        return None

    dir_indent = len(dir_match.group(1))
    name = dir_match.group(2)
    # NOTE: In standard RST (docutils), directive
    # arguments may span multiple lines before the first field-list
    # marker.  Here only the ``.. name::`` line is captured; this is
    # sufficient for NeedDirective where the argument is a single-line
    # title.
    argument = dir_match.group(3).strip()

    # Collect body: indented (or blank) lines after the directive.
    # body_end tracks the last non-blank indented line so trailing
    # blank lines between the directive and outside content are excluded.
    body_end = dir_idx
    for i in range(dir_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) > dir_indent:
            body_end = i
        else:
            break

    body_lines = lines[dir_idx + 1 : body_end + 1]

    options, content_start = _parse_options(body_lines)
    content_lines, content_blanks_removed = _extract_content(body_lines, content_start)
    content = "\n".join(content_lines)

    # Extra content = any non-blank line outside the directive body.
    has_extra = any(lines[i].strip() for i in range(body_end + 1, len(lines)))

    # Line offsets relative to the start of rst_text (0-based).
    directive_line_offset = dir_idx
    if content_lines:
        content_line_offset: int | None = (
            dir_idx + 1 + content_start + content_blanks_removed
        )
    else:
        content_line_offset = None

    return ParsedDirective(
        name=name,
        argument=argument,
        options=options,
        content=content,
        has_extra_content=has_extra,
        directive_line_offset=directive_line_offset,
        content_line_offset=content_line_offset,
    )


# @Extract reStructuredText blocks embedded in comments, IMPL_RST_1, impl, [FE_RST_EXTRACTION]
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
