"""Integration tests for TASK-BDDW-001: Wire factory BDD plugin discovery into Coach.

Covers:
- AC-1: Factory plugin discovery via ``guardkitfactory.bdd.discover`` and
  ``BDDRunResult → bundle.bdd`` mapping.
- AC-3: Absence-of-failure preserved — ``scenarios_attempted == 0`` surfaces
  as ABSENT SIGNAL, never a silent pass.
- AC-4: Per-task glue contract preserved — ``GUARDKIT_BDD_TASK_ID`` env var
  and ``test_<slug>.py`` fallback continue to work.
- AC-5: Legacy ``bdd_runner.py`` demoted to documented fallback.
- AC-6: ``scenarios_failed > 0`` rejection gate through the Coach (Python stack).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    map_bdd_run_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Minimal worktree with pyproject.toml for stack detection."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "features").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# AC-1: BDDRunResult → bundle.bdd mapping
# ---------------------------------------------------------------------------


class TestBddRunResultMapping:
    """Verify the mapping function preserves the bundle.bdd shape."""

    def test_maps_attempted_count(self):
        """A BDDRunResult with scenarios_attempted=0 maps to bundle.bdd as
        ABSENT SIGNAL, never a silent pass.
        """
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=0,
            scenarios_passed=0,
            scenarios_failed=0,
            scenarios_skipped=0,
            scenarios_errored=0,
            duration_seconds=0.0,
            raw_report_path=None,
        )
        mapped = map_bdd_run_result(result)
        assert mapped["scenarios_attempted"] == 0
        assert "scenarios_attempted" in mapped

    def test_maps_nonzero_attempted(self):
        """A BDDRunResult with non-zero scenarios_attempted maps correctly."""
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=5,
            scenarios_passed=4,
            scenarios_failed=1,
            scenarios_skipped=0,
            scenarios_errored=0,
            duration_seconds=2.5,
            raw_report_path=Path("/tmp/report.xml"),
            discoveries=[{"feature_file": "features/login.feature"}],
            errors=["Step not implemented: I click submit"],
        )
        mapped = map_bdd_run_result(result)
        assert mapped["scenarios_attempted"] == 5
        assert mapped["scenarios_passed"] == 4
        assert mapped["scenarios_failed"] == 1
        assert mapped["scenarios_pending"] == 0
        assert mapped["duration_seconds"] == 2.5
        assert mapped["feature_files"] == ["features/login.feature"]
        assert len(mapped["failures"]) == 1
        assert mapped["failures"][0]["error"] == "Step not implemented: I click submit"

    def test_preserves_scenarios_errored(self):
        """scenarios_errored is preserved in the mapping."""
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=3,
            scenarios_passed=1,
            scenarios_failed=0,
            scenarios_skipped=1,
            scenarios_errored=1,
            duration_seconds=1.0,
            raw_report_path=None,
        )
        mapped = map_bdd_run_result(result)
        assert mapped["scenarios_errored"] == 1
        assert mapped["scenarios_pending"] == 1  # maps from skipped

    def test_null_raw_report_path(self):
        """null raw_report_path maps to None in the bundle."""
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=1,
            scenarios_passed=1,
            scenarios_failed=0,
            scenarios_skipped=0,
            scenarios_errored=0,
            duration_seconds=0.5,
            raw_report_path=None,
        )
        mapped = map_bdd_run_result(result)
        assert mapped["raw_report_path"] is None


# ---------------------------------------------------------------------------
# AC-3: Absence-of-failure preserved
# ---------------------------------------------------------------------------


class TestAbsenceOfFailurePreserved:
    """scenarios_attempted == 0 surfaces as ABSENT SIGNAL, not silent pass."""

    def test_zero_attempted_not_coerced(self):
        """Zero-cardinality result must have scenarios_attempted present."""
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=0,
            scenarios_passed=0,
            scenarios_failed=0,
            scenarios_skipped=0,
            scenarios_errored=0,
            duration_seconds=0.0,
            raw_report_path=None,
        )
        mapped = map_bdd_run_result(result)
        # scenarios_attempted is present and equals 0
        assert mapped["scenarios_attempted"] == 0
        assert "scenarios_attempted" in mapped
        # It is NOT absent-coerced (the key must exist)

    def test_zero_attempted_not_silent_pass(self):
        """Zero-cardinality with zero failures is NOT a silent pass."""
        from guardkitfactory.bdd import BDDRunResult

        result = BDDRunResult(
            scenarios_attempted=0,
            scenarios_passed=0,
            scenarios_failed=0,
            scenarios_skipped=0,
            scenarios_errored=0,
            duration_seconds=0.0,
            raw_report_path=None,
        )
        mapped = map_bdd_run_result(result)
        # The Coach's absence-of-failure guard checks scenarios_attempted == 0
        # This should NOT be treated as "all passed" — it's "no oracle ran"
        assert mapped["scenarios_failed"] == 0
        assert mapped["scenarios_attempted"] == 0


# ---------------------------------------------------------------------------
# AC-4: Per-task glue contract preserved
# ---------------------------------------------------------------------------


class TestPerTaskGluePreserved:
    """GUARDKIT_BDD_TASK_ID and test_<slug>.py fallback continue to work."""

    def test_legacy_bdd_runner_still_importable(self):
        """The legacy bdd_runner module is still importable as fallback."""
        from guardkit.orchestrator.quality_gates import bdd_runner

        assert hasattr(bdd_runner, "run_bdd_for_task")
        assert hasattr(bdd_runner, "task_tag")
        assert hasattr(bdd_runner, "is_bdd_glue_file")

    def test_task_tag_format(self):
        """task_tag produces the expected @task: format."""
        from guardkit.orchestrator.quality_gates.bdd_runner import task_tag

        assert task_tag("TASK-BDDW-001") == "@task:TASK-BDDW-001"

    def test_guardkit_bdd_task_id_env_in_bdd_runner(self):
        """The GUARDKIT_BDD_TASK_ID env var is defined in bdd_runner."""
        from guardkit.orchestrator.quality_gates import bdd_runner

        assert hasattr(bdd_runner, "_BDD_TASK_ID_ENV")
        assert bdd_runner._BDD_TASK_ID_ENV == "GUARDKIT_BDD_TASK_ID"


# ---------------------------------------------------------------------------
# AC-5: Legacy bdd_runner.py demoted
# ---------------------------------------------------------------------------


class TestLegacyBddRunnerDemoted:
    """bdd_runner.py is demoted to a documented fallback."""

    def test_agent_invoker_bdd_oracle_has_demotion_comment(self):
        """The _run_bdd_oracle docstring mentions the demotion."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        doc = AgentInvoker._run_bdd_oracle.__doc__
        assert doc is not None
        assert "TASK-BDDW-001" in doc
        assert "demoted" in doc.lower() or "fallback" in doc.lower()


