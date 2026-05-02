"""Pre-flight smoke-gate path validation in ``FeatureLoader._parse_feature``.

Pins TASK-FPSG-005 (L4 — defense-in-depth): the runtime safety net that
catches a stale ``tests/cli``-style path at feature-load time, before
``/feature-build`` bootstraps the worktree and runs Wave 1 only to fail
on the smoke gate ~17 minutes later.

The test pairs a tmp_path "repo" with a fixture feature YAML, runs it
through ``FeatureLoader.load_feature`` (which calls ``_parse_feature``),
and asserts:

- missing path under tests/ → ``SmokeGatePathError`` with the bad path,
  the repo root, and the discovered test roots in the message.
- existing path → load succeeds, no exception.
- no ``smoke_gates`` block → load succeeds (nothing to validate).
- non-pytest ``smoke_gates.command`` (e.g. ``python3 ...``) → load
  succeeds (parser returns ``[]``, validator skipped).
- regression: today's behaviour — the failure used to surface only at
  ``run_smoke_gate`` time inside the orchestrator, *not* at
  ``_parse_feature`` time. This file pins that the failure now happens
  at load time.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    SchemaValidationError,
    SmokeGatePathError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_feature_yaml(features_dir: Path, feature_id: str, body: str) -> Path:
    """Write a feature YAML to ``<features_dir>/<feature_id>.yaml``."""
    features_dir.mkdir(parents=True, exist_ok=True)
    path = features_dir / f"{feature_id}.yaml"
    path.write_text(body)
    return path


def _minimal_feature_body(smoke_gates_block: str = "") -> str:
    """Return a minimal-but-valid feature YAML body with optional smoke_gates."""
    body = dedent(
        """\
        id: FEAT-FPSG5
        name: FPSG-005 fixture
        description: Pre-flight smoke-gate path validation fixture.
        created: 2026-05-02T13:30:00Z
        complexity: 4
        estimated_tasks: 1
        tasks:
          - id: TASK-FPSG5-T1
            file_path: tasks/in_progress/TASK-FPSG5-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-FPSG5-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )
    if smoke_gates_block:
        body += smoke_gates_block
    return body


@pytest.fixture
def repo_with_tests(tmp_path: Path) -> Path:
    """Create a tmp_path "repo" with realistic ``tests/`` subdirs.

    The layout mirrors a forge-style repo so ``discover_test_roots`` has
    something to find when generating the "Available test roots" line in
    the error message.
    """
    (tmp_path / "tests" / "forge").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / ".guardkit" / "features").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Core acceptance criteria
# ---------------------------------------------------------------------------


