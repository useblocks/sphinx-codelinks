from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node as TreeSitterNode


@dataclass
class SourceAnchor:
    filepath: Path
    remote_url: str | None
    lineno: int  # start from 1
    marker: str
    need_ids: list[str]


class SourceComment:
    def __init__(self, node: TreeSitterNode) -> None:
        self.node: TreeSitterNode = node
        self.marker = None
        self.source_file: SourceFile | None = None


class SourceFile:
    def __init__(self, filepath: Path) -> None:
        self.filepath: Path = filepath
        self.src_comments: list[SourceComment] = []

    def add_comment(self, comment: SourceComment) -> None:
        self.src_comments.append(comment)
        comment.source_file = self

    def add_comments(self, comments: list[SourceComment]) -> None:
        for comment in comments:
            self.add_comment(comment)
