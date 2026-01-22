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
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
