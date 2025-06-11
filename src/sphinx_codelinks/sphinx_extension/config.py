from dataclasses import MISSING, dataclass, field, fields
from typing import Any, Literal, TypedDict, cast

from sphinx.application import Sphinx
from sphinx.config import Config as _SphinxConfig
from ubt_source_tracing.virtual_docs.config import (
    OneLineCommentStyle,
    OneLineCommentStyleType,
)

SRC_TRACE_CACHE: str = "src_trace_cache"


class SourceTracingLineHref:
    """Global class for the mapping between source file line numbers and Sphinx documentation links."""

    def __init__(self) -> None:
        self.mappings: dict[str, dict[int, str]] = {}


file_lineno_href = SourceTracingLineHref()


class SrcTraceProjectConfigType(TypedDict):
    # only support C/C++ for now
    comment_type: Literal["cpp", "hpp", "c", "h"]
    src_dir: str
    remote_url_pattern: str
    exclude: list[str]
    include: list[str]
    gitignore: bool
    oneline_comment_style: OneLineCommentStyle


@dataclass
class SrcTraceSphinxConfig:
    def __init__(self, config: _SphinxConfig) -> None:
        super().__setattr__("_config", config)

    def __getattribute__(self, name: str) -> Any:  # type: ignore[misc]
        if name.startswith("__") or name == "_config":
            return super().__getattribute__(name)
        return getattr(super().__getattribute__("_config"), f"src_trace_{name}")

    def __setattr__(self, name: str, value: Any) -> None:  # type: ignore[misc]
        if name == "_config" and "src_trace_projects" in value:
            src_trace_projects: dict[str, SrcTraceProjectConfigType] = value[
                "src_trace_projects"
            ]
            for _config in src_trace_projects.values():
                # overwrite the config into different types on purpose
                # covert dict to OneLineCommentStyle class
                oneline_comment_style: OneLineCommentStyleType | None = cast(
                    OneLineCommentStyleType, _config.get("oneline_comment_style")
                )
                if not oneline_comment_style:
                    raise Exception("OneLineCommentStyle is not given")

                _config["oneline_comment_style"] = OneLineCommentStyle(
                    **oneline_comment_style
                )
        if name.startswith("__") or name == "_config":
            return super().__setattr__(name, value)

        return setattr(super().__getattribute__("_config"), f"src_trace_{name}", value)

    @classmethod
    def add_config_values(cls, app: Sphinx) -> None:
        """Add all config values to Sphinx application"""
        for item in fields(cls):
            if item.default_factory is not MISSING:
                default = item.default_factory()
            elif item.default is not MISSING:
                default = item.default
            else:
                raise Exception(f"Field {item.name} has no default value or factory")

            name = item.name
            app.add_config_value(
                f"src_trace_{name}",
                default,
                item.metadata["rebuild"],
                types=item.metadata["types"],
            )

    @classmethod
    def field_names(cls) -> set[str]:
        return {item.name for item in fields(cls)}

    config_from_toml: str | None = field(
        default=None,
        metadata={
            "rebuild": "env",
            "types": (str, type(None)),
            "schema": {
                "type": ["string", "null"],
                "examples": ["config.toml", None],
            },
        },
    )
    """Path to a TOML file to load configuration from."""

    set_local_url: bool = field(
        default=False,
        metadata={
            "rebuild": "env",
            "types": (bool,),
        },
    )
    """Set the file URL in the extracted need."""

    local_url_field: str = field(
        default="local-url",
        metadata={"rebuild": "env", "types": (str,)},
    )
    """The field name for the file URL in the extracted need."""

    set_remote_url: bool = field(
        default=False,
        metadata={
            "rebuild": "env",
            "types": (bool,),
        },
    )
    remote_url_field: str = field(
        default="remote-url",
        metadata={"rebuild": "env", "types": (str,)},
    )
    """The field name for the remote URL in the extracted need."""

    projects: dict[str, SrcTraceProjectConfigType] = field(
        default_factory=dict,
        metadata={"rebuild": "env", "types": ()},
    )
    """The configuration for the source tracing projects."""

    debug_measurement: bool = field(
        default=False, metadata={"rebuild": "html", "types": (bool,)}
    )
    """If True, log runtime information for various functions."""
    debug_filters: bool = field(
        default=False, metadata={"rebuild": "html", "types": (bool,)}
    )
    """If True, log filter processing runtime information."""
