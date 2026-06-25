from pathlib import Path

from sphinx_codelinks.config import (
    PreprocessorConfig,
    SourceAnalyseConfig,
    convert_analyse_config,
)


def test_source_analyse_config_default_preprocessor_is_none():
    cfg = SourceAnalyseConfig()
    assert cfg.preprocessor is None


def test_convert_analyse_config_builds_preprocessor():
    cfg = convert_analyse_config(
        {
            "get_oneline_needs": True,
            "preprocessor": {
                "compile_commands": "build/compile_commands.json",
                "defines": ["VARIANT_A", "PLATFORM_LINUX=1"],
                "includes": ["include"],
                "variant_name": "linux",
            },
        }
    )
    assert isinstance(cfg.preprocessor, PreprocessorConfig)
    assert cfg.preprocessor.compile_commands == Path("build/compile_commands.json")
    assert cfg.preprocessor.defines == ["VARIANT_A", "PLATFORM_LINUX=1"]
    assert cfg.preprocessor.includes == [Path("include")]
    assert cfg.preprocessor.variant_name == "linux"


def test_convert_analyse_config_no_preprocessor_block():
    cfg = convert_analyse_config({"get_oneline_needs": True})
    assert cfg.preprocessor is None
