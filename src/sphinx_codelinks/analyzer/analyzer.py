from collections.abc import Generator
from dataclasses import dataclass
import json
import logging
import os
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
    MarkedContentType,
    MarkedRst,
    NeedIdRefs,
    OneLineNeed,
    SourceComment,
    SourceFile,
    SourceMap,
)
from sphinx_codelinks.analyzer.oneline_parser import (
    OnelineParserInvalidWarning,
    oneline_parser,
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

    def __init__(  # noqa: PLR0913
        self,
        src_dir: Path,
        comment_type: CommentType = CommentType.cpp,
        outdir: Path | None = None,
        get_need_id_refs: bool = True,
        get_oneline_needs: bool = False,
        get_rst: bool = False,
        markers: list[str] | None = None,
        oneline_comment_style: OneLineCommentStyle | None = None,
    ) -> None:
        self.src_dir = src_dir
        self.markers = markers if markers else ["@"]
        self.comment_type = comment_type
        self.outdir = outdir if outdir else src_dir
        self.get_need_id_refs = get_need_id_refs
        self.get_oneline_needs = get_oneline_needs
        self.get_rst = get_rst
        self.src_files: list[SourceFile] = []
        self.src_comments: list[SourceComment] = []
        self.need_id_refs: list[NeedIdRefs] = []
        self.oneline_needs: list[OneLineNeed] = []
        self.marked_rst: list[MarkedRst] = []
        self.all_marked_content: list[NeedIdRefs | OneLineNeed | MarkedRst] = []
        self.git_root: Path | None = utils.locate_git_root(src_dir)
        self.git_remote_url: str | None = (
            utils.get_remote_url(self.git_root) if self.git_root else None
        )
        self.git_commit_rev: str | None = (
            utils.get_current_rev(self.git_root) if self.git_root else None
        )
        self.oneline_comment_style = (
            oneline_comment_style if oneline_comment_style else OneLineCommentStyle()
        )
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

    def extract_anchors(
        self,
        text: str,
        filepath: Path,
        tagged_scope: TreeSitterNode | None,
        src_comment: SourceComment,
    ) -> list[NeedIdRefs]:
        """Extract need-ids-refs from a comment."""
        anchors: list[NeedIdRefs] = []
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
            anchors.append(
                NeedIdRefs(
                    filepath,
                    remote_url,
                    source_map,
                    src_comment,
                    tagged_scope,
                    need_ids,
                    marker,
                )
            )
        return anchors

    def extract_oneline_need(
        self,
        text: str,
        src_comment: SourceComment,
        oneline_comment_style: OneLineCommentStyle,
    ) -> Generator[tuple[dict[str, str | list[str] | int], int]]:
        lines = text.splitlines(keepends=True)
        row_offset = 0
        if len(lines) == 1:
            # single line comment has no newline char in the extracted comment
            lines[0] = f"{lines[0]}{os.linesep}"

        for line in lines:
            resolved = oneline_parser(line, oneline_comment_style)
            if not resolved:
                continue
            if isinstance(resolved, OnelineParserInvalidWarning):
                if not src_comment.source_file:
                    continue
                self.oneline_warnings.append(
                    AnalyzerWarning(
                        str(src_comment.source_file.filepath),
                        src_comment.node.start_point.row + row_offset + 1,
                        resolved.msg,
                        MarkedContentType.need,
                        resolved.sub_type.value,
                    )
                )
                continue
            yield resolved, row_offset
            row_offset += 1

    def extract_oneline_needs(
        self,
        text: str,
        filepath: Path,
        tagged_scope: TreeSitterNode | None,
        src_comment: SourceComment,
        oneline_comment_style: OneLineCommentStyle,
    ) -> list[OneLineNeed]:
        row_offset = 0
        oneline_needs = []
        for resolved, row_offset in self.extract_oneline_need(
            text, src_comment, oneline_comment_style
        ):
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
                    "column": resolved["start_column"],  # type: ignore[typeddict-item]  # dynamic keys
                },
                "end": {
                    "row": lineno - 1,
                    "column": resolved["end_column"],  # type: ignore[typeddict-item]  # dynamic keys
                },
            }
            del resolved["start_column"]
            del resolved["end_column"]
            oneline_needs.append(
                OneLineNeed(
                    filepath,
                    remote_url,
                    source_map,
                    src_comment,
                    tagged_scope,
                    resolved,  # type: ignore[arg-type] # int arguments were deleted
                )
            )
        return oneline_needs

    def extract_marked_rst(
        self,
        text: str,
        filepath: Path,
        tagged_scope: TreeSitterNode | None,
        src_comment: SourceComment,
    ) -> MarkedRst | None:
        """Extract marked rst from a comment.

        Presumably, only one marked rst text in a comment.
        """
        extracted_rst = utils.extract_rst(text, "@rst", "@endrst")
        if not extracted_rst:
            return None
        if os.linesep in extracted_rst["rst_text"]:
            rst_text = utils.remove_leading_sequences(extracted_rst["rst_text"], ["*"])
        else:
            rst_text = extracted_rst["rst_text"]
        lineno = src_comment.node.start_point.row + extracted_rst["row_offset"] + 1
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
                "column": extracted_rst["start_idx"],
            },
            "end": {
                "row": lineno - 1,
                "column": extracted_rst["end_idx"],
            },
        }
        return MarkedRst(
            filepath,
            remote_url,
            source_map,
            src_comment,
            tagged_scope,
            rst_text,
        )

    def extract_marked_content(self) -> None:
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
            tagged_scope: TreeSitterNode | None = utils.find_associated_scope(
                src_comment.node
            )
            if self.get_need_id_refs:
                anchors = self.extract_anchors(
                    text, filepath, tagged_scope, src_comment
                )
                self.need_id_refs.extend(anchors)

            if self.get_oneline_needs:
                oneline_needs = self.extract_oneline_needs(
                    text,
                    filepath,
                    tagged_scope,
                    src_comment,
                    self.oneline_comment_style,
                )
                self.oneline_needs.extend(oneline_needs)
            if self.get_rst:
                marked_rst = self.extract_marked_rst(
                    text, filepath, tagged_scope, src_comment
                )
                if marked_rst:
                    self.marked_rst.append(marked_rst)

        if self.get_need_id_refs:
            logger.info(f"Need-id-refs extracted: {len(self.need_id_refs)}")
        if self.get_oneline_needs:
            logger.info(f"Oneline needs extracted: {len(self.oneline_needs)}")
        if self.get_rst:
            logger.info(f"Marked rst extracted: {len(self.marked_rst)}")

    def merge_marked_content(self) -> None:
        self.all_marked_content.extend(self.need_id_refs)
        self.all_marked_content.extend(self.oneline_needs)
        self.all_marked_content.extend(self.marked_rst)
        self.all_marked_content.sort(
            key=lambda x: (x.filepath, x.source_map["start"]["row"])
        )

    def dump_marked_content(self) -> None:
        output_path = self.outdir / "marked_content.json"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        to_dump = [
            marked_content.to_dict() for marked_content in self.all_marked_content
        ]
        with output_path.open("w") as f:
            json.dump(to_dump, f)
        logger.info(f"Marked content dumped to {output_path}")

    def run(self) -> None:
        self.create_src_objects()
        self.extract_marked_content()
        self.merge_marked_content()
        self.dump_marked_content()
