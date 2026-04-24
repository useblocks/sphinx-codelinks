import os
from pathlib import Path

from ignore import WalkBuilder
from ignore.overrides import OverrideBuilder

from sphinx_codelinks.source_discover.config import (
    COMMENT_FILETYPE,
    SourceDiscoverConfig,
)


# @Source code file discovery with gitignore support, IMPL_DISC_1, impl, [FE_DISCOVERY, FE_CLI_DISCOVER]
class SourceDiscover:
    def __init__(self, src_discover_config: SourceDiscoverConfig):
        self.src_discover_config = src_discover_config
        # normalize the file types to lower case with leading dot
        self.file_types = {
            f".{ext}" for ext in COMMENT_FILETYPE[src_discover_config.comment_type]
        }

        self.source_paths = self._discover()

    def _build_overrides(self) -> OverrideBuilder | None:
        """Build an OverrideBuilder for include/exclude patterns.

        Include patterns are added as whitelist globs.
        Exclude patterns are added as negated globs (prefixed with ``!``).
        """
        src_dir = str(self.src_discover_config.src_dir)
        has_include = bool(self.src_discover_config.include)
        has_exclude = bool(self.src_discover_config.exclude)

        if not has_include and not has_exclude:
            return None

        ob = OverrideBuilder(src_dir)

        if has_include:
            for pattern in self.src_discover_config.include:
                ob.add(pattern)

        if has_exclude:
            for pattern in self.src_discover_config.exclude:
                ob.add(f"!{pattern}")

        return ob

    def _discover(self) -> list[Path]:
        """Discover source files recursively in the given directory."""
        src_dir = self.src_discover_config.src_dir
        if not src_dir.is_dir():
            return []

        builder = WalkBuilder(str(src_dir))
        builder.hidden(False)
        builder.git_ignore(self.src_discover_config.gitignore)
        builder.git_global(False)
        builder.git_exclude(False)
        builder.follow_links(self.src_discover_config.follow_links)

        override_builder = self._build_overrides()
        if override_builder is not None:
            builder.overrides(override_builder.build())

        discovered_files = []
        for entry in builder.build():
            filepath = entry.path()
            if not filepath.is_file():
                continue
            if self.file_types and filepath.suffix.lower() not in self.file_types:
                continue
            discovered_files.append(filepath.resolve())

        sorted_filepaths = sorted(
            discovered_files, key=lambda x: os.path.normcase(os.path.normpath(x))
        )
        return sorted_filepaths
