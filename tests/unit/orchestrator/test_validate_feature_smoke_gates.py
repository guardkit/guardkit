"""Smoke-gate path validation in ``FeatureLoader.validate_feature``.

Pins TASK-FPSG-004 (L3d): the collect-without-raising defense layer that
runs alongside orchestration / dependency / task_type checks so a stale
``smoke_gates.command`` path lands in the structural-errors list of
``guardkit feature validate FEAT-XXXX`` instead of failing fast at parse
time.

Sister of ``test_feature_loader_smoke_gate_paths.py`` (TASK-FPSG-005, L4
pre-flight) — same fixture shape, opposite contract:

- L4 (``load_feature(validate_paths=True)``)  → raises on bad path
- L3d (``load_feature(validate_paths=False)`` + ``validate_feature``)
  → collects bad path as a structural error, byte-identical message

The byte-identical message contract is what TASK-FPSG-004 buys: an agent
sees the same output whether it invokes
``generate-feature-yaml --validate-smoke-gates`` (L3b) or
``guardkit feature validate`` (L3d), so the fix path is the same in both
flows. The shared formatter lives in ``guardkit.lib.pytest_argv``.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import List

import pytest

from guardkit.lib.pytest_argv import format_smoke_gate_path_error
from guardkit.orchestrator.feature_loader import FeatureLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_feature_yaml(features_dir: Path, feature_id: str, body: str) -> Path:
    features_dir.mkdir(parents=True, exist_ok=True)
    path = features_dir / f"{feature_id}.yaml"
    path.write_text(body)
    return path


def _minimal_feature_body(smoke_gates_block: str = "") -> str:
    body = dedent(
        """\
        id: FEAT-FPSG4
        name: FPSG-004 fixture
        description: validate_feature smoke-gate path fixture.
        created: 2026-05-02T13:30:00Z
        complexity: 4
        estimated_tasks: 1
        tasks:
          - id: TASK-FPSG4-T1
            file_path: tasks/in_progress/TASK-FPSG4-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-FPSG4-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )
    if smoke_gates_block:
        body += smoke_gates_block
    return body


def _write_task_file(repo_root: Path, file_path: str) -> None:
    """Write a minimal task markdown file so structural validation passes."""
    target = repo_root / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        dedent(
            """\
            ---
            id: TASK-FPSG4-T1
            title: Fixture task
            status: in_progress
            ---

            Fixture task body.
            """
        )
    )


@pytest.fixture
def repo_with_tests(tmp_path: Path) -> Path:
    """tmp_path "repo" with realistic ``tests/<name>`` layout + a task file.

    Includes the task file referenced in the fixture YAML so the
    structural validator's other checks (task file exists, task_type
    valid) all pass. That way assertions can pin "exactly the new
    smoke-gate path error appears in the errors list" without false
    positives from an unrelated structural error.
    """
    (tmp_path / "tests" / "forge").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / ".guardkit" / "features").mkdir(parents=True)
    _write_task_file(tmp_path, "tasks/in_progress/TASK-FPSG4-T1.md")
    return tmp_path


def _load_and_validate(
    repo_root: Path, feature_id: str = "FEAT-FPSG4"
) -> List[str]:
    """Load with ``validate_paths=False`` and return validate_feature errors.

    Mirrors the call sequence in ``cli/feature.py validate``: the
    lenient parse skips the L4 raise, then ``validate_feature`` aggregates
    every structural error in one report.
    """
    feature = FeatureLoader.load_feature(
        feature_id, repo_root=repo_root, validate_paths=False
    )
    return FeatureLoader.validate_feature(feature, repo_root=repo_root)


# ---------------------------------------------------------------------------
# AC: validate_feature flags missing smoke-gate paths as structural errors
# ---------------------------------------------------------------------------


