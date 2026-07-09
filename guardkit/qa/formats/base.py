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
import re
from dataclasses import dataclass
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


def check_format_version_window(value: str, current_version: str, kind: str) -> str:
    """Accept major N and N-1 for ``value``; refuse older/newer loudly.

    The same window rule :class:`QAFormatModel` enforces inline, exposed as a
    function so the markdown-convention formats (F11) share it verbatim.
    """
    try:
        instance_major = int(str(value).split(".", 1)[0])
    except ValueError as exc:
        raise ValueError(
            f"format_version {value!r} is not a '<major>.<minor>' version string"
        ) from exc

    current_major = int(current_version.split(".", 1)[0])
    accepted = {current_major, current_major - 1} - {0, -1}

    if instance_major in accepted:
        return value
    if instance_major < current_major:
        raise ValueError(
            f"format_version {value!r} is older than the supported window "
            f"(this guardkit accepts majors {sorted(accepted)} for '{kind}'). "
            f"Migrate the instance forward before re-validating."
        )
    raise ValueError(
        f"format_version {value!r} is newer than this guardkit understands "
        f"(current: {current_version} for '{kind}'). Upgrade guardkit; do not "
        f"edit the instance down."
    )


# ---------------------------------------------------------------------------
# Markdown-convention formats (F11 · executable runbook — session B10)
# ---------------------------------------------------------------------------
#
# Most QA formats are YAML pydantic models. A few are house *markdown*
# patterns; of those, F11 (executable runbook) MUST stay markdown — the binding
# guardrail (WS2 §B10, scope-design §2) is "executable by a human with no
# tooling — markdown first, machine conventions second." So F11 is validated as
# a set of MARKDOWN CONVENTIONS rather than parsed into a strict object model.
# (F7/F12/F13/F14, whose house instance is also markdown, are modelled as their
# structured machine-readable YAML instance — the "data formats first" design
# core — so only F11 needs this layer.)

#: Machine marker a markdown-convention instance carries so its version and kind
#: are declarable without polluting the rendered document (HTML comments are
#: invisible when the markdown renders). Example:
#: ``<!-- qa-format: runbook format_version: 1.0 -->``
_MD_MARKER_RE = re.compile(
    r"<!--\s*qa-format:\s*(?P<kind>[a-z0-9-]+)\s+"
    r"format_version:\s*(?P<version>\d+\.\d+)\s*-->"
)


@dataclass(frozen=True)
class MarkdownValidation:
    """Result of validating a markdown-convention instance.

    Shaped so ``guardkit qa validate`` prints it exactly like a pydantic
    result (``FORMAT_KIND`` + ``format_version``).
    """

    FORMAT_KIND: str
    format_version: str


class MarkdownFormat:
    """Base for markdown-convention QA formats (F11).

    Subclasses set ``FORMAT_KIND`` / ``CURRENT_FORMAT_VERSION`` and implement
    :meth:`_validate_body`, which inspects the markdown text and raises
    ``QAFormatError`` (loud, field-level) on any convention violation. The
    marker line (``<!-- qa-format: <kind> format_version: <v> -->``) supplies
    the version; the base checks the N/N-1 window and kind match.
    """

    FORMAT_KIND: ClassVar[str] = ""
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"
    IS_MARKDOWN: ClassVar[bool] = True

    @classmethod
    def validate_text(cls, text: str, path: Path) -> MarkdownValidation:
        problems: list[str] = []
        marker = _MD_MARKER_RE.search(text)
        if marker is None:
            raise QAFormatError(
                f"{path}: INVALID {cls.FORMAT_KIND} instance\n"
                f"  - missing the machine marker "
                f"'<!-- qa-format: {cls.FORMAT_KIND} format_version: "
                f"{cls.CURRENT_FORMAT_VERSION} -->' (markdown-first, but the "
                f"version/kind marker is required so the validator can pin it)"
            )
        if marker.group("kind") != cls.FORMAT_KIND:
            problems.append(
                f"marker kind {marker.group('kind')!r} != expected "
                f"{cls.FORMAT_KIND!r}"
            )
        version = marker.group("version")
        try:
            check_format_version_window(version, cls.CURRENT_FORMAT_VERSION, cls.FORMAT_KIND)
        except ValueError as exc:
            problems.append(str(exc))

        problems.extend(cls._validate_body(text))

        if problems:
            joined = "\n".join(f"  - {p}" for p in problems)
            raise QAFormatError(
                f"{path}: INVALID {cls.FORMAT_KIND} instance\n{joined}"
            )
        return MarkdownValidation(FORMAT_KIND=cls.FORMAT_KIND, format_version=version)

    @classmethod
    def _validate_body(cls, text: str) -> list[str]:  # pragma: no cover - abstract
        raise NotImplementedError

    @classmethod
    def describe_schema(cls) -> str:
        """Human-readable convention description (the ``schema`` command uses it)."""
        return cls.__doc__ or f"{cls.FORMAT_KIND}: markdown-convention format"


def validate_markdown_file(cls: Type[MarkdownFormat], path: Path) -> MarkdownValidation:
    """Validate a markdown-convention instance file, raising QAFormatError loudly."""
    if not path.is_file():
        raise QAFormatError(f"{path}: file not found")
    text = path.read_text(encoding="utf-8")
    return cls.validate_text(text, path)
