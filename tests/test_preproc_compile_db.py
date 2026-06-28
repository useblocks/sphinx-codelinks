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
                    "command": "clang++ -DB=2 -c b.cpp",
                    "file": "b.cpp",
                },
            ]
        )
    )

    flags = compile_db.load_flags_map(db)
    assert flags[a.resolve()] == ["-DA=1"]
    assert flags[b.resolve()] == ["-DB=2"]


def test_load_flags_map_relative_input_path_stripped(tmp_path: Path):
    """Regression: entry whose arguments reference input by relative subdir path must be stripped.

    When directory = tmp_path, file = "src/a.cpp", and arguments contains "src/a.cpp",
    the old code passed abs_file to filter_args. The input_names set only includes
    the basename "a.cpp" and the absolute path — NOT the relative "src/a.cpp" — so
    the relative path leaked as a spurious positional argument.
    """
    src = tmp_path / "src"
    src.mkdir()
    a = src / "a.cpp"
    a.write_text("")
    db = tmp_path / "compile_commands.json"
    db.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "file": "src/a.cpp",
                    "arguments": ["clang++", "-DA=1", "-c", "src/a.cpp"],
                }
            ]
        )
    )

    flags = compile_db.load_flags_map(db)
    assert flags[a.resolve()] == ["-DA=1"]


def test_defines_to_args(tmp_path: Path):
    out = compile_db.defines_to_args(["VARIANT_A", "X=2"], [tmp_path / "inc"])
    assert "-DVARIANT_A" in out
    assert "-DX=2" in out
    assert f"-I{(tmp_path / 'inc')}" in out
    assert "-std=c++17" in out


def test_is_translation_unit_source():
    # Compiled translation-unit sources (skipped when build-excluded).
    assert compile_db.is_translation_unit_source(Path("a.c"))
    assert compile_db.is_translation_unit_source(Path("a.cpp"))
    assert compile_db.is_translation_unit_source(Path("a.cc"))
    assert compile_db.is_translation_unit_source(Path("a.cxx"))
    assert compile_db.is_translation_unit_source(Path("A.CPP"))  # case-insensitive
    # Header-like files (parsed standalone when absent from the DB).
    assert not compile_db.is_translation_unit_source(Path("a.h"))
    assert not compile_db.is_translation_unit_source(Path("a.hpp"))
    assert not compile_db.is_translation_unit_source(Path("a.hxx"))
    assert not compile_db.is_translation_unit_source(Path("a.hh"))
    assert not compile_db.is_translation_unit_source(Path("a.ci"))
    assert not compile_db.is_translation_unit_source(Path("a.ihl"))
