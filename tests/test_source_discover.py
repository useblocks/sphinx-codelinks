from pathlib import Path

from sphinx_codelinks.source_discover import SourceDiscover


def test_source_discover_all_files(source_directory: Path):
    source_discover = SourceDiscover(source_directory, gitignore=False)
    assert len(source_discover.source_paths) == 5


def test_source_discover_gitignore(source_directory: Path):
    source_discover = SourceDiscover(source_directory, gitignore=True)
    assert len(source_discover.source_paths) == 4


def test_source_discover_includes(source_directory: Path):
    source_discover = SourceDiscover(
        source_directory,
        gitignore=True,
        excludes=["charge/*.cpp"],
        includes=["**/*.cpp"],
    )
    assert len(source_discover.source_paths) == 5


def test_source_discover_excludes(source_directory: Path):
    source_discover = SourceDiscover(
        source_directory, gitignore=True, excludes=["charge/*.cpp"]
    )
    assert len(source_discover.source_paths) == 3


def test_source_discover_type(source_directory: Path):
    source_discover = SourceDiscover(
        source_directory, gitignore=False, file_types=["cpp"]
    )
    assert len(source_discover.source_paths) == 4
    assert all(path.suffix == ".cpp" for path in source_discover.source_paths)
