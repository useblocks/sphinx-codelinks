from collections.abc import ByteString
import logging
from pathlib import Path

from tree_sitter import Language, Parser, Query, QueryCursor
from tree_sitter import Node as TreeSitterNode
import tree_sitter_cpp

from sphinx_codelinks.analyzer import utils
from sphinx_codelinks.analyzer.models import SourceComment, SourceFile
from sphinx_codelinks.source_discovery.source_discover import SourceDiscover

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)
CPP_LANGUAGE = Language(tree_sitter_cpp.language())


class SourceAnalyzer:
    def __init__(self, src_dir: Path, marker: str = "@"):
        self.src_dir = src_dir
        self.marker = marker
        self.src_files: list[SourceFile] = []
        self.git_root: Path | None = utils.locate_git_root(src_dir)
        self.git_remote_url: str | None = (
            utils.get_remote_url(self.git_root) if self.git_root else None
        )
        self.git_commit_rev: str | None = (
            utils.get_current_rev(self.git_root) if self.git_root else None
        )

    def extract_comments(self):
        """Get all comments from source files by tree-sitter."""
        # get source files
        src_discovery = SourceDiscover(
            self.src_dir, file_types=["cpp"], gitignore=False
        )

        # init tree-sitter
        parser = Parser(CPP_LANGUAGE)
        query = Query(CPP_LANGUAGE, """(comment) @comment""")

        for src_file in src_discovery.source_paths:
            with src_file.open("r") as f:
                src_string: ByteString = f.read().encode("utf8")
            read_point_fn = utils.wrap_read_callable_point(src_string)
            tree = parser.parse(read_point_fn)
            query_cursor = QueryCursor(query)
            captures: dict[str, list[TreeSitterNode]] = query_cursor.captures(
                tree.root_node
            )
            src_comments: list[SourceComment] = [
                SourceComment(node) for node in captures["comment"]
            ]
            self.src_files.append(
                SourceFile(src_file.relative_to(src_discovery.root_path), src_comments)
            )

    # TODO: find the locations of the string that meet the pattern
    # TODO: dump these locations into option specified in needextend