class TestValidateFeatureSmokeGatePaths:
    """Pin the four AC scenarios from TASK-FPSG-004."""

    def test_missing_path_yields_structural_error(
        self, repo_with_tests: Path
    ) -> None:
        """Stale ``tests/cli`` path → error in validate_feature output list."""
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
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        assert len(errors) == 1, (
            f"Expected exactly one structural error (the smoke-gate path "
            f"error). Got: {errors}"
        )
        assert "tests/cli" in errors[0]
        assert str(repo_with_tests) in errors[0]
        # Discovered roots should appear in the "Available test roots" line.
        assert "tests/forge" in errors[0]

    def test_existing_paths_yield_no_smoke_gate_error(
        self, repo_with_tests: Path
    ) -> None:
        """``tests/forge`` exists → validate_feature returns no errors."""
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
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        assert errors == []

    def test_no_smoke_gates_block_yields_no_smoke_gate_error(
        self, repo_with_tests: Path
    ) -> None:
        """No ``smoke_gates`` key → validate_feature returns no errors."""
        _write_feature_yaml(
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(),  # no smoke_gates
        )

        errors = _load_and_validate(repo_with_tests)

        assert errors == []

    def test_non_pytest_command_yields_no_smoke_gate_error(
        self, repo_with_tests: Path
    ) -> None:
        """Custom smoke script (parser returns []) → no error.

        The validator must be specific to pytest paths. A
        ``python3 .guardkit/smoke/foo.py`` command has no positional
        pytest argv to check, so the parser returns ``[]`` and the
        validator stays silent — same contract as L3b and L4.
        """
        smoke = dedent(
            """\
            smoke_gates:
              after_wave: 1
              command: python3 .guardkit/smoke/foo.py
              expected_exit: 0
              timeout: 60
            """
        )
        _write_feature_yaml(
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        assert errors == []


# ---------------------------------------------------------------------------
# AC: byte-identical wording with the L3b CLI mode and L4 pre-flight
# ---------------------------------------------------------------------------


class TestByteIdenticalMessage:
    """The error string must come from ``format_smoke_gate_path_error``.

    TASK-FPSG-004 AC: "output messages must be byte-identical so the
    agent sees the same error whether invoked via ``generate-feature-yaml
    --validate-smoke-gates`` or ``guardkit feature validate``."
    """

    def test_message_is_format_smoke_gate_path_error_output(
        self, repo_with_tests: Path
    ) -> None:
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
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        # Reconstruct the expected message from the same shared
        # formatter the L3b and L4 layers use. Byte-equality of the
        # entire string is the contract.
        expected = format_smoke_gate_path_error(
            ["tests/cli"],
            repo_with_tests,
            ["tests/forge", "tests/integration", "tests/unit"],
        )
        assert errors == [expected]


# ---------------------------------------------------------------------------
# Multi-line / multi-positional regression
# ---------------------------------------------------------------------------


class TestMultilineAndMultiplePositionals:
    """Match the parser-edge cases pinned for L4 and L3b."""

    def test_multiline_block_scalar_with_missing_path(
        self, repo_with_tests: Path
    ) -> None:
        smoke = dedent(
            """\
            smoke_gates:
              after_wave: 1
              command: |
                set -e
                pytest tests/cli -x
              expected_exit: 0
              timeout: 60
            """
        )
        _write_feature_yaml(
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        assert len(errors) == 1
        assert "tests/cli" in errors[0]

    def test_two_positionals_one_missing_only_missing_reported(
        self, repo_with_tests: Path
    ) -> None:
        """``pytest tests/forge tests/cli`` → only ``tests/cli`` is flagged."""
        smoke = dedent(
            """\
            smoke_gates:
              after_wave: 1
              command: pytest tests/forge tests/cli -k "smoke"
              expected_exit: 0
              timeout: 60
            """
        )
        _write_feature_yaml(
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG4",
            _minimal_feature_body(smoke),
        )

        errors = _load_and_validate(repo_with_tests)

        assert len(errors) == 1
        message = errors[0]
        assert "tests/cli" in message
        before_roots = message.split("Available test roots")[0]
        # tests/forge exists, must not appear in the missing-paths section.
        assert "tests/forge" not in before_roots
