from collections import deque
from os import linesep
from pathlib import Path
import tempfile
import tomllib
from typing import Annotated, cast

import typer

from sphinx_codelinks.analyzer.config import (
    MarkedRstConfig,
    MarkedRstConfigType,
    NeedIdRefsConfig,
    NeedIdRefsConfigType,
    SourceAnalyzerConfigFileType,
)
from sphinx_codelinks.source_discovery.config import SourceDiscoveryConfig
from sphinx_codelinks.sphinx_extension.config import (
    SrcTraceProjectConfigFileType,
    SrcTraceProjectConfigType,
    build_src_discovery_dict,
    validate_oneline_comment_style,
)
from sphinx_codelinks.virtual_docs.config import (
    OneLineCommentStyle,
    OneLineCommentStyleType,
)

app = typer.Typer(
    no_args_is_help=True, context_settings={"help_option_names": ["-h", "--help"]}
)


@app.command(no_args_is_help=True)
def analyzer(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="The toml config file",
            show_default=False,
            dir_okay=False,
            file_okay=True,
            exists=True,
        ),
    ],
) -> None:
    """Analyze marked content in source code."""
    data = load_src_analyzer_config_from_toml(config)

    # errors: deque[str] = deque()

    # # Get source_discovery configuration
    # src_discovery_4_analyzer_dict: SrcDiscoveryConfigType4Analyzer | None = data.get(
    #     "src_discovery"
    # )
    # if src_discovery_4_analyzer_dict:
    #     src_dicovery_dict: SourceDiscoveryConfigType = {
    #         ("file_types" if key == "comment_type" else key): (
    #             COMMENT_FILETYPE[value] if key == "comment_type" else value
    #         )
    #         for key, value in src_discovery_4_analyzer_dict.items()
    #     }
    #     src_discovery_config = SourceDiscoveryConfig(**src_dicovery_dict)
    # else:
    #     src_discovery_config = SourceDiscoveryConfig()

    # Get oneline_comment_style configuration
    oneline_comment_style_dict: OneLineCommentStyleType | None = data.get(
        "oneline_comment_style"
    )
    if oneline_comment_style_dict is None:
        oneline_comment_style = OneLineCommentStyle()
    else:
        try:
            oneline_comment_style = OneLineCommentStyle(**oneline_comment_style_dict)
        except TypeError as e:
            raise typer.BadParameter(
                f"Invalid oneline comment style configuration: {e}"
            ) from e

    # Get need_id_refs configuration
    need_id_refs_confg_dict: NeedIdRefsConfigType | None = data.get("need_id_refs")
    if not need_id_refs_confg_dict:
        need_id_refs_config = NeedIdRefsConfig()
    else:
        try:
            need_id_refs_config = NeedIdRefsConfig(**need_id_refs_confg_dict)
        except TypeError as e:
            raise typer.BadParameter(
                f"Invalid oneline comment style configuration: {e}"
            ) from e

    # Get marked_rst configuration
    marked_rst_config_dict: MarkedRstConfigType | None = data.get("marked_rst")
    if not marked_rst_config_dict:
        marked_rst_config = MarkedRstConfig()
    else:
        try:
            marked_rst_config = MarkedRstConfig(**marked_rst_config_dict)
        except TypeError as e:
            raise typer.BadParameter(
                f"Invalid oneline comment style configuration: {e}"
            ) from e

    non_root_configs = {
        "source_discovery",
        "oneline_comment_style",
        "need_id_refs",
        "marked_rst",
    }
    # Get root config
    src_analyzer_dict = {
        key: value for key, value in data.items() if key not in non_root_configs
    }
    src_analyzer_dict["need_id_refs_config"] = need_id_refs_config
    src_analyzer_dict["marked_rst_config"] = marked_rst_config
    src_analyzer_dict["oneline_comment_style"] = oneline_comment_style


@app.command(no_args_is_help=True)
def discover(
    src_dir: Annotated[
        Path,
        typer.Argument(
            ...,
            help="Root directory for discovery",
            show_default=False,
            dir_okay=True,
            file_okay=False,
            exists=True,
            resolve_path=True,
        ),
    ],
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--excludes",
            "-e",
            help="Glob patterns to be excluded.",
        ),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--includes",
            "-i",
            help="Glob patterns to be included.",
        ),
    ] = None,
    gitignore: Annotated[bool, typer.Option(help="Respect .gitignore(s)")] = True,
    file_types: Annotated[
        list[str] | None,
        typer.Option(
            "--file-type",
            "-f",
            help="The file extension to be discovered. If not specified, all files are discovered.",
        ),
    ] = None,
) -> None:
    """Discover the filepaths from the given root directory."""
    from sphinx_codelinks.source_discovery.source_discover import SourceDiscover

    source_discover = SourceDiscover(
        src_dir=src_dir,
        exclude=exclude,
        include=include,
        file_types=file_types,
        gitignore=gitignore,
    )
    typer.echo(f"{len(source_discover.source_paths)} files discovered")
    for file_path in source_discover.source_paths:
        typer.echo(file_path)


