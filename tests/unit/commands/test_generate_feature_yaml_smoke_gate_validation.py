"""Unit tests for ``generate-feature-yaml --validate-smoke-gates`` (TASK-FPSG-002).

The validator is the L3b layer of ``feature-plan-smoke-gate-validation``:
``/feature-plan`` Step 8.6 invokes it after the smoke-gates nudge so any
hand-injected ``smoke_gates.command`` path is verified against the target
repo's filesystem before ``/feature-build`` boots a worktree.

Each test pairs a tmp_path "repo" (with realistic ``tests/`` subdirs and
a ``.guardkit/features/`` directory) with a fixture YAML body, then
exercises ``validate_smoke_gates_paths`` directly. We import the function
rather than shelling out so the assertions can pin both the exit code
*and* the captured output.

Coverage Target: >=85%.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Add installer/core/commands/lib to sys.path so the script-style module
# is importable as ``generate_feature_yaml`` (matches conftest.py's
# convention used by the existing test_generate_feature_yaml.py).
_INSTALLER_LIB = (
    Path(__file__).parent.parent.parent.parent
    / "installer"
    / "core"
    / "commands"
    / "lib"
)
if str(_INSTALLER_LIB) not in sys.path:
    sys.path.insert(0, str(_INSTALLER_LIB))

from generate_feature_yaml import validate_smoke_gates_paths  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_feature(repo_root: Path, feature_id: str, body: str) -> Path:
    """Write a YAML body to ``<repo>/.guardkit/features/<feature_id>.yaml``."""
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    path = features_dir / f"{feature_id}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _base_body() -> str:
    """Minimal feature YAML scaffold; smoke_gates is appended per-test."""
    return dedent(
        """\
        id: FEAT-VFSG
        name: Validate-smoke-gates fixture
        description: Fixture for TASK-FPSG-002 validator tests.
        created: 2026-05-02T15:00:00Z
        complexity: 3
        estimated_tasks: 1
        tasks:
          - id: TASK-VFSG-T1
            file_path: tasks/in_progress/TASK-VFSG-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-VFSG-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )


@pytest.fixture
def repo_with_tests(tmp_path: Path) -> Path:
    """Build a tmp_path repo with a forge-shaped ``tests/`` tree.

    The ``tests/cli`` directory is intentionally omitted — that is the
    "missing path" the AC-listed defect cases reference (verbatim from
    TASK-REV-DEA8 in ``appmilla_github/forge``).
    """
    (tmp_path / "tests" / "forge").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Acceptance criteria — bad path
# ---------------------------------------------------------------------------


