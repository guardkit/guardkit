"""Shared base for the tier-1 QA format schemas (F1–F5).

Every format instance carries a ``format_version`` and validators accept the
current major (N) and the previous major (N-1), refusing anything older loudly
with a migration pointer, and refusing anything *newer* loudly with an upgrade
pointer (scope-design §2 evolution rules, 2026-07-07).

Schema changes are additive within a major version — a gate must never start
failing because a schema grew a field. Instances are YAML (or JSON — YAML is a
superset), human-readable and diffable; no format may require a database to
read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar, Dict, Type

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class QAFormatError(Exception):
    """A QA format instance failed to load or validate.

    The message is intended to be printed verbatim by ``guardkit qa validate``
    — it must name the file, the format kind, and every field-level problem so
    a failing instance fails LOUDLY, never quietly.
    """


class QAFormatModel(BaseModel):
    """Base model for all tier-1 QA formats.

    Subclasses set ``FORMAT_KIND`` (the CLI kind string) and
    ``CURRENT_FORMAT_VERSION`` (``"<major>.<minor>"``). ``extra="forbid"`` so a
    typo'd or unknown key is a validation error, not silent acceptance —
    mutated/corrupt instances must fail loudly.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    #: CLI kind string, e.g. ``"pass-bar"``. Set by each concrete format.
    FORMAT_KIND: ClassVar[str] = ""
    #: Current schema version for the format, ``"<major>.<minor>"``.
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    format_version: str

    @field_validator("format_version")
    @classmethod
    def _check_format_version(cls, value: str) -> str:
        """Accept major N and N-1; refuse older and newer loudly."""
        try:
            instance_major = int(str(value).split(".", 1)[0])
        except ValueError as exc:
            raise ValueError(
                f"format_version {value!r} is not a '<major>.<minor>' version string"
            ) from exc

        current_major = int(cls.CURRENT_FORMAT_VERSION.split(".", 1)[0])
        accepted = {current_major, current_major - 1} - {0, -1}

        if instance_major in accepted:
            return value
        if instance_major < current_major:
            raise ValueError(
                f"format_version {value!r} is older than the supported window "
                f"(this guardkit accepts majors {sorted(accepted)} for "
                f"'{cls.FORMAT_KIND}'). Migrate the instance forward — see "
                f"guardkit/qa/formats/ for the current schema and its "
                f"changelog before re-validating."
            )
        raise ValueError(
            f"format_version {value!r} is newer than this guardkit understands "
            f"(current: {cls.CURRENT_FORMAT_VERSION} for '{cls.FORMAT_KIND}'). "
            f"Upgrade guardkit; do not edit the instance down."
        )


def load_yaml_or_json(path: Path) -> Dict[str, Any]:
    """Load a format instance file (YAML or JSON) into a dict.

    Raises:
        QAFormatError: file missing, unparseable, or not a mapping at the root.
    """
    if not path.is_file():
        raise QAFormatError(f"{path}: file not found")
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise QAFormatError(f"{path}: not valid YAML/JSON — {exc}") from exc
    if not isinstance(data, dict):
        raise QAFormatError(
            f"{path}: root of a QA format instance must be a mapping, "
            f"got {type(data).__name__}"
        )
    return data


def validate_file(model_cls: Type[QAFormatModel], path: Path) -> QAFormatModel:
    """Validate ``path`` against ``model_cls``, raising QAFormatError loudly."""
    data = load_yaml_or_json(path)
    try:
        return model_cls.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError formats itself well
        raise QAFormatError(
            f"{path}: INVALID {model_cls.FORMAT_KIND} instance\n{exc}"
        ) from exc


def export_json_schema(model_cls: Type[QAFormatModel]) -> str:
    """Return the JSON-Schema for a format model as a pretty-printed string."""
    return json.dumps(model_cls.model_json_schema(by_alias=True), indent=2)
