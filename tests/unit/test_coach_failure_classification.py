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
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_assertion_error_classified_as_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """AssertionError in test output → code."""
        output = (
            "FAILED tests/test_calc.py::test_add\n"
            "E   AssertionError: assert 4 == 5\n"
            "1 failed in 0.12s"
        )
        assert coach_validator._classify_test_failure(output) == ("code", "n/a")

    def test_import_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """ImportError in test output → infrastructure (ambiguous)."""
        output = (
            "ImportError while importing test module 'tests/test_db.py'\n"
            "ImportError: No module named 'my_missing_package'"
        )
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "ambiguous")

    def test_module_not_found_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """ModuleNotFoundError for unknown lib in test output → infrastructure (ambiguous)."""
        output = "ModuleNotFoundError: No module named 'requests'"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "ambiguous")

    def test_module_not_found_known_service_client_promoted_to_high(
        self, coach_validator: CoachValidator
    ) -> None:
        """ModuleNotFoundError for known service-client lib → infrastructure (high)."""
        output = "ModuleNotFoundError: No module named 'sqlalchemy'"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_module_not_found_redis_promoted_to_high(
        self, coach_validator: CoachValidator
    ) -> None:
        """ModuleNotFoundError for redis → infrastructure (high confidence)."""
        output = "ModuleNotFoundError: No module named 'redis'"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_module_not_found_requests_remains_ambiguous(
        self, coach_validator: CoachValidator
    ) -> None:
        """ModuleNotFoundError for non-service-client lib stays ambiguous."""
        output = "ModuleNotFoundError: No module named 'requests'"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "ambiguous")

    def test_operational_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """sqlalchemy OperationalError → infrastructure (high confidence)."""
        output = (
            "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) "
            "could not connect to server: Connection refused\n"
            "Is the server running on host \"localhost\" and accepting "
            "TCP/IP connections on port 5432?"
        )
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_asyncpg_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """asyncpg connection error → infrastructure (high confidence)."""
        output = (
            "asyncpg.exceptions.ConnectionDoesNotExistError: "
            "connection was closed in the middle of operation"
        )
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_empty_output_returns_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """Empty string output → code (safe default)."""
        assert coach_validator._classify_test_failure("") == ("code", "n/a")

    def test_none_output_returns_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """None output → code (safe default)."""
        assert coach_validator._classify_test_failure(None) == ("code", "n/a")

    def test_case_insensitive_matching(
        self, coach_validator: CoachValidator
    ) -> None:
        """Pattern matching is case-insensitive."""
        output = "CONNECTIONREFUSEDERROR: connection refused"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_redis_connection_error_classified_as_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        """Redis connection error → infrastructure (high confidence)."""
        output = "redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_mixed_high_and_ambiguous_returns_high(
        self, coach_validator: CoachValidator
    ) -> None:
        """Mixed high-confidence + ambiguous patterns → high confidence wins.

        Uses sqlalchemy (a known service-client lib) as the missing module so
        that ModuleNotFoundError still returns high.  psycopg2 is intentionally
        NOT used here — after TASK-FIX-A7F1 it is no longer in
        _KNOWN_SERVICE_CLIENT_LIBS and produces ambiguous, not high.
        """
        output = (
            "ConnectionRefusedError: [Errno 111] Connection refused\n"
            "ModuleNotFoundError: No module named 'sqlalchemy'"
        )
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "high")

    def test_import_error_only_returns_ambiguous(
        self, coach_validator: CoachValidator
    ) -> None:
        """ImportError alone → ambiguous confidence."""
        output = "ImportError: cannot import name 'foo' from 'bar'"
        assert coach_validator._classify_test_failure(output) == ("infrastructure", "ambiguous")

    def test_assertion_error_only_returns_code(
        self, coach_validator: CoachValidator
    ) -> None:
        """AssertionError alone → code classification."""
        output = (
            "FAILED tests/test_math.py::test_add\n"
            "E   AssertionError: assert 4 == 5\n"
            "1 failed in 0.10s"
        )
        assert coach_validator._classify_test_failure(output) == ("code", "n/a")


