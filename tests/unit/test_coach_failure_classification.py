"""
Unit tests for infrastructure vs code test failure classification (TASK-PCTD-9BEB).

Tests the _classify_test_failure method and the classification
``gather_evidence`` attaches to the evidence bundle when the project's tests
ran and failed (it only shapes the words the Player is sent).

Coverage Target: >=90%
"""

from pathlib import Path
from unittest.mock import patch

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
# 3. The classification in the evidence bundle
# ============================================================================


class TestEvidenceBundleClassification:
    """gather_evidence attaches the classification of a red run."""

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

    def _gather(
        self, coach_validator: CoachValidator, test_result: IndependentTestResult
    ):
        with (
            patch.object(
                coach_validator, "read_quality_gate_results", return_value={},
            ),
            patch.object(
                coach_validator, "run_independent_tests",
                return_value=test_result,
            ),
        ):
            return coach_validator.gather_evidence(
                task_id="TASK-TEST-001",
                turn=1,
                task={"acceptance_criteria": ["AC-001: Feature works"]},
            )

    def test_infrastructure_failure_is_classified_in_the_bundle(
        self, coach_validator: CoachValidator
    ) -> None:
        """A ran-and-failed run with an infrastructure error is classified
        as infrastructure, with the output excerpt for the Player."""
        bundle = self._gather(coach_validator, self._make_infra_test_result())

        classification = bundle.independent_test_classification
        assert classification is not None
        assert classification.failure_class == "infrastructure"
        assert classification.confidence == "high"
        assert "ConnectionRefusedError" in classification.raw_output_excerpt

    def test_code_failure_is_classified_in_the_bundle(
        self, coach_validator: CoachValidator
    ) -> None:
        bundle = self._gather(coach_validator, self._make_code_test_result())

        classification = bundle.independent_test_classification
        assert classification is not None
        assert classification.failure_class == "code"
        assert classification.confidence == "n/a"

    def test_a_passing_run_is_not_classified(
        self, coach_validator: CoachValidator
    ) -> None:
        passed = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="5 passed",
            duration_seconds=1.0,
            raw_output="5 passed in 0.10s",
        )
        bundle = self._gather(coach_validator, passed)

        assert bundle.independent_test_classification is None
