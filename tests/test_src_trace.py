from collections.abc import Callable
from pathlib import Path
import shutil

import pytest
from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("sphinx_project", "source_code"),
    [
        (Path("data") / "sphinx", Path("data") / "dcdc"),
        (
            Path("doc_test") / "recursive_dirs",
            Path("doc_test") / "recursive_dirs" / "dummy_src_lv1",
        ),
    ],
)
def test_build_html(
    tmpdir: Path,
    make_app: Callable[..., SphinxTestApp],
    sphinx_project,
    source_code,
    snapshot_doctree,
):
    this_file_dir = Path(__file__).parent

    sphinx_src_dir = tmpdir / sphinx_project
    shutil.copytree(
        this_file_dir / sphinx_project,
        sphinx_src_dir,
        dirs_exist_ok=True,
    )
    shutil.copytree(
        this_file_dir / source_code,
        tmpdir / source_code,
        dirs_exist_ok=True,
    )

    app: SphinxTestApp = make_app(
        srcdir=Path(sphinx_src_dir),
        freshenv=True,
    )
    app.build()
    html = Path(app.outdir, "index.html").read_text()

    assert html
    assert app.env.get_doctree("index") == snapshot_doctree