# ============================================================================
# 2. _is_psycopg2_asyncpg_mismatch unit tests (TASK-FIX-4415)
# ============================================================================


class TestIsPsycopg2AsyncpgMismatch:
    """Unit tests for the _is_psycopg2_asyncpg_mismatch helper."""

    PSYCOPG2_OUTPUT = (
        "FAILED tests/test_db.py::test_connect\n"
        "ModuleNotFoundError: No module named 'psycopg2'\n"
    )

    def test_returns_true_for_psycopg2_error_with_asyncpg_in_requires_infrastructure(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            self.PSYCOPG2_OUTPUT,
            task={"requires_infrastructure": ["asyncpg"]},
        ) is True

    def test_returns_true_for_psycopg2_error_with_asyncpg_in_bootstrap_packages(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            self.PSYCOPG2_OUTPUT,
            task={"bootstrap_packages": ["asyncpg"]},
        ) is True

    def test_returns_false_when_no_asyncpg_signal(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            self.PSYCOPG2_OUTPUT,
            task={"requires_infrastructure": ["postgresql"]},
        ) is False

    def test_returns_false_when_task_is_none(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            self.PSYCOPG2_OUTPUT, task=None
        ) is False

    def test_returns_false_when_output_is_none(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            None, task={"requires_infrastructure": ["asyncpg"]}
        ) is False

    def test_returns_false_when_different_module_missing(
        self, coach_validator: CoachValidator
    ) -> None:
        output = "ModuleNotFoundError: No module named 'requests'\n"
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            output, task={"requires_infrastructure": ["asyncpg"]}
        ) is False

    def test_returns_true_for_sqlalchemy_asyncio_signal(
        self, coach_validator: CoachValidator
    ) -> None:
        assert coach_validator._is_psycopg2_asyncpg_mismatch(
            self.PSYCOPG2_OUTPUT,
            task={"requires_infrastructure": ["sqlalchemy[asyncio]"]},
        ) is True


# ============================================================================
# 3. IndependentTestResult raw_output field tests
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
        assert issue["failure_confidence"] == "high"
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

    def test_psycopg2_error_in_asyncpg_project_gives_specific_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """psycopg2 missing in asyncpg project → specific, actionable feedback (TASK-FIX-4415).

        When the task declares asyncpg as a dependency and psycopg2 is the
        missing module, the Coach must give a specific message directing the
        Player to remove the psycopg2 import.  The generic mock-fixtures /
        SQLite remediation options must NOT appear.
        """
        task_work_results = self._make_task_work_results()
        psycopg2_result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed - ModuleNotFoundError",
            duration_seconds=1.5,
            raw_output=(
                "FAILED tests/test_db.py::test_connect\n"
                "ModuleNotFoundError: No module named 'psycopg2'\n"
                "1 failed in 0.45s"
            ),
        )

        with (
            patch.object(
                coach_validator, "read_quality_gate_results",
                return_value=task_work_results,
            ),
            patch.object(
                coach_validator, "run_independent_tests",
                return_value=psycopg2_result,
            ),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["asyncpg"],
                },
            )

        assert result.decision == "feedback"
        assert len(result.issues) >= 1
        issue = result.issues[0]
        assert "psycopg2" in issue["description"]
        assert "asyncpg" in issue["description"]
        assert "Remove" in issue["description"]
        assert "mock fixtures" not in issue["description"]
        assert "SQLite" not in issue["description"]

    def test_psycopg2_error_without_asyncpg_project_uses_generic_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """psycopg2 missing with no asyncpg signal → generic infrastructure feedback (TASK-FIX-4415).

        When the project does not declare asyncpg, a missing psycopg2 module
        should NOT produce the asyncpg-specific message (AC4).
        """
        task_work_results = self._make_task_work_results()
        psycopg2_result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed - ModuleNotFoundError",
            duration_seconds=1.5,
            raw_output=(
                "FAILED tests/test_db.py::test_connect\n"
                "ModuleNotFoundError: No module named 'psycopg2'\n"
                "1 failed in 0.45s"
            ),
        )

        with (
            patch.object(
                coach_validator, "read_quality_gate_results",
                return_value=task_work_results,
            ),
            patch.object(
                coach_validator, "run_independent_tests",
                return_value=psycopg2_result,
            ),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    # No asyncpg in requires_infrastructure
                },
            )

        assert result.decision == "feedback"
        assert len(result.issues) >= 1
        issue = result.issues[0]
        # Must NOT contain the asyncpg-specific message
        assert "Remove `import psycopg2`" not in issue["description"]