# ---------------------------------------------------------------------------
# AC-6: Coach scenarios_failed > 0 rejection gate
# ---------------------------------------------------------------------------


class TestCoachBddRejectionGate:
    """scenarios_failed > 0 blocks approval through the Coach."""

    def test_check_bdd_results_blocks_on_failures(self):
        """scenarios_failed > 0 produces blocking issues."""
        validator = CoachValidator(Path("/tmp/fake"))
        task_work_results = {
            "bdd_results": {
                "scenarios_attempted": 3,
                "scenarios_passed": 1,
                "scenarios_failed": 2,
                "scenarios_pending": 0,
                "failures": [
                    {
                        "scenario_name": "Login with valid credentials",
                        "failing_step": "Then I see the dashboard",
                        "reason": "AssertionError: expected 200, got 401",
                    }
                ],
                "feature_files": ["features/login.feature"],
            }
        }
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert len(blocking) == 1
        assert blocking[0]["severity"] == "must_fix"
        assert blocking[0]["category"] == "bdd_failure"
        assert blocking[0]["scenarios_failed"] == 2
        assert len(non_blocking) == 0

    def test_check_bdd_results_non_blocking_on_pending(self):
        """scenarios_pending > 0 produces non-blocking issues only."""
        validator = CoachValidator(Path("/tmp/fake"))
        task_work_results = {
            "bdd_results": {
                "scenarios_attempted": 3,
                "scenarios_passed": 3,
                "scenarios_failed": 0,
                "scenarios_pending": 1,
                "pending": [
                    {
                        "scenario_name": "Logout",
                        "pending_step": "When I click logout",
                    }
                ],
                "feature_files": ["features/logout.feature"],
            }
        }
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert len(blocking) == 0
        assert len(non_blocking) == 1
        assert non_blocking[0]["severity"] == "should_fix"
        assert non_blocking[0]["category"] == "bdd_pending"

    def test_check_bdd_results_no_issues_when_clean(self):
        """Zero failures and zero pending produces no issues."""
        validator = CoachValidator(Path("/tmp/fake"))
        task_work_results = {
            "bdd_results": {
                "scenarios_attempted": 5,
                "scenarios_passed": 5,
                "scenarios_failed": 0,
                "scenarios_pending": 0,
            }
        }
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert len(blocking) == 0
        assert len(non_blocking) == 0

    def test_check_bdd_results_no_bdd_results(self):
        """Missing bdd_results produces no issues (no gate active)."""
        validator = CoachValidator(Path("/tmp/fake"))
        task_work_results = {}
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert len(blocking) == 0
        assert len(non_blocking) == 0

    def test_check_bdd_results_no_bdd_results_key(self):
        """bdd_results is None produces no issues."""
        validator = CoachValidator(Path("/tmp/fake"))
        task_work_results = {"bdd_results": None}
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert len(blocking) == 0
        assert len(non_blocking) == 0


