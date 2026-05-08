"""Unit tests for TASK-FIX-CC-BDD: BDD glue file filtering in independent_tests.

The Coach's ``independent_tests`` path runs ``pytest <files>`` on whatever
test files appear in ``task_work_results.tests_written`` (and
``files_created`` / ``files_modified``). When one of those files is
pytest-bdd glue, pytest collects every scenario in the matching
``.feature`` file — including scenarios tagged for downstream peer tasks
that share the master feature. Their unbound steps surface as ``FAILED``
and the ``tests_passed`` / ``scenarios_failed > 0`` gates reject
deterministically.

Fix: ``coach_validator._filter_bdd_glue_files`` is applied to every test
file list before it is composed into a pytest invocation. BDD verification
is delegated to ``run_bdd_for_task`` (already task-tag scoped) via the
Player-side ``_run_bdd_oracle`` and the Coach's separate ``bdd_results``
gate.

Coverage Target: >=85%
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates.bdd_runner import is_bdd_glue_file
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_BDD_GLUE_BODY = """\
\"\"\"Auto-generated pytest-bdd glue.\"\"\"
from pytest_bdd import scenarios

scenarios("nats-fleet-integration.feature")
"""

_BDD_GLUE_BODY_VARIANT = """\
import pytest_bdd

pytest_bdd.scenarios("login.feature")
"""

_PLAIN_TEST_BODY = """\
def test_foo():
    assert True
