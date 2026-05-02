"""Integration tests for ``guardkit feature validate`` smoke-gate paths.

Pins TASK-FPSG-004 (L3d): when a feature YAML has a stale
``smoke_gates.command`` path, ``guardkit feature validate FEAT-XXXX`` must

1. exit non-zero (any structural error → non-zero, AC unchanged), and
2. surface the byte-identical message from ``format_smoke_gate_path_error``
   so the agent sees the same error wording as
   ``generate-feature-yaml --validate-smoke-gates`` (TASK-FPSG-002).

The test drives the click CLI directly via ``CliRunner`` so it exercises
the full code path: ``validate`` → ``_load_raw_yaml`` → schema check →
``load_feature(validate_paths=False)`` → ``validate_feature`` → output
rendering. No subprocess, no installer wrapper — the wrapper is covered
separately in ``test_install_wrapper_feature_subcommand.py``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from guardkit.cli.feature import feature as feature_group
from guardkit.lib.pytest_argv import format_smoke_gate_path_error


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_feature_body(smoke_gates_block: str = "") -> str:
    body = dedent(
        """\
        id: FEAT-FPSG4I
        name: FPSG-004 integration fixture
        description: validate CLI smoke-gate path fixture.
        created: "2026-05-02T13:30:00Z"
        complexity: 4
        estimated_tasks: 1
        tasks:
          - id: TASK-FPSG4I-T1
            file_path: tasks/in_progress/TASK-FPSG4I-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-FPSG4I-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )
    if smoke_gates_block:
        body += smoke_gates_block
    return body


def _write_task_file(repo_root: Path, file_path: str) -> None:
    target = repo_root / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        dedent(
            """\
            ---
            id: TASK-FPSG4I-T1
            title: Fixture task
            status: in_progress
            ---

            Fixture task body.
            """
        )
    )


@pytest.fixture
def repo_with_feature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """tmp_path repo with realistic ``tests/<name>`` layout + feature YAML.

    ``cli/feature.py validate`` resolves paths relative to ``Path.cwd()``,
    so we ``chdir`` into ``tmp_path`` for the duration of the test.
    """
    (tmp_path / "tests" / "forge").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / ".guardkit" / "features").mkdir(parents=True)
    _write_task_file(tmp_path, "tasks/in_progress/TASK-FPSG4I-T1.md")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_feature_yaml(repo_root: Path, feature_id: str, body: str) -> Path:
    path = repo_root / ".guardkit" / "features" / f"{feature_id}.yaml"
    path.write_text(body)
    return path


# ---------------------------------------------------------------------------
# AC: bad path → non-zero exit + byte-identical error wording
# ---------------------------------------------------------------------------


def test_validate_flags_missing_smoke_gate_path_with_nonzero_exit(
    repo_with_feature: Path,
) -> None:
    """``smoke_gates.command: pytest tests/cli`` → exit 1, message in output."""
    smoke = dedent(
        """\
        smoke_gates:
          after_wave: 1
          command: pytest tests/cli -x
          expected_exit: 0
          timeout: 60
        """
    )
    _write_feature_yaml(
        repo_with_feature, "FEAT-FPSG4I", _minimal_feature_body(smoke)
    )

    runner = CliRunner()
    result = runner.invoke(feature_group, ["validate", "FEAT-FPSG4I"])

    # AC: exit non-zero on any structural error (unchanged from prior
    # behaviour — TASK-FPSG-004 only adds a new error class).
    assert result.exit_code == 1, (
        f"Expected exit code 1; got {result.exit_code}.\n"
        f"Output:\n{result.output}"
    )

    # AC: message lines from the shared formatter must appear in output.
    # We don't assert byte-identicalness of the entire CLI rendering
    # (Rich adds the structural-errors banner and a per-line marker), but
    # the formatter's content lines must be present so the agent sees the
    # bad path, the repo root, and the discovered roots — same content
    # as L3b ``--validate-smoke-gates`` and L4 pre-flight surface.
    assert "tests/cli" in result.output
    assert str(repo_with_feature) in result.output
    assert "Available test roots" in result.output
    assert "tests/forge" in result.output