# ============================================================================
# 4. Conditional approval tests (TASK-INFR-24DB)
# ============================================================================


class TestConditionalApproval:
    """Tests for infrastructure-aware conditional approval fallback (TASK-INFR-24DB)."""

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
        """Create a failed test result with high-confidence infrastructure error."""
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

    def test_high_confidence_infra_declared_deps_docker_unavailable_approves(
        self, coach_validator: CoachValidator
    ) -> None:
        """High-confidence infra + declared deps + Docker unavailable -> conditional approve."""
        task_work_results = self._make_task_work_results()
        infra_result = self._make_infra_test_result()

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=infra_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["postgresql"],
                    "_docker_available": False,
                },
            )

        assert result.decision == "approve"
        assert result.approved_without_independent_tests is True

    def test_high_confidence_infra_no_declared_deps_returns_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """High-confidence infra + no declared deps -> feedback (not approve)."""
        task_work_results = self._make_task_work_results()
        infra_result = self._make_infra_test_result()

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=infra_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": [],  # empty = not declared
                    "_docker_available": False,
                },
            )

        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_ambiguous_infra_declared_deps_returns_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """Ambiguous infra + declared deps -> feedback (not approve)."""
        task_work_results = self._make_task_work_results()
        # Use an ImportError with a non-high-confidence module name so that
        # classification returns ("infrastructure", "ambiguous"), not "high"
        ambiguous_result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed - ImportError",
            duration_seconds=1.0,
            raw_output="ImportError: No module named 'some_missing_package'",
        )

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=ambiguous_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["postgresql"],
                    "_docker_available": False,
                },
            )

        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_high_confidence_infra_docker_available_returns_feedback(
        self, coach_validator: CoachValidator
    ) -> None:
        """High-confidence infra + Docker available -> should not reach conditional approval."""
        task_work_results = self._make_task_work_results()
        infra_result = self._make_infra_test_result()

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=infra_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["postgresql"],
                    "_docker_available": True,  # Docker IS available
                },
            )

        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_gates_failed_no_conditional_approval(
        self, coach_validator: CoachValidator
    ) -> None:
        """Quality gates fail -> feedback (gates must pass for conditional approval)."""
        task_work_results = self._make_task_work_results()
        task_work_results["quality_gates"]["all_passed"] = False
        task_work_results["quality_gates"]["coverage"] = 50.0  # Below threshold

        infra_result = self._make_infra_test_result()

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=infra_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["postgresql"],
                    "_docker_available": False,
                },
            )

        # gates_status.all_gates_passed will be False, so it returns feedback from gates check
        # before even reaching the independent test check
        assert result.decision == "feedback"

    def test_conditional_approval_in_to_dict(
        self, coach_validator: CoachValidator
    ) -> None:
        """approved_without_independent_tests appears in to_dict output."""
        task_work_results = self._make_task_work_results()
        infra_result = self._make_infra_test_result()

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=infra_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                    "requires_infrastructure": ["postgresql"],
                    "_docker_available": False,
                },
            )

        result_dict = result.to_dict()
        assert "approved_without_independent_tests" in result_dict
        assert result_dict["approved_without_independent_tests"] is True

    def test_normal_approval_has_false_flag(
        self, coach_validator: CoachValidator
    ) -> None:
        """Normal approval (tests pass) has approved_without_independent_tests=False."""
        task_work_results = self._make_task_work_results()
        passing_result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="5 passed",
            duration_seconds=1.0,
        )

        with (
            patch.object(coach_validator, "read_quality_gate_results", return_value=task_work_results),
            patch.object(coach_validator, "run_independent_tests", return_value=passing_result),
        ):
            result = coach_validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001: Feature works"],
                },
            )

        assert result.decision == "approve"
        assert result.approved_without_independent_tests is False