"""


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "features").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# is_bdd_glue_file: detection helper
# ---------------------------------------------------------------------------


class TestIsBddGlueFile:
    def test_detects_pytest_bdd_scenarios_call(self, tmp_path: Path):
        f = tmp_path / "test_login.py"
        f.write_text(_BDD_GLUE_BODY)
        assert is_bdd_glue_file(f) is True

    def test_detects_import_pytest_bdd(self, tmp_path: Path):
        f = tmp_path / "test_signup.py"
        f.write_text(_BDD_GLUE_BODY_VARIANT)
        assert is_bdd_glue_file(f) is True

    def test_detects_from_pytest_bdd_when_no_scenarios_call(self, tmp_path: Path):
        f = tmp_path / "test_steps.py"
        f.write_text("from pytest_bdd import given, when, then\n")
        assert is_bdd_glue_file(f) is True

    def test_returns_false_for_plain_pytest_file(self, tmp_path: Path):
        f = tmp_path / "test_plain.py"
        f.write_text(_PLAIN_TEST_BODY)
        assert is_bdd_glue_file(f) is False

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        assert is_bdd_glue_file(tmp_path / "no_such.py") is False

    def test_returns_false_for_non_python_extension(self, tmp_path: Path):
        f = tmp_path / "fixture.feature"
        f.write_text("Feature: x\n")
        assert is_bdd_glue_file(f) is False

    def test_returns_false_for_directory(self, tmp_path: Path):
        d = tmp_path / "subdir"
        d.mkdir()
        assert is_bdd_glue_file(d) is False

    def test_returns_false_for_invalid_path_type(self):
        assert is_bdd_glue_file(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CoachValidator._filter_bdd_glue_files
# ---------------------------------------------------------------------------


class TestFilterBddGlueFiles:
    def test_passes_through_plain_files(self, worktree: Path):
        plain1 = worktree / "tests" / "test_plain.py"
        plain1.write_text(_PLAIN_TEST_BODY)
        plain2 = worktree / "tests" / "test_other.py"
        plain2.write_text(_PLAIN_TEST_BODY)

        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        result = validator._filter_bdd_glue_files(
            ["tests/test_plain.py", "tests/test_other.py"]
        )

        assert result == ["tests/test_plain.py", "tests/test_other.py"]

    def test_drops_pytest_bdd_glue_files(self, worktree: Path):
        # Replicates the FEAT-39E1 shape: one BDD glue file in features/<feat>/,
        # one plain unit test in tests/.
        bdd_dir = worktree / "features" / "nats-fleet-integration"
        bdd_dir.mkdir()
        bdd = bdd_dir / "test_nats_fleet_integration.py"
        bdd.write_text(_BDD_GLUE_BODY)
        plain = worktree / "tests" / "test_unit.py"
        plain.write_text(_PLAIN_TEST_BODY)

        validator = CoachValidator(
            worktree_path=str(worktree), task_id="TASK-NATS-PH1-006"
        )

        result = validator._filter_bdd_glue_files([
            "features/nats-fleet-integration/test_nats_fleet_integration.py",
            "tests/test_unit.py",
        ])

        assert result == ["tests/test_unit.py"]

    def test_returns_empty_list_when_all_files_are_bdd(self, worktree: Path):
        bdd_dir = worktree / "features" / "login"
        bdd_dir.mkdir()
        bdd = bdd_dir / "test_login.py"
        bdd.write_text(_BDD_GLUE_BODY)

        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        result = validator._filter_bdd_glue_files(["features/login/test_login.py"])

        assert result == []

    def test_preserves_order_of_plain_files(self, worktree: Path):
        a = worktree / "tests" / "test_a.py"
        a.write_text(_PLAIN_TEST_BODY)
        b = worktree / "tests" / "test_b.py"
        b.write_text(_PLAIN_TEST_BODY)
        bdd_dir = worktree / "features" / "x"
        bdd_dir.mkdir()
        c = bdd_dir / "test_x.py"
        c.write_text(_BDD_GLUE_BODY)

        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        result = validator._filter_bdd_glue_files([
            "tests/test_a.py",
            "features/x/test_x.py",
            "tests/test_b.py",
        ])

        assert result == ["tests/test_a.py", "tests/test_b.py"]

    def test_handles_missing_files_as_non_bdd(self, worktree: Path):
        # Files that don't exist are passed through (is_bdd_glue_file
        # returns False for missing paths). The downstream pytest invocation
        # will surface the missing file as a real failure, not silently
        # filter it out.
        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        result = validator._filter_bdd_glue_files(["tests/nonexistent.py"])

        assert result == ["tests/nonexistent.py"]


# ---------------------------------------------------------------------------
# Integration with _detect_tests_from_results: the FEAT-39E1 reproducer
# ---------------------------------------------------------------------------


class TestDetectTestsFromResultsBddFiltering:
    def test_bdd_glue_excluded_from_pytest_command(self, worktree: Path):
        """The defect: a BDD glue file in tests_written becomes a pytest arg.

        Reproduces the FEAT-39E1 turn-2 shape — ``tests_written`` includes a
        pytest-bdd glue file alongside plain unit tests. After the fix the
        BDD glue file MUST be excluded from the pytest command so peer-task
        scenarios are not collected as failures.
        """
        bdd_dir = worktree / "features" / "nats-fleet-integration"
        bdd_dir.mkdir()
        bdd = bdd_dir / "test_nats_fleet_integration.py"
        bdd.write_text(_BDD_GLUE_BODY)
        plain = worktree / "tests" / "unit"
        plain.mkdir()
        plain_test = plain / "test_serve_nats.py"
        plain_test.write_text(_PLAIN_TEST_BODY)

        validator = CoachValidator(
            worktree_path=str(worktree), task_id="TASK-NATS-PH1-006"
        )

        results = {
            "files_created": [
                "features/nats-fleet-integration/test_nats_fleet_integration.py",
                "tests/unit/test_serve_nats.py",
            ],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(results)

        assert cmd is not None
        assert "tests/unit/test_serve_nats.py" in cmd
        assert "test_nats_fleet_integration.py" not in cmd, (
            "BDD glue file leaked into pytest command — peer-task scenarios "
            "would surface as failures (TASK-FIX-CC-BDD)."
        )

    def test_returns_none_when_only_bdd_glue_present(self, worktree: Path):
        bdd_dir = worktree / "features" / "login"
        bdd_dir.mkdir()
        bdd = bdd_dir / "test_login.py"
        bdd.write_text(_BDD_GLUE_BODY)

        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        results = {
            "files_created": ["features/login/test_login.py"],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(results)

        # Only BDD glue → no plain pytest cmd needed; defer to bdd_results
        # gate which already enforces scenarios_failed == 0.
        assert cmd is None

    def test_unaffected_when_no_bdd_files_present(self, worktree: Path):
        # Backward-compat regression: tasks with only plain test files
        # behave exactly as before.
        plain_dir = worktree / "tests" / "unit"
        plain_dir.mkdir()
        a = plain_dir / "test_a.py"
        a.write_text(_PLAIN_TEST_BODY)
        b = plain_dir / "test_b.py"
        b.write_text(_PLAIN_TEST_BODY)

        validator = CoachValidator(worktree_path=str(worktree), task_id="TASK-001")

        results = {
            "files_created": [
                "tests/unit/test_a.py",
                "tests/unit/test_b.py",
            ],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(results)

        assert cmd is not None
        assert "tests/unit/test_a.py" in cmd
        assert "tests/unit/test_b.py" in cmd
        assert cmd.startswith("pytest ")
        assert cmd.endswith(" -v --tb=short")


# ---------------------------------------------------------------------------
# Regression test: pytest-bdd 3-state model (TASK-FIX-CC-BDD AC)
# ---------------------------------------------------------------------------


class TestPeerTaskScenariosNotSurfacedAsFailures:
    """The FEAT-39E1 fixture reproducer condensed to a unit test.

    Master feature carries scenarios for 9 different tasks. TASK-NATS-PH1-006
    owns one. Pre-fix: the unscoped pytest invocation collected all 30+
    scenarios; peer-task scenarios with unbound step definitions surfaced as
    FAILED. Post-fix: the BDD glue file is filtered out of the pytest cmd
    entirely; verification of TASK-NATS-PH1-006's scenarios is delegated to
    ``run_bdd_for_task`` (task-tag scoped via ``-m @task:TASK-NATS-PH1-006``)
    and the resulting ``bdd_results`` gate evaluates ``scenarios_failed == 0``.
    """

    def test_master_feature_with_multi_task_tags_does_not_pollute_pytest_cmd(
        self, worktree: Path
    ):
        # Multi-task master feature file
        feat = worktree / "features" / "nats-fleet-integration"
        feat.mkdir()
        (feat / "nats-fleet-integration.feature").write_text(
            "Feature: NATS Fleet\n\n"
            "  @task:TASK-NATS-PH1-006\n"
            "  Scenario: Owned\n"
            "    Given a registry\n\n"
            "  @task:TASK-NATS-PH2-001\n"
            "  Scenario: PeerA\n"
            "    Given an unbound step\n\n"
            "  @task:TASK-NATS-PH3-002\n"
            "  Scenario: PeerB\n"
            "    Given another unbound step\n"
        )
        (feat / "test_nats_fleet_integration.py").write_text(_BDD_GLUE_BODY)

        # Plain unit tests this task wrote
        unit_dir = worktree / "tests" / "unit"
        unit_dir.mkdir()
        (unit_dir / "test_serve_nats.py").write_text(_PLAIN_TEST_BODY)
        (unit_dir / "test_registry.py").write_text(_PLAIN_TEST_BODY)

        validator = CoachValidator(
            worktree_path=str(worktree), task_id="TASK-NATS-PH1-006"
        )

        results = {
            "files_created": [
                "features/nats-fleet-integration/test_nats_fleet_integration.py",
                "tests/unit/test_serve_nats.py",
                "tests/unit/test_registry.py",
            ],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(results)

        assert cmd is not None
        # Plain unit tests retained
        assert "tests/unit/test_serve_nats.py" in cmd
        assert "tests/unit/test_registry.py" in cmd
        # BDD glue excluded — peer-task scenarios cannot surface as failures
        assert "test_nats_fleet_integration.py" not in cmd