@app.command(no_args_is_help=True)
def vdoc(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="The toml config file",
            show_default=False,
            dir_okay=False,
            file_okay=True,
            exists=True,
        ),
    ],
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="project identifier in config")
    ] = None,
    output_dir: Path = typer.Option(  # noqa: B008  # to support filepath
        Path(tempfile.gettempdir()),  # noqa: B008  # to support filepath
        "--output-dir",
        "-o",
        help="The output directory of generated documents and caches.",
    ),
) -> None:
    """Generate virtual documents for caching and extract the oneline comments."""

    data = load_config_from_toml(config, project)

    errors: deque[str] = deque()

    oneline_comment_style_dict: OneLineCommentStyleType | None = data.get(
        "oneline_comment_style"
    )
    if oneline_comment_style_dict is None:
        oneline_comment_style = OneLineCommentStyle()
    else:
        try:
            oneline_comment_style = OneLineCommentStyle(**oneline_comment_style_dict)
        except TypeError as e:
            raise typer.BadParameter(
                f"Invalid oneline comment style configuration: {e}"
            ) from e

    project_config = cast(
        SrcTraceProjectConfigType,
        {
            key: value if key != "oneline_comment_style" else oneline_comment_style
            for key, value in data.items()
        },
    )
    oneline_errors = validate_oneline_comment_style(project_config)

    if oneline_errors:
        errors.appendleft("Invalid oneline comment style configuration:")
        errors.extend(oneline_errors)
    src_discovery_errors = []
    src_discovery_dict = build_src_discovery_dict(project_config)
    if src_discovery_dict:
        src_discovery_config = SourceDiscoveryConfig(**src_discovery_dict)
    else:
        src_discovery_config = SourceDiscoveryConfig()
    src_discovery_errors.extend(src_discovery_config.check_schema())

    if src_discovery_errors:
        errors.appendleft("Invalid source discovery configuration:")
        errors.extend(src_discovery_errors)

    if errors:
        raise typer.BadParameter(f"{linesep.join(errors)}")

    from sphinx_codelinks.source_discovery.source_discover import SourceDiscover

    src_dir = (config.parent / src_discovery_config.src_dir).resolve()
    source_discover = SourceDiscover(
        src_dir=src_dir,
        exclude=src_discovery_config.exclude,
        include=src_discovery_config.include,
        file_types=src_discovery_config.file_types,
        gitignore=src_discovery_config.gitignore,
    )

    from sphinx_codelinks.virtual_docs.virtual_docs import VirtualDocs

    virtual_docs = VirtualDocs(
        src_files=source_discover.source_paths,
        src_dir=str(src_dir),
        output_dir=str(output_dir),
        oneline_comment_style=oneline_comment_style,
        comment_type=src_discovery_config.file_types[0]
        if src_discovery_config.file_types
        else "c",
    )
    virtual_docs.collect()
    virtual_docs.dump_virtual_docs()

    if len(virtual_docs.virtual_docs) > 0:
        typer.echo("The virtual documents are generated:")
        for v_doc in virtual_docs.virtual_docs:
            json_path = output_dir / v_doc.filepath.with_suffix(".json").relative_to(
                src_dir
            )
            typer.echo(json_path)
    else:
        typer.echo("No virtual documents are generated.")

    virtual_docs.cache.update_cache()
    typer.echo("The cached files are:")
    for cached_file in virtual_docs.cache.cached_files:
        typer.echo(cached_file)


def load_config_from_toml(
    toml_file: Path, project: str | None = None
) -> SrcTraceProjectConfigFileType:
    try:
        with toml_file.open("rb") as f:
            toml_data = tomllib.load(f)

        if project:
            toml_data = toml_data["src_trace"]["projects"][project]

    except Exception as e:
        raise Exception(
            f"Failed to load source tracing configuration from {toml_file}"
        ) from e

    return cast(SrcTraceProjectConfigFileType, toml_data)


def load_src_analyzer_config_from_toml(toml_file: Path) -> SourceAnalyzerConfigFileType:
    try:
        with toml_file.open("rb") as f:
            toml_data = tomllib.load(f)

    except Exception as e:
        raise Exception(
            f"Failed to load Source Analyzer configuration from {toml_file}"
        ) from e

    return cast(SourceAnalyzerConfigFileType, toml_data)


if __name__ == "__main__":
    app()
