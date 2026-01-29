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
        "requirements_met": requirements_met or [
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

        # Verify task-specific test file was used
        call_args = mock_run.call_args[0][0]
        assert "test_task_abc_001.py" in call_args
        assert "tests/ " not in call_args  # Full directory not used

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
# Graphiti Threshold Integration Tests (TASK-GE-005)
# ============================================================================


class TestGraphitiThresholdIntegration:
    """Test CoachValidator integration with Graphiti quality gate thresholds.

    These tests verify that CoachValidator correctly:
    - Queries Graphiti for task-type/complexity-based thresholds
    - Uses Graphiti thresholds when available
    - Falls back to default profiles when Graphiti unavailable
    - Logs threshold usage for audit trail
    """

    @pytest.mark.asyncio
    async def test_get_graphiti_thresholds_returns_profile_when_config_found(self):
        """Test that get_graphiti_thresholds returns a profile when Graphiti config exists."""
        # Import the actual module for patching
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            # Create a mock QualityGateConfigFact
            mock_config = MagicMock()
            mock_config.id = "QG-FEATURE-MED"
            mock_config.test_pass_required = True
            mock_config.coverage_required = True
            mock_config.arch_review_required = True
            mock_config.arch_review_threshold = 50
            mock_config.coverage_threshold = 75.0

            mock_get_config.return_value = mock_config

            # Call the method
            profile = await CoachValidator.get_graphiti_thresholds("feature", 5)

            # Verify correct profile returned
            assert profile is not None
            assert profile.arch_review_threshold == 50
            assert profile.coverage_threshold == 75.0
            assert profile.tests_required is True
            assert profile.arch_review_required is True

            # Verify Graphiti was queried correctly
            mock_get_config.assert_called_once_with("feature", 5)

    @pytest.mark.asyncio
    async def test_get_graphiti_thresholds_returns_none_when_no_config(self):
        """Test that get_graphiti_thresholds returns None when no config found."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            mock_get_config.return_value = None

            profile = await CoachValidator.get_graphiti_thresholds("unknown_type", 5)

            assert profile is None
            mock_get_config.assert_called_once_with("unknown_type", 5)

    @pytest.mark.asyncio
    async def test_get_graphiti_thresholds_returns_none_when_graphiti_disabled(self):
        """Test graceful handling when Graphiti is disabled."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.GRAPHITI_AVAILABLE", False):
            profile = await CoachValidator.get_graphiti_thresholds("feature", 5)
            assert profile is None

    @pytest.mark.asyncio
    async def test_get_graphiti_thresholds_handles_query_error(self):
        """Test that query errors are handled gracefully."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Graphiti connection error")

            # Should not raise, should return None
            profile = await CoachValidator.get_graphiti_thresholds("feature", 5)
            assert profile is None

    @pytest.mark.asyncio
    async def test_get_graphiti_thresholds_uses_default_threshold_when_none(self):
        """Test that default values are used when config has None thresholds."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.id = "QG-SCAFFOLDING-LOW"
            mock_config.test_pass_required = True
            mock_config.coverage_required = False
            mock_config.arch_review_required = False
            mock_config.arch_review_threshold = None  # None in config
            mock_config.coverage_threshold = None  # None in config

            mock_get_config.return_value = mock_config

            profile = await CoachValidator.get_graphiti_thresholds("scaffolding", 2)

            # Should use default values when config has None
            assert profile.arch_review_threshold == 60  # Default
            assert profile.coverage_threshold == 80.0  # Default

    @pytest.mark.asyncio
    async def test_validate_async_uses_graphiti_profile(self, tmp_worktree, task_work_results_dir):
        """Test that validate_async uses Graphiti profile when available."""
        # Create valid task-work results
        results = make_task_work_results(
            tests_passed=True,
            coverage_met=True,
            arch_score=60,  # Would fail default 60 threshold but pass 50 threshold
        )
        results_file = task_work_results_dir / "task_work_results.json"
        results_file.write_text(json.dumps(results))

        # Create acceptance criteria file
        task = {
            "id": "TASK-001",
            "task_type": "feature",
            "complexity": 5,  # Medium complexity
            "acceptance_criteria": ["Criteria 1", "Criteria 2"],
        }

        # Patch the Graphiti query to return medium feature profile
        with patch.object(CoachValidator, "get_graphiti_thresholds") as mock_thresholds:
            from guardkit.orchestrator.quality_gates.profiles import QualityGateProfile

            mock_thresholds.return_value = QualityGateProfile(
                tests_required=True,
                coverage_required=True,
                arch_review_required=True,
                plan_audit_required=True,
                arch_review_threshold=50,  # Lower threshold from Graphiti
                coverage_threshold=75.0,
            )

            validator = CoachValidator(str(tmp_worktree))
            result = await validator.validate_async("TASK-001", 1, task)

            # Verify Graphiti was queried with correct parameters
            mock_thresholds.assert_called_once_with("feature", 5)

    @pytest.mark.asyncio
    async def test_validate_async_falls_back_to_default_when_graphiti_unavailable(
        self, tmp_worktree, task_work_results_dir
    ):
        """Test that validate_async falls back to default profile when Graphiti unavailable."""
        results = make_task_work_results(tests_passed=True, coverage_met=True, arch_score=82)
        results_file = task_work_results_dir / "task_work_results.json"
        results_file.write_text(json.dumps(results))

        task = {
            "id": "TASK-001",
            "task_type": "feature",
            "complexity": 5,
            "acceptance_criteria": ["Criteria 1"],
        }

        # Patch Graphiti to return None (unavailable)
        with patch.object(CoachValidator, "get_graphiti_thresholds") as mock_thresholds:
            mock_thresholds.return_value = None

            validator = CoachValidator(str(tmp_worktree))
            result = await validator.validate_async("TASK-001", 1, task)

            # Should still complete validation using default profile
            mock_thresholds.assert_called_once()
            # Result should reflect default profile being used
            # (default feature profile is used via _resolve_task_type)


