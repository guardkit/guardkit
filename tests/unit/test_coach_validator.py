"""
Unit tests for CoachValidator: the project's own test run and the evidence
it gathers for the reviewer.

Tests cover:
    - IndependentTestVerification: Independent test execution
    - Test command detection (task-specific, recursive glob, task-work
      results, cumulative diff, prior Player reports, collect_ignore_glob)
    - Task type resolution and the profile's tests_required in gather_evidence
    - Test failure classification
    - The SDK / harness test-execution path and its debug preservation
"""

import json
import os
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory for a PYTHON project.

    TS-lane D.1b: the ``pyproject.toml`` marker is now written explicitly.
    Until the unconditional ``"Could not detect project type, defaulting to
    pytest"`` fallback was deleted, an EMPTY directory silently produced
    ``pytest tests/ -v --tb=short`` — so 14 tests in this file that are about
    timeouts, summaries and gate profiles were riding a stack guess they never
    asked for and never asserted. The marker states the assumption those tests
    always had, and keeps their resolved command byte-identical to before.
    """
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    (worktree / "pyproject.toml").touch()
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree):
    """Create the task-work results directory."""
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def make_task_work_results(
    tests_passed: bool = True,
    failed_count: int = 0,
    total_tests: int = 15,
    coverage_met: bool = True,
    line_coverage: int = 85,
    arch_score: int = 82,
    violations: int = 0,
    requirements_met: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Helper to create task-work results matching actual writer schema."""
    # If tests_passed is False, we need to set failed_count if it's 0
    # This ensures the schema reflects the actual failure state
    if not tests_passed and failed_count == 0:
        failed_count = 1  # Set to at least 1 to indicate failure

    passed_count = total_tests - failed_count
    return {
        # Quality gates object (what writer actually creates)
        "quality_gates": {
            "tests_passing": tests_passed and failed_count == 0,
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "coverage": line_coverage,
            "coverage_met": coverage_met,
            "all_passed": tests_passed and coverage_met,
        },
        # Code review (separate from quality_gates)
        "code_review": {
            "score": arch_score,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        # Plan audit (separate from quality_gates)
        "plan_audit": {
            "violations": violations,
            "file_count_match": True,
        },
        "requirements_met": requirements_met if requirements_met is not None else [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def make_task(acceptance_criteria: Optional[List[str]] = None) -> Dict[str, Any]:
    """Helper to create task data."""
    return {
        "acceptance_criteria": acceptance_criteria or [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def write_task_work_results(results_dir: Path, results: Dict[str, Any]):
    """Helper to write task-work results to file."""
    results_path = results_dir / "task_work_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    return results_path


# ============================================================================
# Test Independent Test Verification
# ============================================================================


class TestIndependentTestVerification:
    """Test independent test running."""

    def test_run_tests_success(self, tmp_worktree):
        """Test successful independent test run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
            result = validator.run_independent_tests()

        assert result.tests_passed is True
        assert "passed" in result.test_output_summary.lower()
        assert result.duration_seconds > 0

    def test_run_tests_failure(self, tmp_worktree):
        """Test failed independent test run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="13 passed, 2 failed in 2.3s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

    def test_run_tests_timeout(self, tmp_worktree):
        """Test test execution timeout."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)

            validator = CoachValidator(
                str(tmp_worktree),
                test_timeout=300,
                toolchain=ToolchainDeclaration(test="make test"),
            )
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()

    def test_run_tests_exception(self, tmp_worktree):
        """Test test execution exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command not found")

            validator = CoachValidator(str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test"))
            result = validator.run_independent_tests()

        # The command did not start, so the check could not run (1 November
        # 2026; it was recorded as no test signal).
        assert result.tests_passed is False
        assert result.check_could_not_run is True
        assert "could not start" in result.test_output_summary

    def test_run_tests_uses_custom_command(self, tmp_worktree):
        """Test custom test command is used."""
        custom_cmd = "make test-all"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree), test_command=custom_cmd)
            result = validator.run_independent_tests()

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == custom_cmd
        assert result.test_command == custom_cmd

    @pytest.mark.parametrize("marker", ["pyproject.toml", "package.json", "Example.csproj"])
    def test_nothing_declared_runs_no_guessed_command(self, tmp_worktree, marker):
        """31 October 2026: a marker file is not a declaration. Nothing runs,
        and the check could not run, saying so."""
        (tmp_worktree / marker).touch()

        with patch("subprocess.run") as mock_run:
            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        mock_run.assert_not_called()
        assert result.test_command == "<nothing declared>"
        assert result.check_could_not_run is True
        assert result.tests_passed is False


# ============================================================================
# Test Dataclasses
# ============================================================================


class TestDataclasses:
    """Test dataclass initialization and behavior."""

    def test_independent_test_result_fields(self):
        """Test IndependentTestResult has expected fields."""
        result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="15 passed in 1.45s",
            duration_seconds=1.45,
        )

        assert result.tests_passed is True
        assert result.test_command == "pytest tests/ -v"
        assert result.test_output_summary == "15 passed in 1.45s"
        assert result.duration_seconds == 1.45


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestCoachValidatorHelpers:
    """Test CoachValidator helper methods."""

    def test_summarize_test_output_truncates(self, tmp_worktree):
        """Test _summarize_test_output truncates long output."""
        validator = CoachValidator(str(tmp_worktree))

        long_output = "line\n" * 1000 + "15 passed in 1.45s"

        summary = validator._summarize_test_output(long_output, max_length=100)

        assert len(summary) <= 100

    def test_summarize_test_output_extracts_summary(self, tmp_worktree):
        """Test _summarize_test_output extracts test summary lines."""
        validator = CoachValidator(str(tmp_worktree))

        output = """
tests/test_one.py::test_example PASSED
tests/test_two.py::test_other PASSED
================
15 passed, 2 failed in 2.34s
================
"""

        summary = validator._summarize_test_output(output)

        assert "passed" in summary.lower()
        assert "failed" in summary.lower()


# ============================================================================
# Test Integration with AutoBuild
# ============================================================================


class TestAutoBuildIntegration:
    """Test CoachValidator integration with AutoBuild orchestrator."""

    def test_validator_can_be_instantiated(self, tmp_worktree):
        """Test CoachValidator can be instantiated."""
        validator = CoachValidator(str(tmp_worktree))

        assert hasattr(validator, "gather_evidence")
        assert hasattr(validator, "read_quality_gate_results")
        assert hasattr(validator, "run_independent_tests")

    def test_validator_returns_expected_type(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test gather_evidence returns a CoachEvidenceBundle."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.gather_evidence("TASK-001", 1, make_task())

        assert isinstance(result, CoachEvidenceBundle)
        assert result.gathering_status == "complete"
        assert result.independent_tests is not None
        assert result.task_type == "feature"

    def test_validator_result_can_serialize_to_json(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test the evidence bundle can be serialized to JSON."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.gather_evidence("TASK-001", 1, make_task())

        # Should not raise
        d = result.to_dict()
        json_str = json.dumps(d)

        assert len(json_str) > 0
        assert '"independent_tests"' in json_str


# ============================================================================
# Test Task Type Profile Support (TASK-FBSDK-021)
# ============================================================================


class TestTaskTypeProfileResolution:
    """Test task type resolution from task metadata."""

    def test_resolve_task_type_default_no_type_specified(self, tmp_worktree):
        """Test default resolution when no task_type specified."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.FEATURE

    def test_resolve_task_type_scaffolding(self, tmp_worktree):
        """Test resolution of scaffolding task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "scaffolding", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.SCAFFOLDING

    def test_resolve_task_type_feature(self, tmp_worktree):
        """Test resolution of feature task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "feature", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.FEATURE

    def test_resolve_task_type_infrastructure(self, tmp_worktree):
        """Test resolution of infrastructure task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "infrastructure", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.INFRASTRUCTURE

    def test_resolve_task_type_documentation(self, tmp_worktree):
        """Test resolution of documentation task type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "documentation", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.DOCUMENTATION

    def test_resolve_task_type_integration(self, tmp_worktree):
        """AC-010: _resolve_task_type accepts 'integration' as valid task_type."""
        from guardkit.models.task_types import TaskType

        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "integration", "acceptance_criteria": []}

        task_type = validator._resolve_task_type(task)

        assert task_type == TaskType.INTEGRATION

    def test_resolve_task_type_invalid(self, tmp_worktree):
        """Test error handling for invalid task_type."""
        validator = CoachValidator(str(tmp_worktree))
        task = {"task_type": "invalid_type", "acceptance_criteria": []}

        with pytest.raises(ValueError) as exc_info:
            validator._resolve_task_type(task)

        assert "Invalid task_type value" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)


class TestQualityGateProfileApplication:
    """The task type no longer decides whether the tests run (31 October
    2026): the parts the task changed do."""

    @pytest.mark.parametrize("task_type", ["scaffolding", "feature", "documentation"])
    def test_every_task_type_runs_the_changed_parts_tests(
        self, tmp_worktree, task_work_results_dir, task_type
    ):
        results = make_task_work_results(tests_passed=True)
        results["files_modified"] = ["src/app.py"]
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")
            validator = CoachValidator(
                str(tmp_worktree), toolchain=ToolchainDeclaration(test="make test")
            )
            result = validator.gather_evidence(
                "TASK-001", 1, {"task_type": task_type, "acceptance_criteria": []}
            )

        mock_run.assert_called_once()
        assert result.independent_tests.test_command == "make test"
        assert result.independent_tests.tests_passed is True


# ============================================================================
# Test _classify_test_failure — psycopg2 misclassification fix (TASK-FIX-A7F1)
# ============================================================================


class TestClassifyTestFailurePsycopg2:
    """Tests for the psycopg2 misclassification fix in _classify_test_failure.

    Source: TASK-FIX-A7F1 — finding F2 from TASK-REV-7EB05.
    """

    def test_psycopg2_module_not_found_no_context_is_ambiguous(self, tmp_worktree):
        """AC2: psycopg2 ModuleNotFoundError with no bootstrap context → ambiguous.

        Previously classified as ("infrastructure", "high"), which gave the
        Player wrong advice (mock fixtures / SQLite) instead of telling them to
        remove the wrong import.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'psycopg2'\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "ambiguous"), (
            f"Expected ('infrastructure', 'ambiguous'), got {result!r}. "
            "psycopg2 ModuleNotFoundError without bootstrap context should not "
            "trigger conditional approval."
        )

    def test_psycopg2_module_not_found_with_bootstrap_context_is_code_error(
        self, tmp_worktree
    ):
        """AC3: psycopg2 ModuleNotFoundError + bootstrap context → code error.

        When the task declares infrastructure requirements (e.g. postgresql),
        a missing psycopg2 import is a Player code-choice error — they should
        be using asyncpg, not psycopg2.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'psycopg2'\n"
        )

        result = validator._classify_test_failure(
            output, requires_infrastructure=["postgresql"]
        )

        assert result == ("code", "high"), (
            f"Expected ('code', 'high'), got {result!r}. "
            "psycopg2 missing when bootstrap declares postgresql means the "
            "Player chose the wrong driver."
        )

    def test_asyncpg_module_not_found_is_infrastructure_high(self, tmp_worktree):
        """AC5: asyncpg ModuleNotFoundError → ('infrastructure', 'high').

        asyncpg remains in _KNOWN_SERVICE_CLIENT_LIBS so its absence is
        treated as a genuine infra/env issue regardless of bootstrap context.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'asyncpg'\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "asyncpg missing is a genuine infra dep issue."
        )

    def test_asyncpg_module_not_found_with_bootstrap_still_infrastructure(
        self, tmp_worktree
    ):
        """AC5: asyncpg missing + bootstrap context → still infrastructure high.

        asyncpg is the correct driver for the project (it's in
        _KNOWN_SERVICE_CLIENT_LIBS), so bootstrap context does not change the
        classification.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "FAILED tests/test_db.py::test_connect\n"
            "ModuleNotFoundError: No module named 'asyncpg'\n"
        )

        result = validator._classify_test_failure(
            output, requires_infrastructure=["postgresql"]
        )

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "asyncpg is the expected driver — bootstrap context should not "
            "downgrade to code error."
        )

    def test_psycopg2_connection_error_still_infrastructure_high(
        self, tmp_worktree
    ):
        """psycopg2 connection errors (not ModuleNotFoundError) remain high.

        When psycopg2 IS installed but the DB is unreachable, the error
        contains e.g. 'psycopg2.OperationalError' which should still be
        classified as infrastructure/high via _INFRA_HIGH_CONFIDENCE.
        """
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "psycopg2.OperationalError: could not connect to server: "
            "Connection refused\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("infrastructure", "high"), (
            f"Expected ('infrastructure', 'high'), got {result!r}. "
            "A psycopg2 connection error (DB unreachable) is a genuine "
            "infrastructure failure."
        )

    def test_psycopg2_not_in_known_service_client_libs(self, tmp_worktree):
        """AC1: psycopg2 is no longer in _KNOWN_SERVICE_CLIENT_LIBS."""
        validator = CoachValidator(str(tmp_worktree))

        assert "psycopg2" not in validator._KNOWN_SERVICE_CLIENT_LIBS, (
            "psycopg2 must be removed from _KNOWN_SERVICE_CLIENT_LIBS to prevent "
            "ModuleNotFoundError from being auto-promoted to high confidence."
        )


# ============================================================================
# Test _classify_test_failure — SDK API error classification (TASK-FIX-d5e6)
# ============================================================================


class TestClassifyTestFailureSdkApiError:
    """Tests for SDK API error pattern matching in _classify_test_failure.

    Source: TASK-FIX-d5e6 — from TASK-REV-ED10.
    """

    def test_sdk_api_error_classified_correctly(self, tmp_worktree):
        """SDK API error: invalid_request → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = (
            "Error: SDK API error: invalid_request\n"
            "The model name is not valid for this endpoint.\n"
        )

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}. "
            "SDK API error should be classified as sdk_api_error, not code."
        )

    def test_invalid_request_error_classified(self, tmp_worktree):
        """invalid_request_error pattern → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = "anthropic.BadRequestError: invalid_request_error: model not found"

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}."
        )

    def test_assistant_message_error_classified(self, tmp_worktree):
        """AssistantMessage.error pattern → ('sdk_api_error', 'high')."""
        validator = CoachValidator(str(tmp_worktree))
        output = "AssistantMessage.error: The request was rejected by the API"

        result = validator._classify_test_failure(output)

        assert result == ("sdk_api_error", "high"), (
            f"Expected ('sdk_api_error', 'high'), got {result!r}."
        )

    def test_unrelated_error_not_classified_as_sdk(self, tmp_worktree):
        """Unrelated test failure should NOT match SDK API error patterns."""
        validator = CoachValidator(str(tmp_worktree))
        output = "AssertionError: expected 5, got 3"

        result = validator._classify_test_failure(output)

        assert result == ("code", "n/a"), (
            f"Expected ('code', 'n/a'), got {result!r}. "
            "Non-SDK errors should fall through to code classification."
        )


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
