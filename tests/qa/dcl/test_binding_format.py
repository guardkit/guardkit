"""dcl-binding F-format validation (D2 §2)."""

from __future__ import annotations

import pytest

from guardkit.qa.formats import (
    FORMAT_KINDS,
    KIND_ALIASES,
    DclBinding,
    QAFormatError,
    resolve_kind,
    validate_instance,
)


def test_registered_kind_and_alias() -> None:
    assert FORMAT_KINDS["dcl-binding"] is DclBinding
    assert KIND_ALIASES["f17"] == "dcl-binding"
    assert resolve_kind("dcl-binding") is DclBinding
    assert resolve_kind("f17") is DclBinding


def test_valid_binding_fixture_validates(binding_file) -> None:
    instance = validate_instance("dcl-binding", binding_file)
    assert isinstance(instance, DclBinding)
    cap = instance.capabilities["ReportServiceStatistics"]
    assert cap.intents["StatisticsQuery"].method == "GET"
    assert cap.intents["StatisticsQuery"].path == "/stats"
    assert cap.success_status == 200
    assert cap.fields["firstRequestAt"].format == "iso8601_utc"
    assert cap.fields["firstRequestAt"].state == "Serving"


def test_extra_key_is_rejected_loud(tmp_path) -> None:
    bad = tmp_path / "binding.yaml"
    bad.write_text(
        "format_version: '1.0'\n"
        "capabilities:\n"
        "  Cap:\n"
        "    intents: {Do: {method: GET, path: /x}}\n"
        "    bogus_key: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(QAFormatError):
        validate_instance("dcl-binding", bad)


def test_missing_intents_is_rejected(tmp_path) -> None:
    bad = tmp_path / "binding.yaml"
    bad.write_text(
        "format_version: '1.0'\ncapabilities:\n  Cap:\n    intents: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(QAFormatError):
        validate_instance("dcl-binding", bad)


def test_naming_only_camel_to_snake(tmp_path) -> None:
    bad = tmp_path / "binding.yaml"
    bad.write_text(
        "format_version: '1.0'\n"
        "capabilities:\n"
        "  Cap:\n"
        "    intents: {Do: {method: GET, path: /x}}\n"
        "    naming: kebab-case\n",
        encoding="utf-8",
    )
    with pytest.raises(QAFormatError):
        validate_instance("dcl-binding", bad)