class TestQualityGateConfigIntegration:
    """Integration tests verifying QualityGateConfigFact works with CoachValidator."""

    @pytest.mark.asyncio
    async def test_scaffolding_task_gets_relaxed_thresholds(self):
        """Test that scaffolding tasks get relaxed quality gate thresholds."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            # Return scaffolding config
            mock_config = MagicMock()
            mock_config.id = "QG-SCAFFOLDING-LOW"
            mock_config.test_pass_required = True
            mock_config.coverage_required = False
            mock_config.arch_review_required = False
            mock_config.arch_review_threshold = None
            mock_config.coverage_threshold = None

            mock_get_config.return_value = mock_config

            profile = await CoachValidator.get_graphiti_thresholds("scaffolding", 2)

            assert profile.arch_review_required is False
            assert profile.coverage_required is False

    @pytest.mark.asyncio
    async def test_high_complexity_feature_gets_strict_thresholds(self):
        """Test that high complexity features get strict quality gate thresholds."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            # Return high complexity feature config
            mock_config = MagicMock()
            mock_config.id = "QG-FEATURE-HIGH"
            mock_config.test_pass_required = True
            mock_config.coverage_required = True
            mock_config.arch_review_required = True
            mock_config.arch_review_threshold = 70  # High threshold
            mock_config.coverage_threshold = 80.0

            mock_get_config.return_value = mock_config

            profile = await CoachValidator.get_graphiti_thresholds("feature", 8)

            assert profile.arch_review_required is True
            assert profile.arch_review_threshold == 70
            assert profile.coverage_threshold == 80.0

    @pytest.mark.asyncio
    async def test_docs_task_bypasses_most_gates(self):
        """Test that documentation tasks have relaxed quality gates."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator.get_quality_gate_config") as mock_get_config:
            # Return docs config
            mock_config = MagicMock()
            mock_config.id = "QG-DOCS"
            mock_config.test_pass_required = False
            mock_config.coverage_required = False
            mock_config.arch_review_required = False
            mock_config.arch_review_threshold = None
            mock_config.coverage_threshold = None

            mock_get_config.return_value = mock_config

            profile = await CoachValidator.get_graphiti_thresholds("docs", 3)

            assert profile.tests_required is False
            assert profile.coverage_required is False
            assert profile.arch_review_required is False


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
