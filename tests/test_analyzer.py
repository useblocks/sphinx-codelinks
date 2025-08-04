import json
from pathlib import Path
import shutil
import subprocess

import pytest
from tree_sitter import Node as TreeSitterNode

from sphinx_codelinks.analyzer.analyzer import SourceAnalyzer
from sphinx_codelinks.analyzer.utils import (
    form_https_url,
    get_current_rev,
    get_remote_url,
    locate_git_root,
)


@pytest.mark.parametrize(
    ("code", "result"),
    [
        (
            """
                # @req-id: need_001
                def dummy_func1():
                    pass
            """,
            "# @req-id: need_001",
        ),
        (
            """
                def dummy_func1():
                    # @req-id: need_001
                    pass
            """,
            "# @req-id: need_001",
        ),
        (
            """
                def dummy_func1():
                    '''
                    @req-id: need_001
                    '''
                    pass
            """,
            "'''\n                    @req-id: need_001\n                    '''",
        ),
        (
            """
                def dummy_func1():
                    text = '''@req-id: need_001, need_002, this docstring shall not be extracted as comment'''
                    # @req-id: need_001
                    pass
            """,
            "# @req-id: need_001",
        ),
    ],
)
def test_python_comment(code, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"], "python")
    comments: list[TreeSitterNode] = anaylzer.extract_comments(code.encode("utf-8"))
    assert len(comments) == 1
    assert comments[0].text
    assert comments[0].text.decode("utf-8") == result


@pytest.mark.parametrize(
    ("code", "result"),
    [
        (
            """
                // @req-id: need_001
                void dummy_func1(){
                }
            """,
            "// @req-id: need_001",
        ),
        (
            """
                void dummy_func1(){
                // @req-id: need_001
                }
            """,
            "// @req-id: need_001",
        ),
        (
            """
                /* @req-id: need_001 */
                void dummy_func1(){
                }
            """,
            "/* @req-id: need_001 */",
        ),
    ],
)
def test_cpp_comment(code, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"], "cpp")
    comments: list[TreeSitterNode] = anaylzer.extract_comments(code.encode("utf-8"))
    assert len(comments) == 1
    assert comments[0].text
    assert comments[0].text.decode("utf-8") == result


@pytest.mark.parametrize(
    ("comment", "result"),
    [
        ("""// @req-id: need_001""", [("@req-id:", ["need_001"], 0)]),
        (
            """// @req-id: need_001 need_002""",
            [("@req-id:", ["need_001", "need_002"], 0)],
        ),
        (
            """/*
            * @req-id: need_001 need_002
            */""",
            [("@req-id:", ["need_001", "need_002"], 1)],
        ),
        (
            """/*
            * @req-id: need_001 need_002
            * @req-id: need_003
            */""",
            [("@req-id:", ["need_001", "need_002"], 1), ("@req-id:", ["need_003"], 2)],
        ),
    ],
)
def test_extract_marker(comment, result, tmp_path):
    anaylzer = SourceAnalyzer(Path(tmp_path), ["@req-id:"])
    for i, (marker, need_ids, row_offset) in enumerate(
        anaylzer.extract_marker(comment)
    ):
        assert (marker, need_ids, row_offset) == result[i]


@pytest.mark.parametrize(
    ("git_url", "rev", "filepath", "lineno", "result"),
    [
        (
            "git@github.com:useblocks/sphinx-codelinks.git",
            "beef1234",
            Path("example") / "to" / "here",
            3,
            "https://github.com/useblocks/sphinx-codelinks/blob/beef1234/example/to/here#L3",
        )
    ],
)
def test_form_https_url(git_url, rev, filepath, lineno, result):
    url = form_https_url(git_url, rev, filepath, lineno=lineno)
    assert url == result


def get_git_path() -> str:
    """Get the path to the git executable."""
    git_path = shutil.which("git")
    if not git_path:
        raise FileNotFoundError("Git executable not found")
    if not Path(git_path).is_file():
        raise FileNotFoundError("Git executable path is invalid")
    return git_path


def init_git_repo(repo_path: Path, remote_url: str) -> Path:
    """Initialize a git repository for testing."""
    git_dir = repo_path / "test_repo"
    src_dir = git_dir / "src"
    src_dir.mkdir(parents=True)

    git_path = get_git_path()
    if not git_path:
        raise FileNotFoundError("Git executable not found")
    if not Path(git_path).is_file():
        raise FileNotFoundError("Git executable path is invalid")

    # Initialize git repo
    subprocess.run([git_path, "init"], cwd=git_dir, check=True, capture_output=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_path, "config", "user.email", "test@example.com"], cwd=git_dir, check=True
    )
    subprocess.run(  # noqa: S603
        [git_path, "config", "user.name", "Test User"], cwd=git_dir, check=True
    )

    # Create a test file and commit
    test_file = src_dir / "test_file.py"
    test_file.write_text("# Test file\nprint('hello')\n")
    subprocess.run([git_path, "add", "."], cwd=git_dir, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [git_path, "commit", "-m", "Initial commit"], cwd=git_dir, check=True
    )

    # Add a remote
    subprocess.run(  # noqa: S603
        [git_path, "remote", "add", "origin", remote_url],
        cwd=git_dir,
        check=True,
    )

    return git_dir


@pytest.fixture(
    params=[
        ("test_repo_git", "git@github.com:test-user/test-repo.git"),
        ("test_repo_https", "https://github.com/test-user/test-repo.git"),
    ]
)
def git_repo(tmp_path: str, request: pytest.FixtureRequest) -> tuple[Path, str]:
    """Create git repos for testing."""
    repo_name, remote_url = request.param
    repo_path = Path(tmp_path) / repo_name
    repo_path = init_git_repo(repo_path, remote_url)
    return repo_path, remote_url


def get_current_commit_hash(git_dir: Path) -> str:
    """Get the current commit hash of the git repository."""
    git_path = get_git_path()
    result = subprocess.run(  # noqa: S603
        [git_path, "rev-parse", "HEAD"],
        cwd=git_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    return str(result.stdout.strip())


def test_locate_git_root(git_repo: tuple[Path, str]) -> None:
    repo_path = git_repo[0]
    src_dir = repo_path / "src"
    git_root = locate_git_root(src_dir)
    assert git_root == repo_path


def test_get_remote_url(git_repo: tuple[Path, str]) -> None:
    repo_path, expected_url = git_repo
    remote_url = get_remote_url(repo_path)
    assert remote_url == expected_url


def test_get_current_rev(git_repo: tuple[Path, str]) -> None:
    repo_path, _ = git_repo
    current_rev = get_current_commit_hash(repo_path)
    assert current_rev == get_current_rev(repo_path)


def test_analyzer(tmp_path, snapshot_anchors):
    src_dir = Path(__file__).parent.parent / "tests" / "data" / "anchors"
    anaylzer = SourceAnalyzer(src_dir, ["@req-id:"], outdir=tmp_path)
    anaylzer.git_remote_url = None
    anaylzer.git_commit_rev = None
    anaylzer.run()

    dumped_anchors = tmp_path / "anchors.json"
    with dumped_anchors.open("r") as f:
        anchors = json.load(f)
    # normalize filepath
    for anchor in anchors:
        anchor["filepath"] = Path(anchor["filepath"]).as_posix()
    assert anchors == snapshot_anchors
