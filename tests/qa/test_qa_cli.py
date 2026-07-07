"""``guardkit qa`` CLI: validate / schema / kinds."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from guardkit.cli.qa import qa

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"


def test_validate_passes_on_exemplar() -> None:
    result = CliRunner().invoke(
        qa, ["validate", "known-failures", str(FIXTURES / "study-tutor/known-failures.yaml")]
    )
    assert result.exit_code == 0, result.output
    assert "VALID" in result.output


def test_validate_accepts_f_alias() -> None:
    result = CliRunner().invoke(
        qa, ["validate", "f2", str(FIXTURES / "lpa-platform-poc/known-failures.yaml")]
    )
    assert result.exit_code == 0, result.output


def test_validate_fails_loudly_on_mutant() -> None:
    result = CliRunner().invoke(
        qa, ["validate", "pass-bar", str(FIXTURES / "mutated/pass-bar-mutated.yaml")]
    )
    assert result.exit_code == 1
    assert "VALIDATION FAILED" in result.output
    # Field-level detail must reach the operator, not just a boolean.
    assert "registered_at" in result.output


def test_validate_unknown_kind_exits_nonzero() -> None:
    result = CliRunner().invoke(
        qa, ["validate", "nonsense", str(FIXTURES / "study-tutor/known-failures.yaml")]
    )
    assert result.exit_code == 1
    assert "unknown QA format kind" in result.output


def test_validate_missing_file_exits_nonzero(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        qa, ["validate", "pass-bar", str(tmp_path / "nope.yaml")]
    )
    assert result.exit_code == 1
    assert "file not found" in result.output


def test_schema_export_stdout() -> None:
    result = CliRunner().invoke(qa, ["schema", "pass-bar"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    # The YAML-facing alias survives export (criteria use `class:` on disk).
    criterion = schema["$defs"]["PassBarCriterion"]["properties"]
    assert "class" in criterion


def test_schema_export_to_file(tmp_path: Path) -> None:
    out = tmp_path / "schemas" / "f3.json"
    result = CliRunner().invoke(qa, ["schema", "f3", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text())["title"] == "LeakSweepManifest"


def test_kinds_lists_all_six() -> None:
    result = CliRunner().invoke(qa, ["kinds"])
    assert result.exit_code == 0
    for kind in (
        "pass-bar",
        "known-failures",
        "leak-sweep",
        "gate-registry",
        "results-envelope",
        "evidence-index",
    ):
        assert kind in result.output
