from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node as TreeSitterNode


@dataclass
class SourceAnchor:
    filepath: Path
    lineno: int
    need_ids: list[str]


class SourceComment:
    def __init__(self, node: TreeSitterNode) -> None:
        self.node: TreeSitterNode = node
        self.marker = None


class SourceFile:
    def __init__(self, filepath: Path, src_comments: list[SourceComment]) -> None:
        self.filepath: Path = filepath
        self.src_comments: list[SourceComment] = src_comments
