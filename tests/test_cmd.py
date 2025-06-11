from pathlib import Path

import pytest
from typer.testing import CliRunner
from ubt_source_tracing.cmd import app

from .conftest import (
    BASIC_VDOC_TOML,
    DEFAULT_VDOC_TOML,
    RECURSIVE_DIR_VDOC_TOML,
    SRC_TRACE_TOML,
    TEST_DIR,
)

runner = CliRunner()


@pytest.mark.parametrize(
    ("options", "stdout"),
    [
        (
            ["discover", str(TEST_DIR / "data" / "dcdc"), "--no-gitignore"],
            "5 files discovered",
        ),
        (
            ["discover", str(TEST_DIR / "data" / "dcdc"), "--gitignore"],
            "4 files discovered",
        ),
    ],
)
def test_discover(options, stdout):
    result = runner.invoke(app, options)
    assert result.exit_code == 0
    assert stdout in result.stdout


@pytest.mark.parametrize(
    ("options", "lines"),
    [
        (
            [
                "vdoc",
                "--config",
                SRC_TRACE_TOML,
                "--project",
                "dcdc",
            ],
            [
                "The virtual documents are generated:",
                Path("charge") / "demo_1.json",
                Path("charge") / "demo_2.json",
                Path("discharge") / "demo_3.json",
                Path("supercharge.json"),
                "The cached files are:",
                TEST_DIR / "data" / "dcdc" / "charge" / "demo_1.cpp",
                TEST_DIR / "data" / "dcdc" / "charge" / "demo_2.cpp",
                TEST_DIR / "data" / "dcdc" / "discharge" / "demo_3.cpp",
                TEST_DIR / "data" / "dcdc" / "supercharge.cpp",
            ],
        ),
        (
            [
                "vdoc",
                "--config",
                BASIC_VDOC_TOML,
            ],
            [
                "The virtual documents are generated:",
                Path("basic_oneliners.json"),
                "The cached files are:",
                TEST_DIR / "data" / "oneline_comment_basic" / "basic_oneliners.c",
            ],
        ),
        (
            [
                "vdoc",
                "--config",
                DEFAULT_VDOC_TOML,
            ],
            [
                "The virtual documents are generated:",
                Path("default_oneliners.json"),
                "The cached files are:",
                TEST_DIR / "data" / "oneline_comment_default" / "default_oneliners.c",
            ],
        ),
        (
            ["vdoc", "--config", RECURSIVE_DIR_VDOC_TOML, "--project", "dummy_src"],
            [
                "The virtual documents are generated:",
                Path("dummy_1.json"),
                Path("dummy_lv2") / "dummy_2.json",
                Path("dummy_lv2") / "dummy_lv3" / "dummy_3.json",
                Path("dummy_lv2") / "dummy_lv3" / "dummy_lv4" / "dummy_4.json",
                "The cached files are:",
                TEST_DIR
                / "doc_test"
                / "recursive_dirs"
                / "dummy_src_lv1"
                / "dummy_1.cpp",
                TEST_DIR
                / "doc_test"
                / "recursive_dirs"
                / "dummy_src_lv1"
                / "dummy_lv2"
                / "dummy_2.cpp",
                TEST_DIR
                / "doc_test"
                / "recursive_dirs"
                / "dummy_src_lv1"
                / "dummy_lv2"
                / "dummy_lv3"
                / "dummy_3.cpp",
                TEST_DIR
                / "doc_test"
                / "recursive_dirs"
                / "dummy_src_lv1"
                / "dummy_lv2"
                / "dummy_lv3"
                / "dummy_lv4"
                / "dummy_4.cpp",
            ],
        ),
    ],
)
def test_vdoc(options, lines, tmp_path):
    options.append("--output-dir")
    options.append(tmp_path)
    for i in range(len(lines)):
        if lines[i] == "The virtual documents are generated:":
            continue
        if lines[i] == "The cached files are:":
            break
        lines[i] = tmp_path / lines[i]

    lines = [str(line) for line in lines]

    result = runner.invoke(
        app,
        options,
    )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == lines
