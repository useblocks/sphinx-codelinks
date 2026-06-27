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


def test_preprocessor_config_passes_analyse_schema_validation():
    """A SourceAnalyseConfig carrying a preprocessor must validate cleanly.

    Regression: the ``preprocessor`` field previously carried a flat
    ``{"type": ["object", "null"]}`` json-schema, so ``check_schema`` validated
    the *constructed* ``PreprocessorConfig`` instance against JSON type
    ``object`` and raised at sphinx ``config-inited``::

        Schema validation error in field 'preprocessor':
        PreprocessorConfig(...) is not of type 'object', 'null'

    Nested dataclass config fields must not carry a flat schema (their siblings
    ``need_id_refs_config`` / ``oneline_comment_style`` do not).
    """
    cfg = convert_analyse_config(
        {
            "get_oneline_needs": True,
            "preprocessor": {"defines": ["FEATURE_A"]},
        }
    )
    assert cfg.preprocessor is not None
    schema_errors = cfg.check_schema()
    assert not any("preprocessor" in err for err in schema_errors), schema_errors
