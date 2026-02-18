"""
Unit tests for CoachValidator lightweight task-work result validation.

Tests cover:
    - CoachValidator: Main validation flow and decision-making
    - QualityGateVerification: Reading and verifying task-work results
    - IndependentTestVerification: Independent test execution
    - RequirementsValidation: Acceptance criteria checking
    - Dataclasses: Data model initialization and behavior

Test Organization:
    - TestCoachValidator: Main validation tests
    - TestQualityGateVerification: Quality gate result verification
    - TestIndependentTestVerification: Independent test running
    - TestRequirementsValidation: Acceptance criteria validation
    - TestDataclasses: Dataclass behavior tests
    - TestCoachValidatorHelpers: Helper method tests
"""

import json
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
    CoachValidationResult,
    CriterionResult,
    QualityGateStatus,
    IndependentTestResult,
    RequirementsValidation,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
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
# Test CoachValidator
# ============================================================================


class TestCoachValidator:
    """Test CoachValidator main validation flow."""

    def test_validate_approves_when_all_gates_pass(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test approve decision when all quality gates pass."""
        # Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Mock subprocess to return successful test run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "approve"
        assert result.quality_gates.all_gates_passed is True
        assert result.independent_tests.tests_passed is True
        assert result.requirements.all_criteria_met is True
        assert len(result.issues) == 0
        assert "passed" in result.rationale.lower()

    def test_validate_feedback_when_tests_failed_in_task_work(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback decision when task-work tests failed."""
        # Write failing task-work results
        results = make_task_work_results(tests_passed=False, failed_count=2)
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates.tests_passed is False
        assert result.quality_gates.all_gates_passed is False
        assert len(result.issues) >= 1
        assert result.issues[0]["category"] == "test_failure"
        assert result.issues[0]["severity"] == "must_fix"

    def test_validate_feedback_when_arch_score_low(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback decision when architectural score is below threshold."""
        # Write results with low arch score
        results = make_task_work_results(arch_score=45)
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates.arch_review_passed is False
        assert result.quality_gates.all_gates_passed is False
        assert any(
            issue["category"] == "architectural"
            for issue in result.issues
        )

    def test_validate_feedback_when_coverage_not_met(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback decision when coverage threshold not met."""
        results = make_task_work_results(coverage_met=False, line_coverage=65)
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates.coverage_met is False
        assert any(
            issue["category"] == "coverage"
            for issue in result.issues
        )

    def test_validate_feedback_when_plan_audit_violations(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback decision when plan audit has violations."""
        results = make_task_work_results(violations=3)
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates.plan_audit_passed is False
        assert any(
            issue["category"] == "plan_audit"
            for issue in result.issues
        )

    def test_validate_feedback_when_independent_tests_fail(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback when independent test verification fails."""
        # Task-work results show tests passed
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # But independent tests fail
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="13 passed, 2 failed",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates.all_gates_passed is True  # task-work passed
        assert result.independent_tests.tests_passed is False  # independent failed
        assert any(
            issue["category"] == "test_verification"
            for issue in result.issues
        )
        assert "independent" in result.rationale.lower()

    def test_validate_feedback_when_requirements_missing(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback when not all acceptance criteria met."""
        # Task has 4 criteria, but only 2 are met
        results = make_task_work_results(
            requirements_met=["OAuth2 authentication flow", "Token generation"]
        )
        write_task_work_results(task_work_results_dir, results)

        task = make_task([
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
            "Rate limiting",
        ])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, task)

        assert result.decision == "feedback"
        assert result.requirements.all_criteria_met is False
        assert result.requirements.criteria_total == 4
        assert result.requirements.criteria_met == 2
        assert "Token refresh" in result.requirements.missing
        assert "Rate limiting" in result.requirements.missing
        assert any(
            issue["category"] == "missing_requirement"
            for issue in result.issues
        )

    def test_validate_feedback_when_results_not_found(
        self,
        tmp_worktree,
    ):
        """Test feedback when task-work results file doesn't exist."""
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert result.quality_gates is None
        assert any(
            issue["category"] == "missing_results"
            for issue in result.issues
        )
        assert "not found" in result.rationale.lower()

    def test_validate_handles_malformed_json(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test feedback when task-work results file has invalid JSON."""
        results_path = task_work_results_dir / "task_work_results.json"
        with open(results_path, "w") as f:
            f.write("{ invalid json }")

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, make_task())

        assert result.decision == "feedback"
        assert any(
            "parse" in issue.get("description", "").lower()
            for issue in result.issues
        )


    def test_validate_with_context_includes_context_used_in_result(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that validate() with context includes context_used in result."""
        # Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Mock subprocess to return successful test run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            test_context = "some architecture context about patterns and services"
            result = validator.validate("TASK-001", 1, make_task(), context=test_context)

        assert result.context_used == test_context
        assert "Architecture context:" in result.rationale

    def test_validate_with_context_none_is_backward_compatible(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that validate() with context=None is backward compatible."""
        # Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Mock subprocess to return successful test run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task(), context=None)

        assert result.context_used is None
        assert "Architecture context:" not in result.rationale

    def test_validate_with_empty_context_treated_as_no_context(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that validate() with context="" treated as no context."""
        # Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Mock subprocess to return successful test run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task(), context="")

        assert result.context_used == ""
        assert "Architecture context:" not in result.rationale

    def test_to_dict_includes_context_used_field(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that to_dict() includes context_used field."""
        # Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Mock subprocess to return successful test run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            test_context = "test context for validation"
            result = validator.validate("TASK-001", 1, make_task(), context=test_context)

        result_dict = result.to_dict()
        assert "context_used" in result_dict
        assert result_dict["context_used"] == test_context


# ============================================================================
# Test Quality Gate Verification
# ============================================================================


class TestQualityGateVerification:
    """Test quality gate status verification."""

    def test_verify_all_gates_passing(self, tmp_worktree):
        """Test all gates pass scenario."""
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results()

        status = validator.verify_quality_gates(results)

        assert status.tests_passed is True
        assert status.coverage_met is True
        assert status.arch_review_passed is True
        assert status.plan_audit_passed is True
        assert status.all_gates_passed is True

    def test_verify_tests_failed(self, tmp_worktree):
        """Test detection of test failure."""
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(tests_passed=False)

        status = validator.verify_quality_gates(results)

        assert status.tests_passed is False
        assert status.all_gates_passed is False

    def test_verify_coverage_not_met(self, tmp_worktree):
        """Test detection of coverage failure."""
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(coverage_met=False)

        status = validator.verify_quality_gates(results)

        assert status.coverage_met is False
        assert status.all_gates_passed is False

    @pytest.mark.parametrize("score,expected", [
        (60, True),   # At threshold - passes
        (59, False),  # Below threshold - fails
        (80, True),   # Above threshold - passes
        (0, False),   # Zero score - fails
        (100, True),  # Perfect score - passes
    ])
    def test_verify_arch_review_threshold(self, tmp_worktree, score, expected):
        """Test architectural review score threshold (60)."""
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(arch_score=score)

        status = validator.verify_quality_gates(results)

        assert status.arch_review_passed is expected

    @pytest.mark.parametrize("violations,expected", [
        (0, True),   # No violations - passes
        (1, False),  # One violation - fails
        (5, False),  # Multiple violations - fails
    ])
    def test_verify_plan_audit_violations(self, tmp_worktree, violations, expected):
        """Test plan audit violation detection."""
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(violations=violations)

        status = validator.verify_quality_gates(results)

        assert status.plan_audit_passed is expected

    def test_verify_handles_missing_fields(self, tmp_worktree):
        """Test graceful handling of missing fields in results."""
        validator = CoachValidator(str(tmp_worktree))
        results = {}  # Empty results

        status = validator.verify_quality_gates(results)

        # Should use defaults: tests_passed=False, coverage_met=True
        assert status.tests_passed is False
        assert status.coverage_met is True  # Default when not present
        assert status.arch_review_passed is False  # Score 0 < 60
        assert status.plan_audit_passed is True  # 0 violations default

    def test_verify_handles_partial_results(self, tmp_worktree):
        """Test handling of partial results."""
        validator = CoachValidator(str(tmp_worktree))
        results = {
            "quality_gates": {"all_passed": True},
            # Include code_review to make arch review pass
            "code_review": {"score": 82},
        }

        status = validator.verify_quality_gates(results)

        assert status.tests_passed is True
        assert status.coverage_met is True  # Default
        assert status.arch_review_passed is True  # Has code_review.score = 82

    def test_verify_coverage_none_treated_as_pass(self, tmp_worktree):
        """Test that coverage_met=None is treated as pass (not measured).

        When task-work writes coverage_met=null (Python None) to task_work_results.json,
        this means coverage data wasn't collected. We should treat this as "not measured"
        and allow the gate to pass, rather than failing because it's not explicitly True.

        This is the fix for TASK-FIX-COVNULL where quality gates failed due to
        coverage=None being evaluated as falsy even though coverage wasn't measured.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage_met": None,  # Explicitly None - coverage not measured
            },
            "code_review": {"score": 82},
        }

        status = validator.verify_quality_gates(results)

        # coverage_met=None should be treated as True (pass) since coverage wasn't measured
        assert status.coverage_met is True
        assert status.all_gates_passed is True

    def test_verify_coverage_false_still_fails(self, tmp_worktree):
        """Test that coverage_met=False still correctly fails the gate.

        Ensure the None handling doesn't break explicit False values.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage_met": False,  # Explicitly False - coverage below threshold
            },
            "code_review": {"score": 82},
        }

        status = validator.verify_quality_gates(results)

        # coverage_met=False should still fail
        assert status.coverage_met is False
        assert status.all_gates_passed is False

    def test_verify_coverage_true_still_passes(self, tmp_worktree):
        """Test that coverage_met=True still correctly passes the gate.

        Ensure the None handling doesn't break explicit True values.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage_met": True,  # Explicitly True - coverage met
            },
            "code_review": {"score": 82},
        }

        status = validator.verify_quality_gates(results)

        # coverage_met=True should pass
        assert status.coverage_met is True
        assert status.all_gates_passed is True

    def test_verify_quality_gates_reads_quality_gates_object(self, tmp_worktree):
        """Coach should read from quality_gates object, not test_results."""
        task_work_results = {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 7,
                "tests_failed": 0,
                "coverage_met": True,
            },
            # Include code_review to make arch review pass
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        assert status.tests_passed is True
        assert status.coverage_met is True
        assert status.arch_review_passed is True
        assert status.all_gates_passed is True


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

            validator = CoachValidator(str(tmp_worktree))
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

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

    def test_run_tests_timeout(self, tmp_worktree):
        """Test test execution timeout."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)

            validator = CoachValidator(str(tmp_worktree), test_timeout=300)
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "timed out" in result.test_output_summary.lower()

    def test_run_tests_exception(self, tmp_worktree):
        """Test test execution exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command not found")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert result.tests_passed is False
        assert "failed" in result.test_output_summary.lower()

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

    def test_run_tests_auto_detects_python(self, tmp_worktree):
        """Test auto-detection of pytest for Python projects."""
        # Create Python project indicator
        (tmp_worktree / "pyproject.toml").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "pytest" in result.test_command

    def test_run_tests_auto_detects_node(self, tmp_worktree):
        """Test auto-detection of npm test for Node projects."""
        # Create Node project indicator
        (tmp_worktree / "package.json").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "npm test" in result.test_command

    def test_run_tests_auto_detects_dotnet(self, tmp_worktree):
        """Test auto-detection of dotnet test for .NET projects."""
        # Create .NET project indicator
        (tmp_worktree / "Example.csproj").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.run_independent_tests()

        assert "dotnet test" in result.test_command


# ============================================================================
# Test Requirements Validation
# ============================================================================


class TestRequirementsValidation:
    """Test requirements satisfaction validation."""

    def test_all_criteria_met(self, tmp_worktree):
        """Test when all acceptance criteria are met."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Criterion A", "Criterion B", "Criterion C"])
        results = make_task_work_results(
            requirements_met=["Criterion A", "Criterion B", "Criterion C"]
        )

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True
        assert validation.criteria_total == 3
        assert validation.criteria_met == 3
        assert len(validation.missing) == 0

    def test_some_criteria_missing(self, tmp_worktree):
        """Test when some acceptance criteria are missing."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["A", "B", "C", "D"])
        results = make_task_work_results(requirements_met=["A", "B"])

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is False
        assert validation.criteria_total == 4
        assert validation.criteria_met == 2
        assert "C" in validation.missing
        assert "D" in validation.missing

    def test_case_insensitive_matching(self, tmp_worktree):
        """Test case-insensitive criteria matching."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["OAuth2 Flow"])
        results = make_task_work_results(requirements_met=["oauth2 flow"])

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True
        assert len(validation.missing) == 0

    def test_whitespace_normalized_matching(self, tmp_worktree):
        """Test whitespace-normalized criteria matching."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["  OAuth2 Flow  "])
        results = make_task_work_results(requirements_met=["OAuth2 Flow"])

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True

    def test_empty_acceptance_criteria(self, tmp_worktree):
        """Test when task has no acceptance criteria."""
        validator = CoachValidator(str(tmp_worktree))
        task = {"acceptance_criteria": []}  # Explicit empty list
        results = {"requirements_met": ["Something"]}  # Explicit

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True
        assert validation.criteria_total == 0
        assert validation.criteria_met == 0

    def test_empty_requirements_met(self, tmp_worktree):
        """Test when task-work has no requirements_met."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["A", "B"])
        results = make_task_work_results(requirements_met=[])

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is False
        assert validation.criteria_met == 0
        assert "A" in validation.missing
        assert "B" in validation.missing


# ============================================================================
# Test Dataclasses
# ============================================================================


class TestDataclasses:
    """Test dataclass initialization and behavior."""

    def test_quality_gate_status_all_passed(self):
        """Test QualityGateStatus with all gates passing."""
        status = QualityGateStatus(
            tests_passed=True,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )

        assert status.all_gates_passed is True

    def test_quality_gate_status_one_failed(self):
        """Test QualityGateStatus with one gate failing."""
        status = QualityGateStatus(
            tests_passed=False,  # Failed
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )

        assert status.all_gates_passed is False

    def test_quality_gate_status_all_failed(self):
        """Test QualityGateStatus with all gates failing."""
        status = QualityGateStatus(
            tests_passed=False,
            coverage_met=False,
            arch_review_passed=False,
            plan_audit_passed=False,
        )

        assert status.all_gates_passed is False

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

    def test_requirements_validation_fields(self):
        """Test RequirementsValidation has expected fields."""
        validation = RequirementsValidation(
            criteria_total=5,
            criteria_met=3,
            all_criteria_met=False,
            missing=["X", "Y"],
        )

        assert validation.criteria_total == 5
        assert validation.criteria_met == 3
        assert validation.all_criteria_met is False
        assert validation.missing == ["X", "Y"]

    def test_requirements_validation_default_missing(self):
        """Test RequirementsValidation missing defaults to empty list."""
        validation = RequirementsValidation(
            criteria_total=3,
            criteria_met=3,
            all_criteria_met=True,
        )

        assert validation.missing == []

    def test_coach_validation_result_approve(self):
        """Test CoachValidationResult for approve decision."""
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="approve",
            quality_gates=QualityGateStatus(True, True, True, True),
            independent_tests=IndependentTestResult(True, "pytest", "OK", 1.0),
            requirements=RequirementsValidation(3, 3, True),
            issues=[],
            rationale="All checks passed",
        )

        assert result.decision == "approve"
        assert len(result.issues) == 0

    def test_coach_validation_result_feedback(self):
        """Test CoachValidationResult for feedback decision."""
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            issues=[{"severity": "must_fix", "category": "test_failure"}],
            rationale="Tests failed",
        )

        assert result.decision == "feedback"
        assert len(result.issues) == 1

    def test_coach_validation_result_to_dict(self):
        """Test CoachValidationResult.to_dict() serialization."""
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=2,
            decision="approve",
            quality_gates=QualityGateStatus(True, True, True, True),
            independent_tests=IndependentTestResult(True, "pytest", "15 passed", 1.5),
            requirements=RequirementsValidation(3, 3, True, []),
            issues=[],
            rationale="All passed",
        )

        d = result.to_dict()

        assert d["task_id"] == "TASK-001"
        assert d["turn"] == 2
        assert d["decision"] == "approve"
        assert d["validation_results"]["quality_gates"]["all_gates_passed"] is True
        assert d["validation_results"]["independent_tests"]["tests_passed"] is True
        assert d["validation_results"]["requirements"]["all_criteria_met"] is True
        assert d["issues"] == []
        assert d["rationale"] == "All passed"

    def test_coach_validation_result_to_dict_with_none(self):
        """Test CoachValidationResult.to_dict() with None values."""
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            quality_gates=None,
            independent_tests=None,
            requirements=None,
            issues=[{"category": "missing_results"}],
            rationale="Results not found",
        )

        d = result.to_dict()

        assert d["validation_results"]["quality_gates"] is None
        assert d["validation_results"]["independent_tests"] is None
        assert d["validation_results"]["requirements"] is None


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestCoachValidatorHelpers:
    """Test CoachValidator helper methods."""

    def test_save_decision_creates_file(self, tmp_worktree):
        """Test save_decision creates JSON file."""
        validator = CoachValidator(str(tmp_worktree))
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="approve",
            issues=[],
            rationale="All passed",
        )

        path = validator.save_decision(result)

        assert path.exists()
        assert path.name == "coach_turn_1.json"

        with open(path) as f:
            saved = json.load(f)

        assert saved["task_id"] == "TASK-001"
        assert saved["turn"] == 1
        assert saved["decision"] == "approve"

    def test_save_decision_creates_directory(self, tmp_worktree):
        """Test save_decision creates parent directories."""
        validator = CoachValidator(str(tmp_worktree))
        result = CoachValidationResult(
            task_id="TASK-NEW",
            turn=1,
            decision="approve",
            issues=[],
            rationale="All passed",
        )

        path = validator.save_decision(result)

        assert path.exists()
        assert "TASK-NEW" in str(path)

    def test_save_decision_multiple_turns(self, tmp_worktree):
        """Test save_decision for multiple turns."""
        validator = CoachValidator(str(tmp_worktree))

        for turn in range(1, 4):
            result = CoachValidationResult(
                task_id="TASK-001",
                turn=turn,
                decision="feedback" if turn < 3 else "approve",
                issues=[] if turn == 3 else [{"category": "test_failure"}],
                rationale=f"Turn {turn}",
            )
            path = validator.save_decision(result)

            assert path.exists()
            assert f"coach_turn_{turn}.json" == path.name

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

        assert hasattr(validator, "validate")
        assert hasattr(validator, "read_quality_gate_results")
        assert hasattr(validator, "verify_quality_gates")
        assert hasattr(validator, "run_independent_tests")
        assert hasattr(validator, "validate_requirements")
        assert hasattr(validator, "save_decision")

    def test_validator_returns_expected_type(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test validate returns CoachValidationResult."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task())

        assert isinstance(result, CoachValidationResult)
        assert hasattr(result, "task_id")
        assert hasattr(result, "turn")
        assert hasattr(result, "decision")
        assert hasattr(result, "quality_gates")
        assert hasattr(result, "independent_tests")
        assert hasattr(result, "requirements")
        assert hasattr(result, "issues")
        assert hasattr(result, "rationale")

    def test_validator_result_can_serialize_to_json(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test validation result can be serialized to JSON."""
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task())

        # Should not raise
        d = result.to_dict()
        json_str = json.dumps(d)

        assert len(json_str) > 0
        assert "TASK-001" in json_str


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
    """Test application of quality gate profiles during validation."""

    def test_scaffolding_profile_skips_arch_review(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that scaffolding profile skips architectural review gate."""
        # Write results with low arch score (would fail feature profile)
        results = make_task_work_results(
            arch_score=45,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "scaffolding",
            "acceptance_criteria": ["Criterion 1"],
        }

        # No subprocess mock needed - scaffolding skips independent tests
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should approve despite low arch score because scaffolding doesn't require arch review
        assert result.decision == "approve"
        assert result.quality_gates.arch_review_required is False
        assert result.quality_gates.arch_review_passed is True  # Skipped, so True
        assert result.quality_gates.all_gates_passed is True
        # Verify independent tests were skipped (not run)
        assert result.independent_tests.test_command == "skipped"

    def test_scaffolding_profile_skips_coverage(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that scaffolding profile skips coverage gate."""
        # Write results with low coverage (would fail feature profile)
        results = make_task_work_results(
            coverage_met=False,
            line_coverage=45,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "scaffolding",
            "acceptance_criteria": ["Criterion 1"],
        }

        # No subprocess mock needed - scaffolding skips independent tests
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should approve despite low coverage because scaffolding doesn't require coverage
        assert result.decision == "approve"
        assert result.quality_gates.coverage_required is False
        assert result.quality_gates.coverage_met is True  # Skipped, so True
        assert result.quality_gates.all_gates_passed is True
        # Verify independent tests were skipped (not run)
        assert result.independent_tests.test_command == "skipped"

    def test_scaffolding_profile_skips_independent_test_verification(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that scaffolding profile skips independent test verification.

        Scaffolding tasks (task_type: scaffolding) should skip independent test
        verification because they CREATE the test infrastructure. Tests don't
        exist yet during scaffolding tasks.

        This is the fix for TASK-FIX-SCAF where quality gates passed but then
        independent test verification failed because tests didn't exist.
        """
        # Write results that pass quality gates for scaffolding
        results = make_task_work_results(
            tests_passed=True,  # Quality gates passed
            requirements_met=["Create test infrastructure"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "scaffolding",
            "acceptance_criteria": ["Create test infrastructure"],
        }

        # DO NOT mock subprocess.run - we want to verify tests are NOT run
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should approve without running independent tests
        assert result.decision == "approve"
        assert result.independent_tests is not None
        # Verify test verification was skipped (not actually run)
        assert result.independent_tests.test_command == "skipped"
        assert "skipped" in result.independent_tests.test_output_summary.lower()
        assert result.independent_tests.tests_passed is True
        assert result.independent_tests.duration_seconds == 0.0

    def test_feature_profile_runs_independent_test_verification(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that feature profile runs independent test verification.

        Feature tasks with tests_required=True should still run independent
        test verification (trust but verify behavior).
        """
        results = make_task_work_results(
            tests_passed=True,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, task)

        # Should run independent tests and approve
        assert result.decision == "approve"
        assert result.independent_tests is not None
        # Verify test verification was actually run (not skipped)
        assert result.independent_tests.test_command != "skipped"
        assert "skipped" not in result.independent_tests.test_output_summary.lower()
        # Verify subprocess.run was called (tests were actually run)
        mock_run.assert_called_once()

    def test_feature_profile_requires_arch_review(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that feature profile enforces architectural review."""
        # Write results with low arch score
        results = make_task_work_results(arch_score=45)
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should reject because feature profile requires arch review
        assert result.decision == "feedback"
        assert result.quality_gates.arch_review_required is True
        assert result.quality_gates.arch_review_passed is False
        assert result.quality_gates.all_gates_passed is False
        assert any(
            issue["category"] == "architectural"
            for issue in result.issues
        )

    def test_infrastructure_profile_skips_arch_review(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that infrastructure profile skips architectural review."""
        # Write results with low arch score
        results = make_task_work_results(
            arch_score=30,
            tests_passed=True,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "infrastructure",
            "acceptance_criteria": ["Criterion 1"],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, task)

        # Should approve despite low arch score (infrastructure doesn't require it)
        assert result.decision == "approve"
        assert result.quality_gates.arch_review_required is False
        assert result.quality_gates.arch_review_passed is True  # Skipped
        assert result.quality_gates.all_gates_passed is True

    def test_infrastructure_profile_requires_tests(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that infrastructure profile requires tests."""
        # Write results with no tests passed
        results = make_task_work_results(tests_passed=False, failed_count=5)
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "infrastructure",
            "acceptance_criteria": ["Criterion 1"],
        }

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should reject because infrastructure requires tests
        assert result.decision == "feedback"
        assert result.quality_gates.tests_required is True
        assert result.quality_gates.tests_passed is False
        assert any(
            issue["category"] == "test_failure"
            for issue in result.issues
        )

    def test_documentation_profile_minimal_gates(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that documentation profile skips most gates."""
        # Write results with all gates failing
        results = make_task_work_results(
            tests_passed=False,
            coverage_met=False,
            arch_score=0,
            violations=5,
            requirements_met=["Document API"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "documentation",
            "acceptance_criteria": ["Document API"],
        }

        # No subprocess mock needed - documentation skips independent tests
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task)

        # Should approve despite all gates failing (documentation minimal gates)
        assert result.decision == "approve"
        assert result.quality_gates.tests_required is False
        # Verify independent tests were skipped (not run)
        assert result.independent_tests.test_command == "skipped"
        assert result.quality_gates.coverage_required is False
        assert result.quality_gates.arch_review_required is False
        assert result.quality_gates.plan_audit_required is False
        assert result.quality_gates.all_gates_passed is True


class TestQualityGateStatusWithProfiles:
    """Test QualityGateStatus with profile-based gate requirements."""

    def test_all_gates_required_all_pass(self):
        """Test all_gates_passed when all required gates pass."""
        status = QualityGateStatus(
            tests_passed=True,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=True,
            arch_review_required=True,
            plan_audit_required=True,
        )

        assert status.all_gates_passed is True

    def test_optional_gate_skip_does_not_fail(self):
        """Test that skipped optional gates don't cause failure."""
        status = QualityGateStatus(
            tests_passed=True,
            coverage_met=False,  # Failed
            arch_review_passed=False,  # Failed
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=False,  # Optional - skip
            arch_review_required=False,  # Optional - skip
            plan_audit_required=True,
        )

        # Should pass because coverage and arch are not required
        assert status.all_gates_passed is True

    def test_required_gate_failure_fails_overall(self):
        """Test that required gate failure fails overall."""
        status = QualityGateStatus(
            tests_passed=False,  # Failed
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,  # Required
            coverage_required=False,
            arch_review_required=False,
            plan_audit_required=False,
        )

        # Should fail because tests are required
        assert status.all_gates_passed is False

    def test_no_gates_required_always_passes(self):
        """Test that when no gates are required, status passes."""
        status = QualityGateStatus(
            tests_passed=False,
            coverage_met=False,
            arch_review_passed=False,
            plan_audit_passed=False,
            tests_required=False,
            coverage_required=False,
            arch_review_required=False,
            plan_audit_required=False,
        )

        # Should pass because no gates are required
        assert status.all_gates_passed is True


# ============================================================================
# Test Skip Arch Review Feature (TASK-FIX-ARIMPL)
# ============================================================================


class TestSkipArchReview:
    """Test skip_arch_review parameter functionality.

    This test class validates the skip_arch_review feature which allows
    implement-only workflows to bypass architectural review requirements.

    Tests verify:
    - skip_arch_review=True passes with zero arch score
    - skip_arch_review=False (default) enforces arch review
    - Default behavior is False
    - Interaction with profile-based requirements
    - Full validation flow with skip flag
    """

    def test_skip_arch_review_passes_with_zero_score(self, tmp_worktree):
        """Test verify_quality_gates with skip_arch_review=True and arch_score=0.

        When skip_arch_review=True, arch review should pass regardless of score.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(arch_score=0)

        status = validator.verify_quality_gates(results, skip_arch_review=True)

        assert status.arch_review_passed is True
        assert status.all_gates_passed is True

    def test_no_skip_fails_with_zero_score(self, tmp_worktree):
        """Test verify_quality_gates with skip_arch_review=False and arch_score=0.

        When skip_arch_review=False (default), zero score should fail.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(arch_score=0)

        status = validator.verify_quality_gates(results, skip_arch_review=False)

        assert status.arch_review_passed is False
        assert status.all_gates_passed is False

    def test_skip_arch_review_default_is_false(self, tmp_worktree):
        """Test that skip_arch_review defaults to False.

        Without explicit skip_arch_review parameter, arch review should be enforced.
        """
        validator = CoachValidator(str(tmp_worktree))
        results = make_task_work_results(arch_score=45)  # Below threshold

        # Call without skip_arch_review parameter - should use default (False)
        status = validator.verify_quality_gates(results)

        assert status.arch_review_passed is False

    def test_skip_arch_review_with_scaffolding_profile_redundant(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test skip_arch_review with scaffolding profile (both skip arch review).

        Scaffolding profile already skips arch review. Adding skip_arch_review=True
        is redundant but should work without issues.
        """
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "scaffolding",
            "acceptance_criteria": ["Criterion 1"],
        }

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task, skip_arch_review=True)

        # Both mechanisms result in arch review being skipped
        assert result.quality_gates.arch_review_required is False
        assert result.decision == "approve"

    def test_skip_arch_review_overrides_profile_requirement(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test skip_arch_review overrides profile-based arch review requirement.

        Feature profile normally requires arch review. skip_arch_review=True
        should override this and allow zero score to pass.
        """
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "feature",  # Feature profile requires arch review
            "acceptance_criteria": ["Criterion 1"],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, task, skip_arch_review=True)

        # Should pass despite feature profile normally requiring arch review
        assert result.quality_gates.arch_review_passed is True
        assert result.decision == "approve"

    def test_validate_with_skip_arch_review_approves(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test full validate() call with skip_arch_review=True and arch_score=0.

        Complete validation flow should approve when skip_arch_review=True
        even with zero arch score.
        """
        results = make_task_work_results(
            arch_score=0,
            tests_passed=True,
            coverage_met=True,
        )
        write_task_work_results(task_work_results_dir, results)

        task = make_task()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, task, skip_arch_review=True)

        assert result.decision == "approve"
        assert result.quality_gates.arch_review_passed is True
        assert result.quality_gates.all_gates_passed is True
        assert len(result.issues) == 0


# ============================================================================
# Test Task-Specific Test Detection (TASK-FIX-INDTEST)
# ============================================================================


class TestTaskSpecificTestDetection:
    """Test task-specific test detection and filtering.

    These tests verify the fix for TASK-FIX-INDTEST where independent test
    verification in shared worktrees was discovering ALL tests from ALL tasks
    instead of just the specific task being validated.
    """

    def test_task_id_to_pattern_prefix_basic(self, tmp_worktree):
        """Test basic task_id to pattern conversion."""
        validator = CoachValidator(str(tmp_worktree))

        assert validator._task_id_to_pattern_prefix("TASK-FHA-002") == "task_fha_002"
        assert validator._task_id_to_pattern_prefix("TASK-001") == "task_001"
        assert validator._task_id_to_pattern_prefix("TASK-AB-001") == "task_ab_001"

    def test_task_id_to_pattern_prefix_lowercase_preserved(self, tmp_worktree):
        """Test that already lowercase IDs are preserved."""
        validator = CoachValidator(str(tmp_worktree))

        # Already lowercase should work
        assert validator._task_id_to_pattern_prefix("task-001") == "task_001"

    def test_detect_test_command_finds_task_specific_tests(self, tmp_worktree):
        """Test detection of task-specific test files."""
        # Create Python project indicator
        (tmp_worktree / "pyproject.toml").touch()

        # Create test directory and task-specific test file
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_fha_002_auth.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FHA-002")
        test_cmd = validator._detect_test_command("TASK-FHA-002")

        assert "test_task_fha_002_auth.py" in test_cmd
        assert "pytest" in test_cmd
        assert "tests/ " not in test_cmd  # Should NOT include full directory

    def test_detect_test_command_returns_none_when_no_task_tests(self, tmp_worktree):
        """Test that None is returned when no task-specific tests found.

        When task_id is provided but no matching test files exist, _detect_test_command
        should return None to signal that independent verification should be skipped.
        This prevents running all tests from parallel tasks in shared worktrees.

        Replaces old fallback behavior (TASK-FIX-INDFB).
        """
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests directory with other tests (not task-specific)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_other_feature.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
        test_cmd = validator._detect_test_command("TASK-XYZ-999")

        # Should return None (skip verification) instead of falling back to full suite
        assert test_cmd is None

    def test_detect_test_command_without_task_id(self, tmp_worktree):
        """Test original behavior when task_id is None."""
        (tmp_worktree / "pyproject.toml").touch()

        validator = CoachValidator(str(tmp_worktree))  # No task_id
        test_cmd = validator._detect_test_command(None)

        assert test_cmd == "pytest tests/ -v --tb=short"

    def test_detect_test_command_multiple_matching_files(self, tmp_worktree):
        """Test handling of multiple task-specific test files."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_fha_002_auth.py").touch()
        (tests_dir / "test_task_fha_002_validation.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FHA-002")
        test_cmd = validator._detect_test_command("TASK-FHA-002")

        # Both files should be included
        assert "test_task_fha_002_auth.py" in test_cmd
        assert "test_task_fha_002_validation.py" in test_cmd

    def test_run_independent_tests_uses_task_specific_command(self, tmp_worktree):
        """Test that run_independent_tests uses task-specific command when available."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_abc_001.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-ABC-001")
            result = validator.run_independent_tests()

        # Verify task-specific test file was used.
        # pytest commands are now passed as a list (sys.executable -m pytest ...) so
        # we check membership across the joined string.
        call_args = mock_run.call_args[0][0]
        call_args_str = " ".join(call_args) if isinstance(call_args, list) else call_args
        assert "test_task_abc_001.py" in call_args_str
        assert "tests/ " not in call_args_str  # Full directory not used

    def test_constructor_stores_task_id(self, tmp_worktree):
        """Test that CoachValidator stores task_id in constructor."""
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-TEST-001")

        assert validator.task_id == "TASK-TEST-001"

    def test_constructor_task_id_defaults_to_none(self, tmp_worktree):
        """Test that task_id defaults to None."""
        validator = CoachValidator(str(tmp_worktree))

        assert validator.task_id is None

    def test_detect_test_command_with_special_characters_in_task_id(self, tmp_worktree):
        """Test task ID conversion handles various formats."""
        validator = CoachValidator(str(tmp_worktree))

        # Test various task ID formats
        assert validator._task_id_to_pattern_prefix("TASK-FIX-INDTEST") == "task_fix_indtest"
        assert validator._task_id_to_pattern_prefix("TASK-REV-FB25") == "task_rev_fb25"
        assert validator._task_id_to_pattern_prefix("TASK-E01-A3F2") == "task_e01_a3f2"

    def test_run_independent_tests_skips_when_no_task_tests(self, tmp_worktree):
        """Test that run_independent_tests skips when no task-specific tests found.

        When task_id is provided but no matching test files exist, independent test
        verification should be skipped instead of running all tests (which would
        include tests from other parallel tasks).

        This is the fix for TASK-FIX-INDFB.
        """
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests directory with other tests (not task-specific)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_other_feature.py").touch()

        # DO NOT mock subprocess.run - we want to verify tests are NOT run
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
        result = validator.run_independent_tests()

        # Should skip verification with descriptive result
        assert result.tests_passed is True
        assert result.test_command == "skipped"
        assert "no task-specific tests found" in result.test_output_summary.lower()
        assert "TASK-XYZ-999" in result.test_output_summary
        assert result.duration_seconds == 0.0

    def test_run_independent_tests_still_runs_when_task_tests_exist(self, tmp_worktree):
        """Test that run_independent_tests runs when task-specific tests ARE found.

        Ensure the skip behavior doesn't affect normal operation when tests exist.
        """
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_xyz_999_feature.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-999")
            result = validator.run_independent_tests()

        # Should actually run the tests
        assert result.test_command != "skipped"
        assert "test_task_xyz_999_feature.py" in result.test_command
        mock_run.assert_called_once()

    def test_run_independent_tests_without_task_id_runs_full_suite(self, tmp_worktree):
        """Test that run_independent_tests runs full suite when task_id is None.

        When no task_id is provided (standalone mode), should run full test suite.
        """
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree))  # No task_id
            result = validator.run_independent_tests()

        # Should run full test suite
        assert result.test_command == "pytest tests/ -v --tb=short"
        mock_run.assert_called_once()


# ============================================================================
# Recursive Test Glob Tests (TASK-FIX-93B1)
# ============================================================================


class TestRecursiveTestGlob:
    """Test recursive glob pattern for task-specific test detection.

    Verifies that _detect_test_command finds tests in nested subdirectories
    (e.g., tests/health/, tests/api/, tests/unit/) via the recursive
    tests/**/test_{prefix}*.py glob pattern.

    Fix for: TASK-FIX-93B1 (P0 from TASK-REV-93E1)
    """

    def test_finds_tests_in_nested_health_directory(self, tmp_worktree):
        """Test that tests in tests/health/ subdirectory are found."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create nested test directory
        health_dir = tmp_worktree / "tests" / "health"
        health_dir.mkdir(parents=True)
        (health_dir / "test_task_db_006_database_health.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DB-006")
        test_cmd = validator._detect_test_command("TASK-DB-006")

        assert test_cmd is not None
        assert "test_task_db_006_database_health.py" in test_cmd
        assert "pytest" in test_cmd

    def test_finds_tests_in_nested_api_directory(self, tmp_worktree):
        """Test that tests in tests/api/ subdirectory are found."""
        (tmp_worktree / "pyproject.toml").touch()

        api_dir = tmp_worktree / "tests" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "test_task_foo_001_endpoints.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FOO-001")
        test_cmd = validator._detect_test_command("TASK-FOO-001")

        assert test_cmd is not None
        assert "test_task_foo_001_endpoints.py" in test_cmd

    def test_finds_tests_in_deeply_nested_directory(self, tmp_worktree):
        """Test that tests in deeply nested directories are found."""
        (tmp_worktree / "pyproject.toml").touch()

        deep_dir = tmp_worktree / "tests" / "unit" / "models"
        deep_dir.mkdir(parents=True)
        (deep_dir / "test_task_abc_001_model.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-ABC-001")
        test_cmd = validator._detect_test_command("TASK-ABC-001")

        assert test_cmd is not None
        assert "test_task_abc_001_model.py" in test_cmd

    def test_still_finds_tests_in_flat_directory(self, tmp_worktree):
        """Test that flat tests/ directory tests are still found (** matches zero dirs)."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_foo_001_basic.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-FOO-001")
        test_cmd = validator._detect_test_command("TASK-FOO-001")

        assert test_cmd is not None
        assert "test_task_foo_001_basic.py" in test_cmd

    def test_finds_tests_across_multiple_nested_dirs(self, tmp_worktree):
        """Test that tests spread across multiple nested dirs are all found."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create tests in multiple subdirectories
        for subdir in ["unit", "integration"]:
            nested = tmp_worktree / "tests" / subdir
            nested.mkdir(parents=True)

        (tmp_worktree / "tests" / "unit" / "test_task_xyz_001_unit.py").touch()
        (tmp_worktree / "tests" / "integration" / "test_task_xyz_001_integ.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-XYZ-001")
        test_cmd = validator._detect_test_command("TASK-XYZ-001")

        assert test_cmd is not None
        assert "test_task_xyz_001_unit.py" in test_cmd
        assert "test_task_xyz_001_integ.py" in test_cmd

    def test_no_match_in_nested_returns_none(self, tmp_worktree):
        """Test that no matches in any directory still returns None."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create nested dirs with non-matching tests
        health_dir = tmp_worktree / "tests" / "health"
        health_dir.mkdir(parents=True)
        (health_dir / "test_task_other_999.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DB-006")
        test_cmd = validator._detect_test_command("TASK-DB-006")

        assert test_cmd is None




# ============================================================================
# Primary Test Detection via task_work_results (TASK-FIX-TDPR)
# ============================================================================


class TestPrimaryTestDetection:
    """Tests for detecting test files from task_work_results (primary path).

    The primary detection path extracts test files from task_work_results
    files_created/files_modified lists (already in memory). The task-ID
    glob pattern is kept as a fallback for when results aren't available.
    """

    def test_detect_tests_from_results_finds_created_tests(self, tmp_worktree):
        """Test that test files in files_created list are detected."""
        # Create the test file in the worktree
        test_dir = tmp_worktree / "tests" / "orchestrator"
        test_dir.mkdir(parents=True)
        (test_dir / "test_mcp_design_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": [
                "guardkit/orchestrator/mcp_design_extractor.py",
                "tests/orchestrator/test_mcp_design_extractor.py",
            ],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_mcp_design_extractor.py" in result
        assert "pytest" in result

    def test_detect_tests_from_results_finds_modified_tests(self, tmp_worktree):
        """Test that test files in files_modified list are detected."""
        test_dir = tmp_worktree / "tests" / "unit"
        test_dir.mkdir(parents=True)
        (test_dir / "test_design_integration.py").write_text("def test_y(): pass")

        task_work_results = {
            "files_created": [],
            "files_modified": ["tests/unit/test_design_integration.py"],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-007")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "test_design_integration.py" in result

    def test_detect_tests_from_results_ignores_nonexistent_files(self, tmp_worktree):
        """Test that test files listed but not present on disk are skipped."""
        # Don't create the file on disk
        task_work_results = {
            "files_created": ["tests/test_nonexistent.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-003")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is None

    def test_detect_tests_from_results_returns_none_when_no_tests(self, tmp_worktree):
        """Test that None is returned when results have no test files."""
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-001")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is None

    def test_detect_tests_from_results_handles_suffix_test_naming(self, tmp_worktree):
        """Test detection of *_test.py naming convention."""
        test_dir = tmp_worktree / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "browser_verifier_test.py").write_text("def test_a(): pass")

        task_work_results = {
            "files_created": ["tests/browser_verifier_test.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-009")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        assert "browser_verifier_test.py" in result

    def test_detect_tests_from_results_deduplicates_files(self, tmp_worktree):
        """Test that duplicate test files across created/modified are deduplicated."""
        test_dir = tmp_worktree / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "test_detector.py").write_text("def test_a(): pass")

        task_work_results = {
            "files_created": ["tests/test_detector.py"],
            "files_modified": ["tests/test_detector.py"],  # Same file in both lists
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-010")
        result = validator._detect_tests_from_results(task_work_results)

        assert result is not None
        # Should appear only once
        assert result.count("test_detector.py") == 1

    def test_detect_test_command_uses_results_as_primary(self, tmp_worktree):
        """Test that _detect_test_command uses task_work_results as primary source."""
        (tmp_worktree / "pyproject.toml").touch()

        # No task-ID-named tests exist
        tests_dir = tmp_worktree / "tests" / "unit"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_mcp_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": ["tests/unit/test_mcp_extractor.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        assert test_cmd is not None
        assert "test_mcp_extractor.py" in test_cmd
        assert "pytest" in test_cmd

    def test_detect_test_command_falls_back_to_glob_when_no_results(self, tmp_worktree):
        """Test that _detect_test_command falls back to glob when task_work_results is None."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create task-ID-named test file (matches glob pattern)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_task_dm_002_main.py").touch()

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command("TASK-DM-002", task_work_results=None)

        assert test_cmd is not None
        assert "test_task_dm_002_main.py" in test_cmd

    def test_detect_test_command_falls_back_to_glob_when_results_have_no_tests(self, tmp_worktree):
        """Test that _detect_test_command falls back to glob when results have no test files."""
        (tmp_worktree / "pyproject.toml").touch()

        # Create task-ID-named test file (matches glob pattern)
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_task_dm_002_main.py").touch()

        # Results have no test files
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        # Should fall back to glob pattern since results had no tests
        assert test_cmd is not None
        assert "test_task_dm_002_main.py" in test_cmd

    def test_detect_test_command_results_take_priority_over_glob(self, tmp_worktree):
        """Test that task_work_results take priority over task-ID glob pattern."""
        (tmp_worktree / "pyproject.toml").touch()

        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)

        # Create task-ID-named test file (matches glob pattern)
        (tests_dir / "test_task_dm_002_main.py").touch()

        # Create a different test file referenced in results
        (tests_dir / "test_mcp_extractor.py").write_text("def test_x(): pass")

        task_work_results = {
            "files_created": ["tests/test_mcp_extractor.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        # Should use the results-based test, not the glob pattern
        assert "test_mcp_extractor.py" in test_cmd
        assert "test_task_dm_002_main.py" not in test_cmd

    def test_detect_test_command_returns_none_when_no_tests_anywhere(self, tmp_worktree):
        """Test None returned when neither results nor glob find tests."""
        (tmp_worktree / "pyproject.toml").touch()

        # No tests exist at all
        task_work_results = {
            "files_created": ["guardkit/models/frontmatter.py"],
            "files_modified": [],
        }

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-DM-002")
        test_cmd = validator._detect_test_command(
            "TASK-DM-002", task_work_results=task_work_results
        )

        assert test_cmd is None


# ============================================================================
# Approval Rationale and Zero-Test Anomaly (TASK-FIX-QGVZ + TASK-FIX-ITDF)
# ============================================================================


class TestApprovalRationaleAndZeroTestAnomaly:
    """Tests for accurate rationale messages and zero-test anomaly detection."""

    def test_rationale_when_tests_independently_verified(self, tmp_worktree, task_work_results_dir):
        """Test rationale when independent tests actually ran."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        test_result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/test_something.py -v",
            test_output_summary="5 passed",
            duration_seconds=1.5,
        )
        task_work_results = make_task_work_results()

        validator = CoachValidator(str(tmp_worktree))
        rationale = validator._build_approval_rationale(
            test_result=test_result,
            gates_status=QualityGateStatus(
                tests_passed=True, coverage_met=True,
                arch_review_passed=True, plan_audit_passed=True,
            ),
            task_work_results=task_work_results,
            profile=profile,
        )

        assert "Independent verification confirmed." in rationale
        assert "skipped" not in rationale.lower()

    def test_rationale_when_tests_skipped_no_files_found(self, tmp_worktree, task_work_results_dir):
        """Test rationale when independent tests were skipped (no tests found)."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        test_result = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )
        task_work_results = make_task_work_results()

        validator = CoachValidator(str(tmp_worktree))
        rationale = validator._build_approval_rationale(
            test_result=test_result,
            gates_status=QualityGateStatus(
                tests_passed=True, coverage_met=True,
                arch_review_passed=True, plan_audit_passed=True,
            ),
            task_work_results=task_work_results,
            profile=profile,
        )

        assert "Independent verification skipped: no task-specific tests found." in rationale
        assert "confirmed" not in rationale.lower()

    def test_rationale_when_tests_not_required(self, tmp_worktree, task_work_results_dir):
        """Test rationale for scaffolding tasks where tests aren't required."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.SCAFFOLDING)
        test_result = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="Independent test verification skipped (tests_required=False)",
            duration_seconds=0.0,
        )
        task_work_results = make_task_work_results()

        validator = CoachValidator(str(tmp_worktree))
        rationale = validator._build_approval_rationale(
            test_result=test_result,
            gates_status=QualityGateStatus(
                tests_passed=True, coverage_met=True,
                arch_review_passed=True, plan_audit_passed=True,
            ),
            task_work_results=task_work_results,
            profile=profile,
        )

        assert "Tests not required for this task type." in rationale

    def test_zero_test_anomaly_detected_for_feature_task(self, tmp_worktree):
        """Test that zero-test anomaly is detected with error severity for feature tasks."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 1
        assert issues[0]["category"] == "zero_test_anomaly"
        assert issues[0]["severity"] == "error"  # blocking for feature tasks
        assert "no tests were executed" in issues[0]["description"]

    def test_zero_test_anomaly_not_raised_for_scaffolding(self, tmp_worktree):
        """Test that zero-test anomaly is NOT raised for scaffolding tasks."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.SCAFFOLDING)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 0

    def test_zero_test_anomaly_not_raised_when_tests_exist(self, tmp_worktree):
        """Test that zero-test anomaly is NOT raised when tests actually ran."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 37,
                "tests_failed": 0,
                "coverage": 82.0,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 0

    def test_zero_test_anomaly_not_raised_when_all_passed_false(self, tmp_worktree):
        """Test that anomaly is NOT raised when all_passed is False (failure, not anomaly)."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "all_passed": False,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 0

    def test_zero_test_anomaly_blocks_feature_task_approval(self, tmp_worktree, task_work_results_dir):
        """Test that zero-test anomaly blocks approval for feature tasks (zero_test_blocking=True)."""
        # Create task work results with zero tests
        results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": True,
            },
            "code_review": {"score": 85},
            "plan_audit": {"violations": 0},
            "requirements_met": ["Criterion A"],
        }
        (task_work_results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001")
        result = validator.validate(
            task_id="TASK-001",
            turn=1,
            task={
                "acceptance_criteria": ["Criterion A"],
                "task_type": "feature",
            },
        )

        # Feature profile has zero_test_blocking=True, so decision should be feedback
        assert result.decision == "feedback"
        assert len(result.issues) == 1
        assert result.issues[0]["category"] == "zero_test_anomaly"
        assert result.issues[0]["severity"] == "error"
        # Rationale should mention zero-test anomaly
        assert "zero-test anomaly" in result.rationale.lower()


# ============================================================================
# Test Zero-Test Blocking Configuration (TASK-AQG-002)
# ============================================================================


class TestZeroTestBlockingConfiguration:
    """Test configurable zero-test anomaly blocking behavior."""

    def test_feature_profile_has_zero_test_blocking_true(self):
        """AC1: Feature profile has zero_test_blocking=True."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        assert profile.zero_test_blocking is True

    def test_refactor_profile_has_zero_test_blocking_true(self):
        """AC1: Refactor profile has zero_test_blocking=True."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.REFACTOR)
        assert profile.zero_test_blocking is True

    def test_documentation_profile_has_zero_test_blocking_false(self):
        """AC3: Documentation profile has zero_test_blocking=False (unaffected)."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.DOCUMENTATION)
        assert profile.zero_test_blocking is False

    def test_testing_profile_has_zero_test_blocking_false(self):
        """AC3: Testing profile has zero_test_blocking=False (unaffected)."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.TESTING)
        assert profile.zero_test_blocking is False

    def test_scaffolding_profile_has_zero_test_blocking_false(self):
        """AC4: Scaffolding profile keeps default zero_test_blocking=False."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.SCAFFOLDING)
        assert profile.zero_test_blocking is False

    def test_infrastructure_profile_has_zero_test_blocking_false(self):
        """AC4: Infrastructure profile keeps default zero_test_blocking=False."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.INFRASTRUCTURE)
        assert profile.zero_test_blocking is False

    def test_default_zero_test_blocking_is_false(self):
        """AC4: Default value is False for backward compatibility."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
        )
        assert profile.zero_test_blocking is False

    def test_blocking_enabled_zero_tests_returns_error(self, tmp_worktree):
        """AC2/AC5: Blocking enabled + zero tests = error severity."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["category"] == "zero_test_anomaly"

    def test_blocking_disabled_zero_tests_returns_warning(self, tmp_worktree):
        """AC5: Blocking disabled + zero tests = warning severity (non-blocking)."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=False,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert issues[0]["category"] == "zero_test_anomaly"

    def test_non_zero_tests_returns_empty_regardless_of_blocking(self, tmp_worktree):
        """AC5: Non-zero tests = no issues regardless of blocking setting."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 15,
                "coverage": 85.0,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(task_work_results, profile)

        assert len(issues) == 0

    def test_blocking_zero_test_prevents_approval(self, tmp_worktree, task_work_results_dir):
        """AC2: Feature task with zero tests gets feedback decision (blocked)."""
        results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": True,
            },
            "code_review": {"score": 85},
            "plan_audit": {"violations": 0},
            "requirements_met": ["Criterion A"],
        }
        (task_work_results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001")
        result = validator.validate(
            task_id="TASK-001",
            turn=1,
            task={
                "acceptance_criteria": ["Criterion A"],
                "task_type": "feature",
            },
        )

        assert result.decision == "feedback"
        assert any(i["category"] == "zero_test_anomaly" for i in result.issues)
        assert "zero-test anomaly" in result.rationale.lower()

    def test_non_blocking_zero_test_allows_approval(self, tmp_worktree, task_work_results_dir):
        """AC3: Documentation task with zero tests still gets approved."""
        results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": True,
            },
            "code_review": {"score": 85},
            "plan_audit": {"violations": 0},
            "requirements_met": ["Criterion A"],
        }
        (task_work_results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001")
        result = validator.validate(
            task_id="TASK-001",
            turn=1,
            task={
                "acceptance_criteria": ["Criterion A"],
                "task_type": "documentation",
            },
        )

        # Documentation tasks have tests_required=False, so anomaly check is skipped entirely
        assert result.decision == "approve"


# ============================================================================
# Independent Test Override for Zero-Test Anomaly (TASK-FIX-CEE8b)
# ============================================================================


class TestZeroTestAnomalyIndependentTestOverride:
    """Test that independent test results override zero-test anomaly detection."""

    def test_independent_tests_passed_skips_anomaly(self, tmp_worktree):
        """AC-001: Zero-test anomaly with independent_tests.tests_passed=True returns empty list."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="5 passed",
            duration_seconds=1.5,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 0

    def test_independent_tests_none_still_fires(self, tmp_worktree):
        """AC-002: Zero-test anomaly with independent_tests=None still fires."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=None
        )

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["category"] == "zero_test_anomaly"

    def test_independent_tests_failed_still_fires(self, tmp_worktree):
        """AC-003: Zero-test anomaly with independent_tests.tests_passed=False still fires."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }
        independent_tests = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="2 failed",
            duration_seconds=1.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["category"] == "zero_test_anomaly"

    def test_non_zero_tests_with_independent_passed_returns_empty(self, tmp_worktree):
        """AC-004: Non-zero tests with independent tests passed returns empty list."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 10,
                "coverage": 85.0,
                "all_passed": True,
            },
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="10 passed",
            duration_seconds=2.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 0

    def test_independent_passed_non_blocking_profile_also_skips(self, tmp_worktree):
        """Independent tests passed skips anomaly even with non-blocking profile."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=False,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/ -v",
            test_output_summary="3 passed",
            duration_seconds=0.5,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 0

    def test_vacuous_pass_skipped_still_fires_anomaly(self, tmp_worktree):
        """Vacuous pass (test_command='skipped', no tests found) still fires anomaly."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "coverage": None,
                "all_passed": True,
            },
        }
        # Vacuous pass: tests_passed=True but test_command="skipped" (no test files found)
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["category"] == "zero_test_anomaly"

    def test_validate_approval_with_zero_tests_and_independent_passed(
        self, tmp_worktree, task_work_results_dir
    ):
        """Integration: validate() approves when independent tests pass despite zero-test data."""
        results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": True,
            },
            "code_review": {"score": 85},
            "plan_audit": {"violations": 0},
            "requirements_met": ["Criterion A"],
        }
        (task_work_results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001")
        # Patch run_independent_tests to return passing result
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = IndependentTestResult(
                tests_passed=True,
                test_command="pytest tests/ -v",
                test_output_summary="5 passed",
                duration_seconds=1.0,
            )
            result = validator.validate(
                task_id="TASK-001",
                turn=1,
                task={
                    "acceptance_criteria": ["Criterion A"],
                    "task_type": "feature",
                },
            )

        # With independent tests passing, zero-test anomaly should NOT block
        assert result.decision == "approve"


# ============================================================================
# Test Project-Wide Pass Bypass (TASK-FIX-ACA7a)
# ============================================================================


class TestProjectWidePassBypass:
    """Test that zero-test anomaly catches project-wide pass masking zero task-specific tests.

    Bug: When a task goes through the task-work delegation path, the stream parser captures
    "Quality gates: PASSED" from the project's existing test suite. This writes all_passed=True
    and tests_passed_count > 0 to task_work_results.json. The zero-test anomaly check sees
    tests_passed_count > 0 and doesn't trigger, even though the task contributed zero new tests.
    """

    def test_project_wide_pass_with_zero_tests_written_triggers_anomaly(self, tmp_worktree):
        """AC-001: Detects when tests_written is empty AND independent verification skipped."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "tests_failed": 0,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],  # Player created zero task-specific tests
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["category"] == "zero_test_anomaly"
        assert "task-specific tests" in issues[0]["description"]

    def test_project_wide_pass_description_contains_glob_pattern(self, tmp_worktree):
        """AC-ABF-003: Description includes glob pattern and actionable guidance."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "tests_failed": 0,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests,
            task_id="TASK-FHA-002",
        )

        assert len(issues) == 1
        desc = issues[0]["description"]
        # AC: description includes the glob pattern that was tried
        assert "tests/**/test_task_fha_002*.py" in desc
        # AC: description suggests listing test files in task_work_results
        assert "files_created" in desc
        assert "files_modified" in desc
        # AC: description suggests the naming convention
        assert "test_task_fha_002" in desc

    def test_project_wide_pass_blocking_profile_returns_error(self, tmp_worktree):
        """AC-002: Blocking error for profiles with zero_test_blocking=True."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)  # zero_test_blocking=True
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"

    def test_project_wide_pass_non_blocking_profile_returns_warning(self, tmp_worktree):
        """AC-003: Warning for profiles with zero_test_blocking=False."""
        from guardkit.models.task_types import QualityGateProfile

        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=False,
            zero_test_blocking=False,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_no_false_positive_when_task_creates_tests(self, tmp_worktree):
        """AC-004: No false positive for tasks that DO create tests."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 219,
                "coverage": 86.0,
                "all_passed": True,
            },
            "tests_written": ["tests/test_new_feature.py"],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/test_new_feature.py -v",
            test_output_summary="1 passed",
            duration_seconds=0.5,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 0

    def test_no_false_positive_for_tests_not_required(self, tmp_worktree):
        """AC-005: No false positive for tasks with tests_required=False."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.SCAFFOLDING)  # tests_required=False
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="Independent test verification skipped (tests_required=False)",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 0

    def test_no_false_positive_when_tests_written_missing_from_results(self, tmp_worktree):
        """No false positive when tests_written key is absent (defaults to empty list)
        but independent tests actually ran successfully."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 5,
                "coverage": 80.0,
                "all_passed": True,
            },
            # No tests_written key at all
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/test_feature.py -v",
            test_output_summary="5 passed",
            duration_seconds=1.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        # Independent tests passed with actual test_command (not "skipped"),
        # so the early return at line 1391-1396 catches this — no anomaly
        assert len(issues) == 0

    def test_project_wide_pass_blocks_approval_integration(
        self, tmp_worktree, task_work_results_dir
    ):
        """Integration: validate() returns feedback when project-wide pass masks zero task tests."""
        results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 218,
                "tests_failed": 0,
                "coverage": 85.0,
                "coverage_met": True,
                "all_passed": True,
            },
            "code_review": {"score": 85},
            "plan_audit": {"violations": 0},
            "requirements_met": ["Criterion A"],
            "tests_written": [],
        }
        (task_work_results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-001")
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = IndependentTestResult(
                tests_passed=True,
                test_command="skipped",
                test_output_summary="No task-specific tests found",
                duration_seconds=0.0,
            )
            result = validator.validate(
                task_id="TASK-001",
                turn=1,
                task={
                    "acceptance_criteria": ["Criterion A"],
                    "task_type": "feature",
                },
            )

        assert result.decision == "feedback"
        assert any(i["category"] == "zero_test_anomaly" for i in result.issues)
        assert "zero-test anomaly" in result.rationale.lower()

    def test_no_anomaly_without_independent_tests_param(self, tmp_worktree):
        """No anomaly triggered when independent_tests is None (backward compat)."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "coverage": 85.0,
                "all_passed": True,
            },
            "tests_written": [],
        }

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=None
        )

        # independent_tests is None, so the new check doesn't trigger
        # (and the original check at line 1403 also doesn't trigger because tests_passed=218)
        assert len(issues) == 0


# ============================================================================
# Test tests_written End-to-End (TASK-FIX-93A1)
# ============================================================================


class TestTestsWrittenEndToEnd:
    """Integration test: verify Coach sees tests_written from task_work_results.json.

    TASK-FIX-93A1: When Player reports tests_written, the results writer includes it,
    and Coach's _check_zero_test_anomaly() sees the actual list (not []).
    """

    def test_coach_sees_tests_written_from_results(self, tmp_worktree):
        """AC-003: Coach sees non-empty tests_written when Player reported tests."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        # Simulate task_work_results.json written WITH tests_written (post-fix)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage": 80.0,
                "all_passed": True,
            },
            "tests_written": ["tests/health/test_router.py"],
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/health/test_router.py -v",
            test_output_summary="5 passed",
            duration_seconds=0.5,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        # With non-empty tests_written AND real test_command, no anomaly expected
        assert len(issues) == 0

    def test_coach_still_detects_anomaly_with_empty_tests_written(self, tmp_worktree):
        """Empty tests_written + skipped independent tests still triggers anomaly."""
        from guardkit.models.task_types import get_profile, TaskType

        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "quality_gates": {
                "tests_passed": 218,
                "tests_failed": 0,
                "all_passed": True,
            },
            "tests_written": [],  # Player wrote no tests
        }
        independent_tests = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found",
            duration_seconds=0.0,
        )

        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=independent_tests
        )

        assert len(issues) == 1
        assert issues[0]["category"] == "zero_test_anomaly"


# ============================================================================
# Test Criteria Verification (TASK-AQG-001)
# ============================================================================


class TestCriteriaVerification:
    """Test structured acceptance criteria verification in Coach validator."""

    def test_criteria_results_populated_on_full_match(self, tmp_worktree):
        """AC1: validate_requirements produces per-criterion results when all match."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["OAuth2 flow", "Token refresh", "Session management"])
        results = make_task_work_results(
            requirements_met=["OAuth2 flow", "Token refresh", "Session management"]
        )

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 3
        assert all(cr.result == "verified" for cr in validation.criteria_results)
        assert all(cr.status == "verified" for cr in validation.criteria_results)
        assert validation.criteria_results[0].criterion_id == "AC-001"
        assert validation.criteria_results[1].criterion_id == "AC-002"
        assert validation.criteria_results[2].criterion_id == "AC-003"

    def test_criteria_results_populated_on_partial_match(self, tmp_worktree):
        """AC1: validate_requirements produces per-criterion results with partial match."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["User authentication", "Database schema", "Payment processing"])
        results = make_task_work_results(requirements_met=["User authentication"])

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 3
        assert validation.criteria_results[0].result == "verified"
        assert validation.criteria_results[1].result == "rejected"
        assert validation.criteria_results[2].result == "rejected"

    def test_criteria_results_populated_on_no_match(self, tmp_worktree):
        """AC1: validate_requirements produces per-criterion results when none match."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["A", "B"])
        results = make_task_work_results(requirements_met=[])

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 2
        assert all(cr.result == "rejected" for cr in validation.criteria_results)

    def test_criteria_results_empty_for_empty_criteria(self, tmp_worktree):
        """AC6: validate_requirements returns empty results for empty criteria list."""
        validator = CoachValidator(str(tmp_worktree))
        task = {"acceptance_criteria": []}
        results = {"requirements_met": []}

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 0
        assert validation.all_criteria_met is True

    def test_criterion_result_has_evidence(self, tmp_worktree):
        """AC1: Each criterion result includes evidence string."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature X"])
        results = make_task_work_results(requirements_met=["Feature X"])

        validation = validator.validate_requirements(task, results)

        cr = validation.criteria_results[0]
        assert cr.evidence != ""
        assert "Feature X" in cr.evidence

    def test_criterion_result_has_criterion_text(self, tmp_worktree):
        """AC1: Each criterion result includes the original criterion text."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["My specific criterion"])
        results = make_task_work_results(requirements_met=[])

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_results[0].criterion_text == "My specific criterion"

    def test_to_dict_includes_criteria_verification(self):
        """AC2: to_dict serializes criteria_verification in format for _display_criteria_progress."""
        cr1 = CriterionResult(
            criterion_id="AC-001",
            criterion_text="Feature A",
            result="verified",
            status="verified",
            evidence="Matched",
        )
        cr2 = CriterionResult(
            criterion_id="AC-002",
            criterion_text="Feature B",
            result="rejected",
            status="rejected",
            evidence="Not found",
        )
        reqs = RequirementsValidation(
            criteria_total=2,
            criteria_met=1,
            all_criteria_met=False,
            missing=["Feature B"],
            criteria_results=[cr1, cr2],
        )
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            requirements=reqs,
        )

        d = result.to_dict()

        # Verify criteria_verification is populated (for _display_criteria_progress)
        cv = d["criteria_verification"]
        assert len(cv) == 2
        assert cv[0]["criterion_id"] == "AC-001"
        assert cv[0]["result"] == "verified"
        assert cv[0]["notes"] == "Matched"  # notes alias for evidence
        assert cv[1]["criterion_id"] == "AC-002"
        assert cv[1]["result"] == "rejected"

    def test_to_dict_includes_acceptance_criteria_verification(self):
        """AC2: to_dict serializes acceptance_criteria_verification for _count_criteria_passed."""
        cr1 = CriterionResult(
            criterion_id="AC-001",
            criterion_text="Feature A",
            result="verified",
            status="verified",
            evidence="Matched",
        )
        reqs = RequirementsValidation(
            criteria_total=1,
            criteria_met=1,
            all_criteria_met=True,
            criteria_results=[cr1],
        )
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="approve",
            requirements=reqs,
        )

        d = result.to_dict()

        # Verify acceptance_criteria_verification.criteria_results (for _count_criteria_passed)
        acv = d["acceptance_criteria_verification"]
        assert "criteria_results" in acv
        assert len(acv["criteria_results"]) == 1
        assert acv["criteria_results"][0]["status"] == "verified"

    def test_to_dict_empty_criteria_verification_when_no_requirements(self):
        """AC2: to_dict returns empty criteria_verification when no requirements."""
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            requirements=None,
        )

        d = result.to_dict()

        assert d["criteria_verification"] == []
        assert d["acceptance_criteria_verification"]["criteria_results"] == []

    def test_display_criteria_progress_format_compatibility(self, tmp_worktree):
        """AC3: criteria_verification format matches CriterionVerification.from_dict expectations."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        results = make_task_work_results(
            requirements_met=["Feature A"]
        )

        validation = validator.validate_requirements(task, results)

        # Simulate what _display_criteria_progress does
        cr_dicts = [cr.to_dict() for cr in validation.criteria_results]
        for cr_dict in cr_dicts:
            assert "criterion_id" in cr_dict
            assert "result" in cr_dict
            assert "notes" in cr_dict
            assert cr_dict["result"] in ("verified", "rejected")

    def test_count_criteria_passed_format_compatibility(self, tmp_worktree):
        """AC4: acceptance_criteria_verification.criteria_results format matches _count_criteria_passed."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["A", "B", "C"])
        results = make_task_work_results(requirements_met=["A", "C"])

        validation = validator.validate_requirements(task, results)

        # Simulate what _count_criteria_passed does
        cr_dicts = [cr.to_dict() for cr in validation.criteria_results]
        count = sum(1 for r in cr_dicts if r.get("status") == "verified")
        assert count == 2

    def test_existing_gate_evaluation_unchanged(self, tmp_worktree, task_work_results_dir):
        """AC5: Existing quality gate evaluation is unaffected by criteria verification."""
        results = make_task_work_results(
            tests_passed=True,
            coverage_met=True,
            arch_score=82,
            violations=0,
            requirements_met=["OAuth2 authentication flow", "Token generation", "Token refresh"],
        )
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )
            validator = CoachValidator(str(tmp_worktree))
            task = make_task()
            result = validator.validate("TASK-001", 1, task)

        assert result.decision == "approve"
        assert result.quality_gates is not None
        assert result.quality_gates.all_gates_passed is True

    def test_case_insensitive_criteria_results(self, tmp_worktree):
        """AC6: Case insensitive matching produces correct per-criterion results."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["OAuth2 Flow"])
        results = make_task_work_results(requirements_met=["oauth2 flow"])

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 1
        assert validation.criteria_results[0].result == "verified"

    def test_whitespace_normalized_criteria_results(self, tmp_worktree):
        """AC6: Whitespace normalization produces correct per-criterion results."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["  Feature A  "])
        results = make_task_work_results(requirements_met=["Feature A"])

        validation = validator.validate_requirements(task, results)

        assert len(validation.criteria_results) == 1
        assert validation.criteria_results[0].result == "verified"

    def test_criterion_result_dataclass(self):
        """Test CriterionResult dataclass fields and to_dict."""
        cr = CriterionResult(
            criterion_id="AC-001",
            criterion_text="Test criterion",
            result="verified",
            status="verified",
            evidence="Found in requirements_met",
        )

        assert cr.criterion_id == "AC-001"
        assert cr.criterion_text == "Test criterion"
        assert cr.result == "verified"
        assert cr.status == "verified"
        assert cr.evidence == "Found in requirements_met"

        d = cr.to_dict()
        assert d["criterion_id"] == "AC-001"
        assert d["result"] == "verified"
        assert d["status"] == "verified"
        assert d["notes"] == "Found in requirements_met"

    def test_requirements_validation_default_criteria_results(self):
        """Test RequirementsValidation criteria_results defaults to empty list."""
        validation = RequirementsValidation(
            criteria_total=3,
            criteria_met=3,
            all_criteria_met=True,
        )
        assert validation.criteria_results == []

    def test_full_validate_produces_criteria_in_to_dict(
        self, tmp_worktree, task_work_results_dir
    ):
        """AC2+AC3+AC4: Full validate → to_dict produces correct criteria data."""
        results = make_task_work_results(
            requirements_met=["OAuth2 authentication flow", "Token generation", "Token refresh"],
        )
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )
            validator = CoachValidator(str(tmp_worktree))
            task = make_task()
            result = validator.validate("TASK-001", 1, task)

        d = result.to_dict()

        # _display_criteria_progress consumer
        assert len(d["criteria_verification"]) == 3
        assert all(v["result"] == "verified" for v in d["criteria_verification"])

        # _count_criteria_passed consumer
        acv = d["acceptance_criteria_verification"]["criteria_results"]
        assert len(acv) == 3
        count = sum(1 for r in acv if r.get("status") == "verified")
        assert count == 3


