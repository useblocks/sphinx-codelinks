from collections.abc import ByteString, Generator
import json
import logging
from pathlib import Path
from typing import Any, Literal, TypedDict

from tree_sitter import Language, Parser, Query, QueryCursor
from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.analyzer import utils
from sphinx_codelinks.analyzer.models import SourceAnchor, SourceComment, SourceFile
from sphinx_codelinks.source_discovery.source_discover import SourceDiscover

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


class SourceAnalyzerConfig(TypedDict, total=False):
    src_dir: Path
    markers: list[str]


LANGUAGE_FILETYPE = {"cpp": ["c", "cpp", "h", "hpp"], "python": ["py"]}


class SourceAnalyzer:
    def __init__(
        self,
        src_dir: Path,
        markers: list[str] | None = None,
        language: Literal["python", "cpp"] = "cpp",
        outdir: Path | None = None,
    ) -> None:
        self.src_dir = src_dir
        self.markers = markers if markers else ["@"]
        self.language = language
        self.outdir = outdir if outdir else src_dir

        # init tree-sitter

        if language == "cpp":
            import tree_sitter_cpp  # noqa: PLC0415

            parsed_language = Language(tree_sitter_cpp.language())
            query = """(comment) @comment"""
        elif language == "python":
            import tree_sitter_python  # noqa: PLC0415

            parsed_language = Language(tree_sitter_python.language())
            query = """
                ; Match comments
                (comment) @comment

                ; Match docstrings inside modules, functions, or classes
                (module (expression_statement (string)) @comment)
                (function_definition (block (expression_statement (string)) @comment))
                (class_definition (block (expression_statement (string)) @comment))
            """
        else:
            raise ValueError(f"Unsupported language: {language}")
        self.parser = Parser(parsed_language)
        self.query = Query(parsed_language, query)

        self.src_files: list[SourceFile] = []
        self.src_comments: list[SourceComment] = []
        self.anchors: list[SourceAnchor] = []  # a flat view of each link
        self.git_root: Path | None = utils.locate_git_root(src_dir)
        self.git_remote_url: str | None = (
            utils.get_remote_url(self.git_root) if self.git_root else None
        )
        self.git_commit_rev: str | None = (
            utils.get_current_rev(self.git_root) if self.git_root else None
        )

    def get_src_strings(self) -> Generator[tuple[Path, bytes], Any, None]:  # type: ignore[explicit-any]
        """Load source files and extract their content."""
        src_discovery = SourceDiscover(
            self.src_dir, file_types=LANGUAGE_FILETYPE[self.language], gitignore=False
        )
        for src_path in src_discovery.source_paths:
            with src_path.open("r") as f:
                yield src_path, f.read().encode("utf8")

    def extract_comments(self, src_string: ByteString) -> list[TreeSitterNode]:
        """Get all comments from source files by tree-sitter."""
        read_point_fn = utils.wrap_read_callable_point(src_string)
        tree = self.parser.parse(read_point_fn)
        query_cursor = QueryCursor(self.query)
        captures: dict[str, list[TreeSitterNode]] = query_cursor.captures(
            tree.root_node
        )
        return captures["comment"]

    def create_src_objects(self) -> None:
        for src_path, src_string in self.get_src_strings():
            comments: list[TreeSitterNode] = self.extract_comments(src_string)
            src_comments: list[SourceComment] = [
                SourceComment(node) for node in comments
            ]
            project_path: Path = self.git_root if self.git_root else self.src_dir
            src_file = SourceFile(src_path.relative_to(project_path))
            src_file.add_comments(src_comments)
            self.src_files.append(src_file)
            self.src_comments.extend(src_comments)

    def extract_marker(
        self,
        text: str,
    ) -> Generator[tuple[str, list[str], int], None, None]:
        lines = text.splitlines()
        row_offset = 0
        for line in lines:
            for marker in self.markers:
                marker_idx = line.find(marker)
                if marker_idx == -1:
                    continue
                markered_text = line[marker_idx + len(marker) :].strip()
                need_ids = markered_text.replace(",", " ").split()
                yield marker, need_ids, row_offset
            row_offset += 1

    def extract_markers(self) -> None:
        for src_comment in self.src_comments:
            text = (
                src_comment.node.text.decode("utf-8") if src_comment.node.text else None
            )
            if not text:
                continue
            filepath = (
                src_comment.source_file.filepath if src_comment.source_file else None
            )
            if not filepath:
                continue

            for marker, need_ids, row_offset in self.extract_marker(text):
                lineno = src_comment.node.start_point.row + row_offset + 1
                remote_url = self.git_remote_url
                if self.git_remote_url and self.git_commit_rev:
                    remote_url = utils.form_https_url(
                        self.git_remote_url,
                        self.git_commit_rev,
                        filepath,
                        lineno,
                    )
                self.anchors.append(
                    SourceAnchor(
                        filepath,
                        remote_url,
                        lineno,
                        marker,
                        need_ids,
                    )
                )

    def dump_anchors(self) -> None:
        output_path = self.outdir / "anchors.json"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        anchors = [anchor.to_dict() for anchor in self.anchors]
        with output_path.open("w") as f:
            json.dump(anchors, f)

    def run(self) -> None:
        self.create_src_objects()
        self.extract_markers()
        self.dump_anchors()
