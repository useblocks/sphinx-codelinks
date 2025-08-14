"""Covert the generated JSON file created by CodeLinks anaylse to need-extend in RST."""

from collections import deque
from dataclasses import MISSING, dataclass, field, fields
import json
from os import linesep
from pathlib import Path
from string import Template
from typing import Any, TypedDict, cast

from jsonschema import ValidationError, validate

from sphinx_codelinks.analyse.models import MarkedContentType, SourceMap
from sphinx_codelinks.logger import logger

NEEDEXTEND_TEMPLATE = Template(""".. needextend:: $need_id
   :$remote_url_field: $remote_url

""")


@dataclass
class MarkedContentSchema:
    @classmethod
    def field_names(cls) -> set[str]:
        return {item.name for item in fields(cls)}

    filepath: str = field(
        metadata={"schema": {"type": "string"}},
    )
    """filepath where the marked content is located."""

    remote_url: str | None = field(
        metadata={"schema": {"type": "string", "nullable": True}}
    )
    """remote url which can be directed to the the marked content."""

    source_map: SourceMap = field(
        metadata={
            "schema": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "object",
                        "properties": {
                            "row": {"type": "integer"},
                            "column": {"type": "integer"},
                        },
                        "required": ["row", "column"],
                    },
                    "end": {
                        "type": "object",
                        "properties": {
                            "row": {"type": "integer"},
                            "column": {"type": "integer"},
                        },
                        "required": ["row", "column"],
                    },
                },
                "required": ["start", "end"],
                "additionalProperties": False,
            }
        }
    )
    """Coordinate of the marked content in a file"""

    tagged_scope: str | None = field(metadata={"schema": {"type": ["string", "null"]}})
    """The scoped tagged by the marked content"""

    type: MarkedContentType = field(
        metadata={
            "schema": {
                "type": "string",
                "enum": [key.value for key in MarkedContentType],
            }
        }
    )
    """Type of the marked content."""

    marker: str | None = field(
        default=None, metadata={"schema": {"type": ["string", "null"]}}
    )
    """Marker of the marked content."""

    need_ids: list[str] | None = field(
        default=None,
        metadata={"schema": {"type": ["array", "null"], "items": {"type": "string"}}},
    )
    """Need id refs which is associated to the need items in the documentation."""
    need: dict[str, str | list[str]] | None = field(
        default=None,
        metadata={
            "schema": {
                "type": ["object", "null"],
                "properties": {"title": {"type": "string"}, "id": {"title": "string"}},
                "required": ["title", "id"],
                "additionalProperties": True,
            }
        },
    )
    """Definition of a need item"""

    rst: str | None = field(
        default=None, metadata={"schema": {"type": ["string", "null"]}}
    )
    """Extracted rst text."""

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
            try:
                validate(instance=value, schema=schema)  # type: ignore[arg-type]  # validate has no type
            except ValidationError as e:
                errors.append(
                    f"Schema validation error in field '{_field_name}': {e.message}"
                )
        return errors

    def check_conditional_required_fields(self) -> list[str]:
        errors = []
        if self.type == MarkedContentType.need.value and not self.need:
            errors.append(
                "Need definition is required for marked content of type 'need'"
            )
        elif self.type == MarkedContentType.need_id_refs.value:
            if not self.marker:
                errors.append(
                    "Marker is required for marked content of type 'need_id_refs'"
                )
            if not self.need_ids:
                errors.append(
                    "Need id refs are required for marked content of type 'need_id_refs'"
                )
        elif self.type == MarkedContentType.need.value and not self.need_ids:
            errors.append(
                "Need id refs are required for marked content of type 'need_id_refs'"
            )
        elif self.type == MarkedContentType.rst.value and not self.rst:
            errors.append("RST text is required for marked content of type 'rst'")
        return errors

    def check_loaded_objs(self) -> list[str]:
        return self.check_schema() + self.check_conditional_required_fields()


class MarkedObjType(TypedDict):
    filepath: str
    remote_url: str | None
    source_map: SourceMap
    tagged_scope: str | None
    type: MarkedContentType
    need_ids: list[str] | None
    need: dict[str, str | list[str]] | None
    rst: str | None


def convert_marked_content(
    jsonpath: Path, outdir: Path, remote_url_field: str = "remote_url"
) -> None:
    """Convert marked objects extracted by anaylse CLI to needextend in RST"""
    with jsonpath.open("r") as f:
        marked_objs = json.load(f)

    warnings = []

    need_id_refs = [
        obj
        for obj in marked_objs
        if obj["type"] == MarkedContentType.need_id_refs.value
    ]

    for obj in need_id_refs:
        schema = MarkedContentSchema(**obj)
        obj_warnings: deque[str] = deque()
        obj_warnings.extend(schema.check_schema())
        obj_warnings.extend(schema.check_conditional_required_fields())
        if obj_warnings:
            obj_warnings.appendleft(f"{obj} has the following warnings:")
            warnings.extend(list(obj_warnings))

    if warnings:
        logger.warning(
            f"Marked objects have the following warnings: {linesep.join(warnings)}"
        )

    needextend_texts: list[str] = []
    for obj in need_id_refs:
        for need_id in obj["need_ids"]:
            needextend_text = NEEDEXTEND_TEMPLATE.safe_substitute(
                need_id=need_id,
                remote_url_field=remote_url_field,
                remote_url=obj[remote_url_field],
            )
            needextend_texts.append(needextend_text)

    needextend_path = outdir / "needextend.rst"
    with needextend_path.open("w") as f:
        f.writelines(needextend_texts)

    logger.info(f"Generated needextend.rst in {needextend_path}")