# ============================================================================
# Test Completion Promises Matching (TASK-FIX-ACA7b)
# ============================================================================


class TestCompletionPromisesMatching:
    """Test ID-based matching via completion_promises in validate_requirements."""

    def test_promises_match_all_criteria(self, tmp_worktree):
        """AC-003: All criteria verified when all promises have status complete."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B", "Feature C"])
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Impl A"},
                {"criterion_id": "AC-002", "status": "complete", "evidence": "Impl B"},
                {"criterion_id": "AC-003", "status": "complete", "evidence": "Impl C"},
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True
        assert validation.criteria_met == 3
        assert validation.criteria_total == 3
        assert len(validation.criteria_results) == 3
        assert all(cr.status == "verified" for cr in validation.criteria_results)

    def test_promises_partial_match(self, tmp_worktree):
        """AC-004: Incomplete promises show as rejected, not false positive."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B", "Feature C"])
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Done A"},
                {"criterion_id": "AC-002", "status": "incomplete", "evidence": "WIP"},
                {"criterion_id": "AC-003", "status": "complete", "evidence": "Done C"},
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is False
        assert validation.criteria_met == 2
        assert validation.criteria_results[0].status == "verified"
        assert validation.criteria_results[1].status == "rejected"
        assert validation.criteria_results[2].status == "verified"
        assert "Feature B" in validation.missing

    def test_promises_missing_criterion(self, tmp_worktree):
        """AC-004: Missing promise for a criterion shows as rejected."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Done A"},
                # AC-002 missing entirely
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_met == 1
        assert validation.criteria_results[0].status == "verified"
        assert validation.criteria_results[1].status == "rejected"
        assert "No completion promise for AC-002" in validation.criteria_results[1].evidence

    def test_promises_evidence_preserved(self, tmp_worktree):
        """AC-003: Evidence from Player promise is included in criterion result."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Implement OAuth2 flow"])
        results = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "evidence": "Added OAuth2 handler in auth.py with token refresh",
                },
            ],
        }

        validation = validator.validate_requirements(task, results)

        cr = validation.criteria_results[0]
        assert cr.status == "verified"
        assert "OAuth2 handler" in cr.evidence

    def test_promises_preferred_over_requirements_met(self, tmp_worktree):
        """AC-002: completion_promises takes priority over requirements_met."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        results = {
            # Both strategies present — promises should win
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Done"},
                {"criterion_id": "AC-002", "status": "incomplete"},
            ],
            "requirements_met": ["Feature A", "Feature B"],  # Would match both
        }

        validation = validator.validate_requirements(task, results)

        # Promises say AC-002 incomplete, so it should be rejected
        # even though requirements_met has "Feature B"
        assert validation.criteria_met == 1
        assert validation.criteria_results[1].status == "rejected"

    def test_falls_back_to_text_when_no_promises(self, tmp_worktree):
        """AC-005: Falls back to requirements_met text matching when no promises."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        results = {
            "requirements_met": ["Feature A", "Feature B"],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True
        assert all(cr.status == "verified" for cr in validation.criteria_results)

    def test_empty_promises_falls_back_to_text(self, tmp_worktree):
        """AC-005: Empty promises list falls back to text matching."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {
            "completion_promises": [],
            "requirements_met": ["Feature A"],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.all_criteria_met is True

    def test_promises_from_player_report_file(self, tmp_worktree):
        """AC-002: Reads completion_promises from player_turn_N.json on disk."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        results = {"task_id": "TASK-001"}  # No promises in task_work_results

        # Write player report with promises
        player_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
        player_dir.mkdir(parents=True, exist_ok=True)
        player_report = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Done A"},
                {"criterion_id": "AC-002", "status": "complete", "evidence": "Done B"},
            ],
        }
        (player_dir / "player_turn_1.json").write_text(json.dumps(player_report))

        validation = validator.validate_requirements(task, results, turn=1)

        assert validation.all_criteria_met is True
        assert validation.criteria_met == 2

    def test_no_player_report_falls_back_to_text(self, tmp_worktree):
        """AC-005: No player report file falls back to text matching."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {
            "task_id": "TASK-NONEXISTENT",
            "requirements_met": ["Feature A"],
        }

        validation = validator.validate_requirements(task, results, turn=1)

        # Should fall back to text matching
        assert validation.all_criteria_met is True

    def test_promises_recovered_from_prior_turn_report(self, tmp_worktree):
        """TASK-FIX-AE7E Fix 1: Falls back to prior player_turn_N.json when current turn has no promises."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A", "Feature B"])
        # Current turn (turn 3) has no promises
        results = {"task_id": "TASK-001"}

        player_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
        player_dir.mkdir(parents=True, exist_ok=True)

        # Turn 1 had the full set of promises
        turn1_report = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete", "evidence": "Done A"},
                {"criterion_id": "AC-002", "status": "complete", "evidence": "Done B"},
            ],
        }
        (player_dir / "player_turn_1.json").write_text(json.dumps(turn1_report))
        # Turn 2 has no promises (iterative fix turn)
        (player_dir / "player_turn_2.json").write_text(json.dumps({}))

        # Turn 3 has no promises either — should recover from turn 1
        validation = validator.validate_requirements(task, results, turn=3)

        assert validation.all_criteria_met is True
        assert validation.criteria_met == 2

    def test_promises_fallback_logs_at_info(self, tmp_worktree, caplog):
        """TASK-FIX-AE7E Fix 1: Backward scan logs INFO when promises are recovered."""
        import logging

        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {"task_id": "TASK-001"}

        player_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
        player_dir.mkdir(parents=True, exist_ok=True)
        (player_dir / "player_turn_1.json").write_text(
            json.dumps({
                "completion_promises": [
                    {"criterion_id": "AC-001", "status": "complete", "evidence": "Done"},
                ],
            })
        )

        with caplog.at_level(logging.INFO):
            validator.validate_requirements(task, results, turn=2)

        assert any(
            "recovered from player_turn_1.json" in r.message for r in caplog.records
        )

    def test_no_prior_reports_returns_empty_and_falls_back_to_text(self, tmp_worktree):
        """TASK-FIX-AE7E Fix 1: No prior player reports — behaviour unchanged (text fallback)."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {
            "task_id": "TASK-001",
            "requirements_met": ["Feature A"],
        }

        # No player turn files exist at all
        validation = validator.validate_requirements(task, results, turn=3)

        # Falls back to text matching — unchanged behaviour
        assert validation.all_criteria_met is True

    def test_promise_id_format_matching(self, tmp_worktree):
        """AC-002: Criterion IDs are zero-padded (AC-001, AC-002, etc.)."""
        validator = CoachValidator(str(tmp_worktree))
        criteria = [f"Criterion {i}" for i in range(1, 11)]
        task = make_task(criteria)
        promises = [
            {"criterion_id": f"AC-{i:03d}", "status": "complete", "evidence": f"Done {i}"}
            for i in range(1, 11)
        ]
        results = {"completion_promises": promises}

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_met == 10
        assert validation.all_criteria_met is True
        assert validation.criteria_results[9].criterion_id == "AC-010"

    def test_promise_without_evidence_uses_default(self, tmp_worktree):
        """AC-003: Missing evidence field uses default message."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete"},
                # No evidence field
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_results[0].status == "verified"
        assert "AC-001" in validation.criteria_results[0].evidence

    def test_promise_with_unknown_status_rejected(self, tmp_worktree):
        """AC-004: Unknown promise status treated as not complete."""
        validator = CoachValidator(str(tmp_worktree))
        task = make_task(["Feature A"])
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "in_progress"},
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_results[0].status == "rejected"
        assert "in_progress" in validation.criteria_results[0].evidence

    def test_empty_acceptance_criteria_with_promises(self, tmp_worktree):
        """AC-005: Empty acceptance criteria returns empty results."""
        validator = CoachValidator(str(tmp_worktree))
        task = {"acceptance_criteria": []}
        results = {
            "completion_promises": [
                {"criterion_id": "AC-001", "status": "complete"},
            ],
        }

        validation = validator.validate_requirements(task, results)

        assert validation.criteria_total == 0
        assert validation.all_criteria_met is True