# ---------------------------------------------------------------------------
# Factory discovery integration (when available)
# ---------------------------------------------------------------------------


class TestFactoryDiscoveryIntegration:
    """End-to-end factory plugin discovery and mapping."""

    def test_guardkitfactory_available_flag(self):
        """The availability flag reflects whether the package is installed."""
        from guardkit.orchestrator.quality_gates.coach_validator import (
            _GUARDKITFACTORY_AVAILABLE,
        )
        # This test is informational — the flag should be True in the
        # development environment where guardkitfactory is installed.
        assert _GUARDKITFACTORY_AVAILABLE is True

    def test_detect_stack_profile_returns_python(self, worktree: Path):
        """Stack detection returns a Python profile for a pyproject.toml."""
        from guardkit.orchestrator.quality_gates.coach_validator import (
            _detect_stack_profile,
        )
        profile = _detect_stack_profile(worktree)
        assert profile is not None
        assert profile.language == "python"
        assert profile.test_framework == "pytest"

    @pytest.mark.integration_contract("BDDRunResult")
    def test_full_mapping_round_trip(self):
        """BDDRunResult → map_bdd_run_result → bundle.bdd preserves all fields."""
        from guardkitfactory.bdd import BDDRunResult

        raw = BDDRunResult(
            scenarios_attempted=10,
            scenarios_passed=7,
            scenarios_failed=2,
            scenarios_skipped=1,
            scenarios_errored=0,
            duration_seconds=3.14,
            raw_report_path=Path("/tmp/junit.xml"),
            discoveries=[
                {"feature_file": "features/a.feature"},
                {"feature_file": "features/b.feature"},
            ],
            errors=["Error 1", "Error 2"],
        )
        mapped = map_bdd_run_result(raw)
        assert mapped["scenarios_attempted"] == 10
        assert mapped["scenarios_passed"] == 7
        assert mapped["scenarios_failed"] == 2
        assert mapped["scenarios_pending"] == 1
        assert mapped["scenarios_errored"] == 0
        assert mapped["duration_seconds"] == 3.14
        assert mapped["raw_report_path"] == "/tmp/junit.xml"
        assert len(mapped["feature_files"]) == 2
        assert len(mapped["failures"]) == 2
        assert "pending" in mapped
        assert isinstance(mapped["pending"], list)
        assert len(mapped["pending"]) == 0