class TestPreflightSmokeGatePaths:
    """Pin the four AC scenarios from TASK-FPSG-005."""

    def test_missing_path_raises_smoke_gate_path_error(
        self, repo_with_tests: Path
    ) -> None:
        """Stale ``tests/cli`` path → SmokeGatePathError at load time."""
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        with pytest.raises(SmokeGatePathError) as exc_info:
            FeatureLoader.load_feature("FEAT-FPSG5", repo_root=repo_with_tests)

        message = str(exc_info.value)
        # AC: message includes the missing path, the repo root, and the
        # available roots — agents need all three to fix the YAML in one
        # edit instead of repeatedly bouncing off the validator.
        assert "tests/cli" in message
        assert str(repo_with_tests) in message
        assert "tests/forge" in message
        assert "tests/integration" in message
        assert "tests/unit" in message

    def test_existing_path_loads_cleanly(self, repo_with_tests: Path) -> None:
        """``tests/forge`` exists → load succeeds with smoke_gates populated."""
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        feature = FeatureLoader.load_feature(
            "FEAT-FPSG5", repo_root=repo_with_tests
        )

        assert feature.smoke_gates is not None
        assert feature.smoke_gates.command == "pytest tests/forge -x"

    def test_no_smoke_gates_block_loads_cleanly(
        self, repo_with_tests: Path
    ) -> None:
        """No ``smoke_gates`` key → load succeeds, ``smoke_gates is None``."""
        _write_feature_yaml(
            repo_with_tests / ".guardkit" / "features",
            "FEAT-FPSG5",
            _minimal_feature_body(),  # no smoke_gates block
        )

        feature = FeatureLoader.load_feature(
            "FEAT-FPSG5", repo_root=repo_with_tests
        )

        assert feature.smoke_gates is None

    def test_non_pytest_command_loads_cleanly(
        self, repo_with_tests: Path
    ) -> None:
        """Non-pytest command (parser returns ``[]``) → load succeeds.

        The validator must be specific to pytest paths. Custom smoke
        scripts (``python3 .guardkit/smoke/foo.py``) are out of scope —
        the parser returns ``[]`` and the validator does not run.
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        feature = FeatureLoader.load_feature(
            "FEAT-FPSG5", repo_root=repo_with_tests
        )

        assert feature.smoke_gates is not None
        assert "python3" in feature.smoke_gates.command


# ---------------------------------------------------------------------------
# Multi-line / shell-block-scalar regression
# ---------------------------------------------------------------------------


class TestMultilineCommandHandling:
    """The parser must work the same for ``set -e\\npytest ...`` blocks."""

    def test_multiline_pytest_block_with_missing_path(
        self, repo_with_tests: Path
    ) -> None:
        """Block scalar with bad pytest line still raises at load time."""
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        with pytest.raises(SmokeGatePathError) as exc_info:
            FeatureLoader.load_feature("FEAT-FPSG5", repo_root=repo_with_tests)

        assert "tests/cli" in str(exc_info.value)

    def test_multiple_positional_paths_one_missing(
        self, repo_with_tests: Path
    ) -> None:
        """Two positionals, one missing → only the missing one is reported."""
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        with pytest.raises(SmokeGatePathError) as exc_info:
            FeatureLoader.load_feature("FEAT-FPSG5", repo_root=repo_with_tests)

        message = str(exc_info.value)
        assert "tests/cli" in message
        # tests/forge exists and must NOT appear in the missing list. We
        # check it isn't called out as "non-existent" — it's fine for it
        # to appear under "Available test roots".
        assert "non-existent" in message
        # Crude but pinned: the path-list section must not name forge.
        # (The "Available test roots" line lists every existing root —
        # so we look only at the lines preceding it.)
        before_roots = message.split("Available test roots")[0]
        assert "tests/forge" not in before_roots


# ---------------------------------------------------------------------------
# Error-shape regression
# ---------------------------------------------------------------------------


class TestErrorTaxonomy:
    """Pin that ``SmokeGatePathError`` is a ``SchemaValidationError`` subtype.

    Existing pre-flight callers in the orchestrator catch
    ``SchemaValidationError`` (or its parent ``FeatureParseError``); this
    test guarantees we have not regressed that contract.
    """

    def test_smoke_gate_path_error_is_schema_validation_error(
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
            "FEAT-FPSG5",
            _minimal_feature_body(smoke),
        )

        with pytest.raises(SchemaValidationError):
            FeatureLoader.load_feature("FEAT-FPSG5", repo_root=repo_with_tests)


# ---------------------------------------------------------------------------
# Run-2-style failure-mode regression
# ---------------------------------------------------------------------------


def test_failure_surfaces_at_load_time_not_runtime(
    repo_with_tests: Path,
) -> None:
    """Pin that the failure happens at ``_parse_feature`` time, not at
    ``run_smoke_gate`` time.

    Pre-TASK-FPSG-005 behaviour: the orchestrator bootstrapped the
    worktree, ran Wave 1 (~17 min), then failed on the smoke gate.
    Post-TASK-FPSG-005 behaviour: the failure surfaces inside
    ``FeatureLoader.load_feature`` *before* the orchestrator does any
    expensive work.

    We pin this by asserting the exception is raised by ``load_feature``
    itself — no orchestrator, no worktree, no Wave 1.
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
        repo_with_tests / ".guardkit" / "features",
        "FEAT-FPSG5",
        _minimal_feature_body(smoke),
    )

    # No worktree, no run_smoke_gate call — load_feature alone must
    # raise. This is the regression contract.
    with pytest.raises(SmokeGatePathError):
        FeatureLoader.load_feature("FEAT-FPSG5", repo_root=repo_with_tests)