# ============================================================================
# Test Seam Test Recommendation (TASK-SFT-009)
# ============================================================================


class TestSeamTestRecommendation:
    """Test seam test recommendation feature in CoachValidator."""

    def test_seam_test_check_skipped_for_scaffolding(self, tmp_worktree):
        """Seam test check skipped when seam_tests_recommended=False."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.SCAFFOLDING)
        task_work_results = {
            "tests_written": ["tests/test_config.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        assert len(issues) == 0

    def test_seam_test_check_skipped_for_documentation(self, tmp_worktree):
        """Seam test check skipped for DOCUMENTATION task type."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.DOCUMENTATION)
        task_work_results = {
            "tests_written": [],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        assert len(issues) == 0

    def test_seam_test_check_runs_for_feature(self, tmp_worktree):
        """Seam test check runs when seam_tests_recommended=True (FEATURE)."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": ["tests/test_feature.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        # Should recommend seam tests since no seam/contract/boundary tests
        assert len(issues) == 1
        assert issues[0]["category"] == "seam_test_recommendation"
        assert issues[0]["severity"] == "consider"

    def test_seam_test_check_runs_for_refactor(self, tmp_worktree):
        """Seam test check runs when seam_tests_recommended=True (REFACTOR)."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.REFACTOR)
        task_work_results = {
            "tests_written": ["tests/test_migration.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        # Should recommend seam tests since no seam/contract/boundary tests
        assert len(issues) == 1
        assert issues[0]["category"] == "seam_test_recommendation"

    def test_no_warning_when_seam_tests_present(self, tmp_worktree):
        """No warning when seam tests are detected in tests_written."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": ["tests/test_seam_api.py", "tests/test_feature.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        # No warning - seam test detected
        assert len(issues) == 0

    def test_no_warning_with_contract_tests(self, tmp_worktree):
        """No warning when contract tests are present."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": ["tests/test_contract_validation.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        assert len(issues) == 0

    def test_no_warning_with_boundary_tests(self, tmp_worktree):
        """No warning when boundary tests are present."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": ["tests/test_boundary_checks.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        assert len(issues) == 0

    def test_no_warning_with_integration_tests(self, tmp_worktree):
        """No warning when integration tests are present (pattern match)."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": ["tests/test_integration_api.py"],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        assert len(issues) == 0

    def test_no_warning_when_no_tests_written(self, tmp_worktree):
        """No warning when tests_written is empty (other gates handle this)."""
        from guardkit.models.task_types import TaskType, get_profile

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)
        task_work_results = {
            "tests_written": [],
        }

        issues = validator._check_seam_test_recommendation(task_work_results, profile)

        # No warning - empty tests_written triggers zero-test anomaly instead
        assert len(issues) == 0

    def test_seam_test_recommendation_is_non_blocking(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Seam test recommendation does not block approval."""
        # Write passing task-work results without seam tests
        results = make_task_work_results()
        results["tests_written"] = ["tests/test_feature.py"]
        write_task_work_results(task_work_results_dir, results)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, make_task())

        # Should approve despite missing seam tests (soft gate)
        assert result.decision == "approve"
        # Should have recommendation in issues
        seam_issues = [
            i for i in result.issues if i["category"] == "seam_test_recommendation"
        ]
        assert len(seam_issues) == 1
        assert seam_issues[0]["severity"] == "consider"


# ============================================================================
# Test Cumulative Diff Fallback (TASK-ABF-004)
# ============================================================================


class TestCumulativeDiffFallback:
    """Test cumulative git diff fallback for test detection across checkpoints."""

    def test_cumulative_diff_finds_tests_across_checkpoints(self, tmp_worktree):
        """Cumulative diff finds test files created in earlier turns."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-001"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "abc123", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        # Create test files on disk
        tests_dir = tmp_worktree / "tests"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_oauth.py"
        test_file.write_text("def test_oauth(): pass")

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-001")

        # Mock git commands
        with patch("subprocess.run") as mock_run:
            # First call: git rev-parse abc123~1 -> returns parent hash
            # Second call: git diff --name-only parent HEAD -> returns test files
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout="parent_hash_xyz",
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout="tests/test_oauth.py\n",
                    stderr="",
                ),
            ]

            # Call with NO task_work_results (primary fails)
            # and pattern that won't match (glob fails)
            cmd = validator._detect_test_command(task_id="TASK-CD-001")

            # Should find test via cumulative diff
            assert cmd is not None
            assert "pytest" in cmd
            assert "tests/test_oauth.py" in cmd
            assert "-v" in cmd
            assert "--tb=short" in cmd

    def test_cumulative_diff_excludes_pre_task_files(self, tmp_worktree):
        """Cumulative diff excludes files that don't exist on disk."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-002"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "def456", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        # NOTE: test file is NOT created on disk

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-002")

        with patch("subprocess.run") as mock_run:
            # Mock git to return test file that doesn't exist on disk
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="parent_hash_456", stderr=""),
                MagicMock(returncode=0, stdout="tests/test_deleted.py\n", stderr=""),
            ]

            cmd = validator._detect_test_command(task_id="TASK-CD-002")

            # Should return None because file doesn't exist
            assert cmd is None

    def test_cumulative_diff_handles_no_checkpoints(self, tmp_worktree):
        """Cumulative diff gracefully handles missing checkpoints file."""
        # NOTE: No checkpoints.json created

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-003")

        # No mocking needed - should fail gracefully
        cmd = validator._detect_test_command(task_id="TASK-CD-003")

        # Should return None (no checkpoints file)
        assert cmd is None

    def test_cumulative_diff_handles_git_failure(self, tmp_worktree):
        """Cumulative diff gracefully handles git command failures."""
        # Set up checkpoints.json
        checkpoints_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-CD-004"
        checkpoints_dir.mkdir(parents=True)
        checkpoints_data = {
            "checkpoints": [
                {"commit_hash": "ghi789", "turn": 1, "phase": "implementation"}
            ]
        }
        (checkpoints_dir / "checkpoints.json").write_text(
            json.dumps(checkpoints_data, indent=2)
        )

        validator = CoachValidator(str(tmp_worktree), task_id="TASK-CD-004")

        with patch("subprocess.run") as mock_run:
            # Mock git rev-parse to fail
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: bad revision",
            )

            cmd = validator._detect_test_command(task_id="TASK-CD-004")

            # Should return None (git command failed)
            assert cmd is None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
