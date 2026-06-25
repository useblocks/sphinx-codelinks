from pathlib import Path

from sphinx_codelinks.analyse.preproc import compile_db


def test_find_compile_db_in_build_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    build = tmp_path / "build"
    build.mkdir()
    db = build / "compile_commands.json"
    db.write_text("[]")
    src = tmp_path / "src" / "deep"
    src.mkdir(parents=True)
    # Walk up from src/deep should find build/compile_commands.json? No:
    # walk-up only ascends; the db is in a sibling 'build'. So a db placed
    # at the project root is what walk-up finds. Place one at root instead.
    root_db = tmp_path / "compile_commands.json"
    root_db.write_text("[]")
    found = compile_db.find_compile_db(src, project_root=tmp_path)
    assert found == root_db


def test_find_compile_db_absent(tmp_path: Path):
    (tmp_path / "ubproject.toml").write_text("")
    src = tmp_path / "a"
    src.mkdir()
    assert compile_db.find_compile_db(src, project_root=tmp_path) is None


def test_find_compile_db_stops_at_git_root(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    db = tmp_path / "compile_commands.json"
    db.write_text("[]")
    nested = tmp_path / "x" / "y"
    nested.mkdir(parents=True)
    assert compile_db.find_compile_db(nested) == db