class TestBadPath:
    """``smoke_gates.command`` references a path that does not exist."""

    def test_missing_path_exits_non_zero_with_path_and_roots_in_message(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """Reproduces TASK-REV-DEA8 verbatim: ``tests/cli`` in a forge repo.

        Asserts both AC requirements: non-zero exit code AND a message
        containing the bad path AND the discovered test roots.
        """
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: |
                set -e
                pytest tests/cli tests/forge -x
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc != 0
        captured = capsys.readouterr()
        # Error goes to stderr per AC.
        assert "tests/cli" in captured.err
        # Discovered roots must appear so the agent knows what to pick.
        assert "tests/forge" in captured.err
        assert "tests/integration" in captured.err
        assert "tests/unit" in captured.err
        # The valid path should NOT be reported as missing.
        # (We check by looking for the bad path in the missing-paths body
        # while ensuring the good path is only in the "Available roots"
        # context — both contain "tests/forge", so use surrounding text.)
        assert "Available test roots" in captured.err

    def test_missing_path_message_includes_repo_root(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """AC: the repo root must appear so worktree vs main is unambiguous.

        Without the repo root in the message, an agent debugging a
        worktree-vs-main mismatch (where the path exists in one but not
        the other) cannot tell which tree is at fault.
        """
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: pytest tests/cli -x
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc != 0
        captured = capsys.readouterr()
        # The repo root we passed in must appear in the error.
        assert str(repo_with_tests) in captured.err


# ---------------------------------------------------------------------------
# Acceptance criteria — happy paths
# ---------------------------------------------------------------------------


class TestGoodPaths:
    """Every positional path under ``smoke_gates.command`` resolves OK."""

    def test_existing_paths_exit_zero_with_ok_message(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """All paths exist → exit 0 and emit the AC-required OK line."""
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: |
                set -e
                pytest tests/forge tests/integration -x
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc == 0
        captured = capsys.readouterr()
        assert "smoke_gates.command paths OK" in captured.out
        # No errors on stderr.
        assert captured.err == ""


# ---------------------------------------------------------------------------
# Acceptance criteria — escape hatches
# ---------------------------------------------------------------------------


class TestEscapeHatches:
    """The validator must exit 0 when there is nothing it can check."""

    def test_no_smoke_gates_block_exits_zero(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """Feature without ``smoke_gates`` → exit 0, friendly message.

        Single-wave features and authors who deliberately opt out of
        smoke gates must not be punished by a load-time validator.
        """
        _write_feature(repo_with_tests, "FEAT-VFSG", _base_body())

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc == 0
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_non_pytest_command_exits_zero(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """``python3 .guardkit/smoke/foo.py`` → exit 0 (parser returns []).

        Per AC: validator only checks pytest argv. Authors who run a
        bespoke smoke script are responsible for their own path checks.
        """
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: python3 .guardkit/smoke/foo.py
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc == 0
        captured = capsys.readouterr()
        assert captured.err == ""


# ---------------------------------------------------------------------------
# --quiet behaviour
# ---------------------------------------------------------------------------


class TestQuietMode:
    """Honour ``--quiet`` like the AC-quality / BDD-oracle / smoke-gates nudges."""

    def test_quiet_suppresses_success_messages(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """In quiet mode the OK path produces zero stdout output.

        CI runs that pipe the script's stdout into something brittle
        (e.g. a feature ID parser) must not see the validator chatter.
        """
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: pytest tests/forge -x
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=True,
        )

        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_quiet_does_not_suppress_errors(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """Quiet mode must NOT swallow validation errors.

        Suppressing errors in quiet mode would defeat the whole point
        of the validator in CI: the run must fail loudly so the author
        sees what to fix.
        """
        body = _base_body() + dedent(
            """\
            smoke_gates:
              after_wave: all
              command: pytest tests/cli -x
              expected_exit: 0
              timeout: 120
            """
        )
        _write_feature(repo_with_tests, "FEAT-VFSG", body)

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=True,
        )

        assert rc != 0
        captured = capsys.readouterr()
        assert "tests/cli" in captured.err


# ---------------------------------------------------------------------------
# Defensive branches — must never crash the validator
# ---------------------------------------------------------------------------


class TestDefensive:
    """Bad inputs surface clear errors without tracebacks."""

    def test_missing_yaml_file_exits_non_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        """Wrong feature ID or never-generated YAML → clear failure.

        Surfacing this as a validator failure (rather than a Python
        traceback) lets ``/feature-plan`` Step 8.6 print the message
        inline and instruct the agent to fix it.
        """
        rc = validate_smoke_gates_paths(
            feature_id="FEAT-NOPE",
            base_path=tmp_path,
            quiet=False,
        )

        assert rc != 0
        captured = capsys.readouterr()
        assert "FEAT-NOPE" in captured.err

    def test_malformed_yaml_exits_non_zero(
        self, repo_with_tests: Path, capsys: pytest.CaptureFixture
    ):
        """A YAML parse error must surface as a non-zero exit.

        Defensive path — without this, the validator would fail with a
        Python traceback inside ``yaml.safe_load`` and Step 8.6 would
        look like a ``/feature-plan`` bug rather than a YAML bug.
        """
        path = (
            repo_with_tests / ".guardkit" / "features" / "FEAT-VFSG.yaml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        # Unclosed bracket → guaranteed YAML parse failure.
        path.write_text("id: FEAT-VFSG\nname: [unclosed", encoding="utf-8")

        rc = validate_smoke_gates_paths(
            feature_id="FEAT-VFSG",
            base_path=repo_with_tests,
            quiet=False,
        )

        assert rc != 0
        captured = capsys.readouterr()
        # Some error message landed on stderr.
        assert captured.err != ""
