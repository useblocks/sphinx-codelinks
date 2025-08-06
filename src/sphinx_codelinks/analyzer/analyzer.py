from collections.abc import Generator
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any

from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.analyzer import utils
from sphinx_codelinks.analyzer.config import (
    COMMENT_FILETYPE,
    CommentType,
    OneLineCommentStyle,
)
from sphinx_codelinks.analyzer.models import (
    SourceAnchor,
    SourceComment,
    SourceFile,
    SourceMap,
)
from sphinx_codelinks.source_discovery.source_discover import SourceDiscover

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


@dataclass
class AnalyzerWarning:
    file_path: str
    lineno: int
    msg: str
    type: str
    sub_type: str


class SourceAnalyzer:
    warning_filepath: Path = Path("cached_warnings") / "codelinks_warnings.json"

    def __init__(
        self,
        src_dir: Path,
        markers: list[str] | None = None,
        comment_type: CommentType = CommentType.cpp,
        outdir: Path | None = None,
        oneline_comment_style: OneLineCommentStyle | None = None,
    ) -> None:
        self.src_dir = src_dir
        self.markers = markers if markers else ["@"]
        self.comment_type = comment_type
        self.outdir = outdir if outdir else src_dir

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
        self.oneline_comment_style = oneline_comment_style
        self.oneline_warnings: list[AnalyzerWarning] = []
        self.warnings_path = self.outdir / SourceAnalyzer.warning_filepath

    def get_src_strings(self) -> Generator[tuple[Path, bytes], Any, None]:  # type: ignore[explicit-any]
        """Load source files and extract their content."""
        src_discovery = SourceDiscover(
            self.src_dir,
            file_types=COMMENT_FILETYPE[self.comment_type],
            gitignore=False,
        )
        for src_path in src_discovery.source_paths:
            with src_path.open("r") as f:
                yield src_path, f.read().encode("utf8")

    def create_src_objects(self) -> None:
        parser, query = utils.init_tree_sitter(self.comment_type)

        for src_path, src_string in self.get_src_strings():
            comments: list[TreeSitterNode] = utils.extract_comments(
                src_string, parser, query
            )
            src_comments: list[SourceComment] = [
                SourceComment(node) for node in comments
            ]
            project_path: Path = self.git_root if self.git_root else self.src_dir
            src_file = SourceFile(src_path.relative_to(project_path))
            src_file.add_comments(src_comments)
            self.src_files.append(src_file)
            self.src_comments.extend(src_comments)

        logger.info(f"Source files loaded: {len(self.src_files)}")
        logger.info(f"Source comments extracted: {len(self.src_comments)}")

    def extract_marker(
        self,
        text: str,
    ) -> Generator[tuple[str, list[str], int, int, int], None, None]:
        lines = text.splitlines()
        row_offset = 0
        for line in lines:
            for marker in self.markers:
                marker_idx = line.find(marker)
                if marker_idx == -1:
                    continue
                markered_text = line[marker_idx + len(marker) :].strip()
                need_ids = markered_text.replace(",", " ").split()
                start_column = marker_idx + len(marker)
                end_column = start_column + len(markered_text)
                yield marker, need_ids, row_offset, start_column, end_column
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

            if src_comment.node.parent:
                tagged_scope: TreeSitterNode | None = utils.find_enclosing_scope(
                    src_comment.node, self.comment_type
                )
            else:
                tagged_scope: TreeSitterNode | None = utils.find_next_scope(
                    src_comment.node, self.comment_type
                )

            for (
                marker,
                need_ids,
                row_offset,
                start_column,
                end_column,
            ) in self.extract_marker(text):
                lineno = src_comment.node.start_point.row + row_offset + 1
                remote_url = self.git_remote_url
                if self.git_remote_url and self.git_commit_rev:
                    remote_url = utils.form_https_url(
                        self.git_remote_url,
                        self.git_commit_rev,
                        filepath,
                        lineno,
                    )
                source_map: SourceMap = {
                    "start": {
                        "row": lineno - 1,
                        "column": start_column,
                    },
                    "end": {
                        "row": lineno - 1,
                        "column": end_column,
                    },
                }
                self.anchors.append(
                    SourceAnchor(
                        filepath,
                        remote_url,
                        source_map,
                        marker,
                        src_comment,
                        tagged_scope,
                        need_ids,
                    )
                )

        logger.info(f"Source anchors extracted: {len(self.anchors)}")

    def dump_anchors(self) -> None:
        output_path = self.outdir / "anchors.json"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        anchors = [anchor.to_dict() for anchor in self.anchors]
        with output_path.open("w") as f:
            json.dump(anchors, f)
        logger.info(f"Source anchors dumped to {output_path}")

    def run(self) -> None:
        self.create_src_objects()
        self.extract_markers()
        self.dump_anchors()
