from collections.abc import Callable
import json
from pathlib import Path

from _pytest.mark import ParameterSet
from docutils.nodes import document
import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
import yaml

from sphinx_codelinks.config import OneLineCommentStyle

pytest_plugins = "sphinx.testing.fixtures"

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"
SRC_TRACE_TOML = TEST_DIR / "data" / "sphinx" / "src_trace.toml"
RECURSIVE_DIR_analyse_TOML = TEST_DIR / "doc_test" / "recursive_dirs" / "src_trace.toml"
ONELINE_COMMENT_STYLE = OneLineCommentStyle(
    start_sequence="[[",
    end_sequence="]]",
    field_split_char=",",
    needs_fields=[
        {"name": "id"},
        {"name": "title"},
        {"name": "type", "default": "impl"},
        {"name": "links", "type": "list[str]", "default": []},
        {"name": "status", "default": "open"},
        {"name": "priority", "default": "low"},
    ],
)

ONELINE_COMMENT_STYLE_DEFAULT = OneLineCommentStyle()


@pytest.fixture(scope="session")
def source_directory() -> Path:
    tests_dir = Path(__file__).parent
    source_directory = tests_dir / "data" / "dcdc"
    return source_directory


@pytest.fixture(scope="session")
def source_paths(source_directory: Path) -> list[Path]:
    source_paths = [
        source_directory / "charge" / "demo_1.cpp",
        source_directory / "charge" / "demo_2.cpp",
        source_directory / "discharge" / "demo_3.cpp",
        source_directory / "supercharge.cpp",
    ]
    return source_paths


@pytest.fixture(scope="session", autouse=True)
def temporary_gitignore(source_directory: Path):
    gitignore_path = source_directory / ".gitignore"
    gitignore_path.write_text("demo_1.cpp\n", encoding="utf-8")
    yield
    gitignore_path.unlink()


class DoctreeSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "doctree.xml"

    def serialize(self, data, **_kwargs):
        if not isinstance(data, document):
            raise TypeError(f"Expected document, got {type(data)}")
        doc = data.deepcopy()
        doc["source"] = "<source>"  # this will be a temp path
        doc.attributes.pop("translation_progress", None)  # added in sphinx 7.1
        return doc.pformat()


@pytest.fixture
def snapshot_doctree(snapshot):
    """Snapshot fixture for doctrees.

    Here we try to sanitize the doctree, to make the snapshots reproducible.
    """
    try:
        return snapshot.with_defaults(extension_class=DoctreeSnapshotExtension)
    except AttributeError:
        # fallback for older versions of pytest-snapshot
        return snapshot.use_extension(DoctreeSnapshotExtension)


class AnchorsSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "anchors.json"

    def serialize(self, data, **_kwargs):
        if not isinstance(data, list):
            raise TypeError(f"Expected list, got {type(data)}")
        anchors = data

        return json.dumps(anchors, indent=2)


@pytest.fixture
def snapshot_marks(snapshot):
    """Snapshot fixture for markers.

    Sanitize the markers, to make the snapshots reproducible.
    """
    return snapshot.with_defaults(extension_class=AnchorsSnapshotExtension)


def create_parameters(
    *rel_paths: str, skip_files: None | list[str] = None
) -> list[ParameterSet]:
    """Create parameters for a pytest param_file decorator."""
    paths: list[Path] = []
    for rel_path in rel_paths:
        assert not Path(rel_path).is_absolute()
        path = TEST_DIR.joinpath(rel_path)
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(path.glob("*.yaml"))
        else:
            raise FileNotFoundError(f"File / folder not found: {path}")

    if skip_files:
        paths = [
            path for path in paths if str(path.relative_to(TEST_DIR)) not in skip_files
        ]

    if not paths:
        raise FileNotFoundError(f"No files found: {rel_paths}")

    if len(paths) == 1:
        with paths[0].open(encoding="utf8") as f:
            try:
                data = yaml.safe_load(f)
            except Exception as err:
                raise OSError(f"Error loading {paths[0]}") from err
        return [pytest.param(value, id=id) for id, value in data.items()]
    else:
        params: list[ParameterSet] = []
        for subpath in paths:
            with subpath.open(encoding="utf8") as f:
                try:
                    data = yaml.safe_load(f)
                except Exception as err:
                    raise OSError(f"Error loading {subpath}") from err
            for key, value in data.items():
                params.append(
                    pytest.param(
                        value,
                        id=f"{subpath.relative_to(TEST_DIR).with_suffix('')}-{key}",
                    )
                )
        return params


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate tests for a ``@pytest.mark.fixture_file`` decorator."""
    for marker in metafunc.definition.iter_markers(name="fixture_file"):
        params = create_parameters(*marker.args, **marker.kwargs)
        metafunc.parametrize(argnames="content", argvalues=params)


@pytest.fixture
def write_fixture_files() -> Callable[[Path, dict[str, str | list[Path]]], None]:
    def _inner(tmp: Path, content: dict[str, str | list[Path]]) -> None:
        section_file_mapping: dict[str, Path] = {
            "ubproject": tmp / "ubproject.toml",
        }
        for section, file_path in section_file_mapping.items():
            if section in content:
                if isinstance(content[section], str):
                    file_path.write_text(content[section], encoding="utf-8")  # type: ignore[assignment]
                else:
                    raise ValueError(
                        f"Unsupported content type for section '{section}': {type(content[section])}"
                    )
        src_paths: list[Path] = []
        for key, value in content.items():
            if key.startswith("dummy") and isinstance(value, str):
                dummy_file_path = tmp / key
                dummy_file_path.write_text(value, encoding="utf-8")
                src_paths.append(dummy_file_path)
        content["src_paths"] = src_paths

    return _inner