def test_validate_byte_identical_message_with_format_smoke_gate_path_error(
    repo_with_feature: Path,
) -> None:
    """The formatter output is embedded verbatim in the structural-errors list.

    Pins the byte-identical contract: every line of
    ``format_smoke_gate_path_error`` appears verbatim in the CLI output
    so an agent comparing wording across L3b and L3d sees the same
    text.
    """
    smoke = dedent(
        """\
        smoke_gates:
          after_wave: 1
          command: pytest tests/cli -x
          expected_exit: 0
          timeout: 60
        """
    )
    _write_feature_yaml(
        repo_with_feature, "FEAT-FPSG4I", _minimal_feature_body(smoke)
    )

    runner = CliRunner()
    result = runner.invoke(feature_group, ["validate", "FEAT-FPSG4I"])

    expected = format_smoke_gate_path_error(
        ["tests/cli"],
        repo_with_feature,
        ["tests/forge", "tests/integration", "tests/unit"],
    )
    # Each line of the formatter output must appear in the rendered CLI
    # output. We can't assert equality of the whole result.output because
    # Rich injects banner / per-line markers around it, but each line
    # must be intact (no truncation, no rewording).
    for line in expected.splitlines():
        assert line in result.output, (
            f"Expected formatter line missing from CLI output:\n"
            f"  Line: {line!r}\n"
            f"  Full output:\n{result.output}"
        )


def test_validate_clean_smoke_gate_path_succeeds(
    repo_with_feature: Path,
) -> None:
    """``smoke_gates.command: pytest tests/forge`` → exit 0."""
    smoke = dedent(
        """\
        smoke_gates:
          after_wave: 1
          command: pytest tests/forge -x
          expected_exit: 0
          timeout: 60
        """
    )
    _write_feature_yaml(
        repo_with_feature, "FEAT-FPSG4I", _minimal_feature_body(smoke)
    )

    runner = CliRunner()
    result = runner.invoke(feature_group, ["validate", "FEAT-FPSG4I"])

    assert result.exit_code == 0, (
        f"Expected exit code 0; got {result.exit_code}.\n"
        f"Output:\n{result.output}"
    )


def test_validate_no_smoke_gates_block_succeeds(
    repo_with_feature: Path,
) -> None:
    """No ``smoke_gates`` key → validate exits 0."""
    _write_feature_yaml(
        repo_with_feature, "FEAT-FPSG4I", _minimal_feature_body()
    )

    runner = CliRunner()
    result = runner.invoke(feature_group, ["validate", "FEAT-FPSG4I"])

    assert result.exit_code == 0, (
        f"Expected exit code 0; got {result.exit_code}.\n"
        f"Output:\n{result.output}"
    )


def test_validate_json_mode_includes_smoke_gate_path_error(
    repo_with_feature: Path,
) -> None:
    """``--json`` mode embeds the formatter output in ``structural_errors``."""
    import json

    smoke = dedent(
        """\
        smoke_gates:
          after_wave: 1
          command: pytest tests/cli -x
          expected_exit: 0
          timeout: 60
        """
    )
    _write_feature_yaml(
        repo_with_feature, "FEAT-FPSG4I", _minimal_feature_body(smoke)
    )

    runner = CliRunner()
    result = runner.invoke(
        feature_group, ["validate", "FEAT-FPSG4I", "--json"]
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["valid"] is False
    assert payload["feature_id"] == "FEAT-FPSG4I"
    # The structural_errors list contains exactly one entry — the
    # smoke-gate path error formatted by the shared helper. JSON mode
    # is the byte-identical channel: no Rich wrapping.
    assert len(payload["structural_errors"]) == 1
    expected = format_smoke_gate_path_error(
        ["tests/cli"],
        repo_with_feature,
        ["tests/forge", "tests/integration", "tests/unit"],
    )
    assert payload["structural_errors"][0] == expected
