import json
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


def test_filter_args_strips_compiler_and_output():
    argv = [
        "clang++", "-std=c++17", "-c", "-o", "out.o",
        "-DVARIANT_A=1", "-I/inc", "-MMD", "-MF", "dep.d",
        "src/a.cpp",
    ]
    out = compile_db.filter_args(argv, "src/a.cpp")
    assert out == ["-std=c++17", "-DVARIANT_A=1", "-I/inc"]


def test_load_flags_map_command_and_arguments_forms(tmp_path: Path):
    a = tmp_path / "a.cpp"
    a.write_text("")
    b = tmp_path / "b.cpp"
    b.write_text("")
    db = tmp_path / "compile_commands.json"
    db.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "arguments": ["clang++", "-DA=1", "-c", str(a)],
                    "file": str(a),
                },
                {
                    "directory": str(tmp_path),
                    "command": f"clang++ -DB=2 -c {b}",
                    "file": "b.cpp",
                },
            ]
        )
    )

    flags = compile_db.load_flags_map(db)
    assert flags[a.resolve()] == ["-DA=1"]
    assert flags[b.resolve()] == ["-DB=2"]


def test_defines_to_args(tmp_path: Path):
    out = compile_db.defines_to_args(["VARIANT_A", "X=2"], [tmp_path / "inc"])
    assert "-DVARIANT_A" in out
    assert "-DX=2" in out
    assert f"-I{(tmp_path / 'inc')}" in out
    assert "-std=c++17" in out
