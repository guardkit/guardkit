"""
Unit tests for infrastructure vs code test failure classification (TASK-PCTD-9BEB).

Tests the _classify_test_failure method and its integration with the Coach
feedback path when independent test verification fails.

Coverage Target: >=90%
Test Count: 14 tests
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


@pytest.fixture
def coach_validator(tmp_path: Path) -> CoachValidator:
    """Create a CoachValidator instance for testing."""
    return CoachValidator(worktree_path=str(tmp_path))


# ============================================================================
# 1. _classify_test_failure unit tests
# ============================================================================


class TestClassifyTestFailure:
    """Tests for _classify_test_failure method."""

    def test_connection_refused_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """ConnectionRefusedError in test output → infrastructure."""
        output = (
            "FAILED tests/test_db.py::test_create_user\n"
            "E   ConnectionRefusedError: [Errno 111] Connection refused\n"
            "1 failed in 2.31s"
        )
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_assertion_error_classified_as_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """AssertionError in test output → code."""
        output = (
            "FAILED tests/test_calc.py::test_add\n"
            "E   AssertionError: assert 4 == 5\n"
            "1 failed in 0.12s"
        )
        assert coach_validator._classify_test_failure(output) == "code"

    def test_import_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """ImportError in test output → infrastructure."""
        output = (
            "ImportError while importing test module 'tests/test_db.py'\n"
            "ImportError: No module named 'psycopg2'"
        )
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_module_not_found_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """ModuleNotFoundError in test output → infrastructure."""
        output = "ModuleNotFoundError: No module named 'redis'"
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_operational_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """sqlalchemy OperationalError → infrastructure."""
        output = (
            "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) "
            "could not connect to server: Connection refused\n"
            "Is the server running on host \"localhost\" and accepting "
            "TCP/IP connections on port 5432?"
        )
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_asyncpg_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """asyncpg connection error → infrastructure."""
        output = (
            "asyncpg.exceptions.ConnectionDoesNotExistError: "
            "connection was closed in the middle of operation"
        )
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_empty_output_returns_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """Empty string output → code (safe default)."""
        assert coach_validator._classify_test_failure("") == "code"

    def test_none_output_returns_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """None output → code (safe default)."""
        assert coach_validator._classify_test_failure(None) == "code"

    def test_case_insensitive_matching(
        self, coach_validator: CoachValidator
    ) -> None:
        """Pattern matching is case-insensitive."""
        output = "CONNECTIONREFUSEDERROR: connection refused"
        assert coach_validator._classify_test_failure(output) == "infrastructure"

    def test_redis_connection_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """Redis connection error → infrastructure."""
        output = "redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379"
        assert coach_validator._classify_test_failure(output) == "infrastructure"


# ============================================================================
# 2. IndependentTestResult raw_output field tests
# ============================================================================


class TestIndependentTestResultRawOutput:
    """Tests for the raw_output field on IndependentTestResult."""

    def test_raw_output_defaults_to_none(self) -> None:
        """raw_output defaults to None for backward compatibility."""
        result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="5 passed",
            duration_seconds=1.0,
        )
        assert result.raw_output is None

    def test_raw_output_can_be_set(self) -> None:
        """raw_output can be explicitly set."""
        result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed",
            duration_seconds=2.0,
            raw_output="ConnectionRefusedError: [Errno 111] Connection refused",
        )
        assert result.raw_output == "ConnectionRefusedError: [Errno 111] Connection refused"


# ============================================================================
# 3. Feedback path integration tests
# ============================================================================


class TestFeedbackPathClassification:
    """Tests verifying the feedback path produces correct messages."""

    def _make_task_work_results(self) -> Dict[str, Any]:
        """Create minimal task_work_results that pass quality gates."""
        return {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 10,
                "tests_failed": 0,
                "coverage": 85.0,
                "branch_coverage": 80.0,
            },
            "code_review": {"score": 80},
            "plan_audit": {"violations": 0},
            "requirements_met": ["AC-001: Feature works"],
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "criterion_text": "Feature works",
                    "status": "complete",
                    "evidence": "Tests pass",
                },
            ],
        }

    def _make_infra_test_result(self) -> IndependentTestResult:
        """Create a failed test result with infrastructure error."""
        return IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed - ConnectionRefusedError",
            duration_seconds=3.0,
            raw_output=(
                "FAILED tests/test_db.py::test_create_user\n"
                "E   ConnectionRefusedError: [Errno 111] Connection refused\n"
                "1 failed in 2.31s"
            ),
        )

    def _make_code_test_result(self) -> IndependentTestResult:
        """Create a failed test result with code error."""
        return IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed - assert 4 == 5",
            duration_seconds=1.0,
            raw_output=(
                "FAILED tests/test_calc.py::test_add\n"
                "E   AssertionError: assert 4 == 5\n"
                "1 failed in 0.12s"
            ),
        )

    def test_infrastructure_failure_produces_actionable_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """Infrastructure failure produces feedback with remediation options."""
        task_work_results = self._make_task_work_results()
        infra_result = self._make_infra_test_result()

        with (
            patch.object(
                coach_validator, "read_quality_gate_results",
                return_value=task_work_results,
            ),
            patch.object(
                coach_validator, "run_independent_tests",
                return_value=infra_result,
            ),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                },
            )

        assert result.decision == "feedback"
        assert len(result.issues) >= 1
        issue = result.issues[0]
        assert issue["failure_classification"] == "infrastructure"
        assert "mock fixtures" in issue["description"]
        assert "SQLite" in issue["description"]
        assert "infrastructure" in result.rationale

    def test_code_failure_produces_standard_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """Code failure produces standard feedback without remediation options."""
        task_work_results = self._make_task_work_results()
        code_result = self._make_code_test_result()

        with (
            patch.object(
                coach_validator, "read_quality_gate_results",
                return_value=task_work_results,
            ),
            patch.object(
                coach_validator, "run_independent_tests",
                return_value=code_result,
            ),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                },
            )

        assert result.decision == "feedback"
        assert len(result.issues) >= 1
        issue = result.issues[0]
        assert issue["failure_classification"] == "code"
        assert issue["description"] == "Independent test verification failed"
        assert "infrastructure" not in result.rationale
