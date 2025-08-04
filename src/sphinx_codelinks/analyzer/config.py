from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, TypedDict, cast

from jsonschema import ValidationError, validate

LANGUAGE_FILETYPE = {"cpp": ["c", "cpp", "h", "hpp"], "python": ["py"]}


class Language(str, Enum):
    python = "python"
    cpp = "cpp"


class SourceAnalyzerConfigType(TypedDict, total=False):
    src_dir: Path
    markers: list[str]
    language: Language
    outdir: Path


@dataclass
class SourceAnalyzerConfig:
    @classmethod
    def field_names(cls) -> set[str]:
        return {item.name for item in fields(cls)}

    src_dir: Path = field(
        default_factory=lambda: Path("./"), metadata={"schema": {"type": "string"}}
    )
    """The root of the source directory."""
    markers: list[str] = field(
        default_factory=lambda: ["@"],
        metadata={"schema": {"type": "array", "items": {"type": "string"}}},
    )
    """The markers to extract need ids from"""
    language: Language = field(
        default=Language.cpp,
        metadata={"schema": {"type": "string", "enum": ["python", "cpp"]}},
    )
    """The language of the source files."""
    outdir: Path = field(
        default_factory=lambda: Path.cwd(), metadata={"schema": {"type": "string"}}
    )
    """The output directory."""

    @classmethod
    def get_schema(cls, name: str) -> dict[str, Any] | None:  # type: ignore[explicit-any]
        _field = next(_field for _field in fields(cls) if _field.name is name)
        if _field.metadata is not MISSING and "schema" in _field.metadata:
            return cast(dict[str, Any], _field.metadata["schema"])  # type: ignore[explicit-any]
        return None

    def check_schema(self) -> list[str]:
        errors = []
        for _field_name in self.field_names():
            schema = self.get_schema(_field_name)
            value = getattr(self, _field_name)
            if isinstance(value, Path):  # adapt to json schema restriction
                value = str(value)
            try:
                validate(instance=value, schema=schema)  # type: ignore[arg-type] # the library doesn't support typing
            except ValidationError as e:
                errors.append(
                    f"Schema validation error in field '{_field_name}': {e.message}"
                )
        return errors
