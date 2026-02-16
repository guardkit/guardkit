"""
Seam tests for AutoBuild → Coach Agent wiring.

This module verifies the data flow between the AutoBuild orchestrator and
CoachValidator, ensuring that:
1. Acceptance criteria flow from task files to CoachValidator.validate()
2. CoachValidator receives real QualityGateStatus objects
3. Player task-work results files are actually read (not mocked away)
4. Coach feedback propagates back to the turn loop
5. Zero-test anomaly detection fires when tasks have no test files

Historical Context:
    From failure pattern FP-002: Player self-report unreliability. In the g3
    ablation study, removing Coach made output non-functional despite Player
    claiming success. These seam tests ensure Coach actually receives the
    data it needs to validate independently.

Seam Definition:
    Layer A: AutoBuild orchestrator (_execute_turn(), turn loop)
    Layer B: Coach validation (CoachValidator.validate(), _invoke_coach_safely())
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    CoachValidationResult,
    QualityGateStatus,
    IndependentTestResult,
    RequirementsValidation,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree

pytestmark = pytest.mark.seam


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    """Create a temporary worktree directory with required structure."""
    worktree = tmp_path / "worktrees" / "TASK-S6-001"
    worktree.mkdir(parents=True)

    # Create required directories
    (worktree / ".guardkit" / "autobuild" / "TASK-S6-001").mkdir(parents=True)
    (worktree / "tests").mkdir(parents=True)

    # Create pyproject.toml to trigger pytest detection
    (worktree / "pyproject.toml").write_text("[tool.pytest]\n")

    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    """Return the task-work results directory."""
    return tmp_worktree / ".guardkit" / "autobuild" / "TASK-S6-001"


@pytest.fixture
def mock_worktree(tmp_worktree: Path) -> Mock:
    """Create a mock Worktree that points to our temp directory."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-S6-001"
    worktree.path = tmp_worktree
    worktree.branch_name = "autobuild/TASK-S6-001"
    worktree.base_branch = "main"
    return worktree


def make_task_work_results(
    tests_passed: bool = True,
    failed_count: int = 0,
    total_tests: int = 15,
    coverage_met: bool = True,
    line_coverage: int = 85,
    arch_score: int = 82,
    violations: int = 0,
    requirements_met: Optional[List[str]] = None,
    tests_written: Optional[List[str]] = None,
    task_id: str = "TASK-S6-001",
) -> Dict[str, Any]:
    """Create task-work results matching actual schema."""
    if not tests_passed and failed_count == 0:
        failed_count = 1

    passed_count = total_tests - failed_count
    return {
        "task_id": task_id,
        "quality_gates": {
            "tests_passing": tests_passed and failed_count == 0,
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "coverage": line_coverage,
            "coverage_met": coverage_met,
            "all_passed": tests_passed and coverage_met,
        },
        "code_review": {
            "score": arch_score,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        "plan_audit": {
            "violations": violations,
            "file_count_match": True,
        },
        "requirements_met": requirements_met or [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
        "tests_written": tests_written or ["tests/test_auth.py"],
        "files_created": ["src/auth.py", "tests/test_auth.py"],
        "files_modified": [],
    }


def write_task_work_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    """Write task-work results to file."""
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    return results_path


def make_player_report(
    task_id: str = "TASK-S6-001",
    turn: int = 1,
    tests_passed: bool = True,
    completion_promises: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a Player report for Coach validation."""
    return {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/auth.py"],
        "files_created": ["tests/test_auth.py"],
        "tests_written": ["tests/test_auth.py"],
        "tests_run": True,
        "tests_passed": tests_passed,
        "test_output_summary": "15 tests passed",
        "implementation_notes": "Implemented OAuth2 flow",
        "concerns": [],
        "requirements_addressed": ["OAuth2 authentication"],
        "requirements_remaining": [],
        "completion_promises": completion_promises or [
            {
                "criterion_id": "AC-001",
                "criterion_text": "OAuth2 authentication flow",
                "status": "complete",
                "evidence": "Implemented in src/auth.py",
                "test_file": "tests/test_auth.py",
                "implementation_files": ["src/auth.py"],
            }
        ],
    }


# ============================================================================
# Test: Acceptance Criteria Flow to CoachValidator
# ============================================================================


class TestAcceptanceCriteriaFlow:
    """Verify acceptance criteria flow from task to CoachValidator.validate()."""

    def test_acceptance_criteria_reaches_coach_validator(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: acceptance_criteria from task file reaches CoachValidator.validate() parameter.

        This tests the seam between AutoBuild's task parsing and Coach's validation.
        The CoachValidator must receive the actual acceptance criteria, not empty lists.
        """
        # Arrange: Write passing task-work results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Create test task data with explicit acceptance criteria
        acceptance_criteria = [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh mechanism",
        ]
        task = {"acceptance_criteria": acceptance_criteria}

        # Act: Create real CoachValidator and call validate
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="15 passed in 1.45s",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: Verify criteria were received and processed
        assert result.requirements is not None, "Requirements validation must be performed"
        assert result.requirements.criteria_total == 3, (
            f"Expected 3 criteria, got {result.requirements.criteria_total}"
        )

        # Verify each criterion was evaluated
        assert len(result.requirements.criteria_results) == 3
        for i, criterion_result in enumerate(result.requirements.criteria_results):
            assert criterion_result.criterion_text == acceptance_criteria[i], (
                f"Criterion {i} text mismatch: expected '{acceptance_criteria[i]}', "
                f"got '{criterion_result.criterion_text}'"
            )

    def test_empty_acceptance_criteria_handled_gracefully(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Verify CoachValidator handles empty acceptance criteria without error.

        This edge case ensures the seam doesn't break when tasks lack criteria.
        """
        # Arrange: Write passing results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Empty acceptance criteria
        task = {"acceptance_criteria": []}

        # Act: Validate with empty criteria
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: Should approve (no criteria to fail)
        assert result.requirements is not None
        assert result.requirements.criteria_total == 0
        assert result.requirements.all_criteria_met is True


# ============================================================================
# Test: QualityGateStatus Data Integrity
# ============================================================================


class TestQualityGateStatusIntegrity:
    """Verify CoachValidator receives real QualityGateStatus objects."""

    def test_coach_receives_real_quality_gate_status(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: CoachValidator receives real QualityGateStatus (not empty/default).

        This verifies the quality gate data actually flows through the seam,
        not being replaced with empty defaults somewhere in the pipeline.
        """
        # Arrange: Create specific quality gate values
        results = make_task_work_results(
            tests_passed=True,
            failed_count=0,
            total_tests=25,
            coverage_met=True,
            line_coverage=92,
            arch_score=88,
            violations=0,
        )
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": ["Test coverage >= 80%"]}

        # Act: Validate
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: Quality gates reflect actual values, not defaults
        assert result.quality_gates is not None, "QualityGateStatus must be present"
        assert result.quality_gates.tests_passed is True
        assert result.quality_gates.coverage_met is True
        assert result.quality_gates.arch_review_passed is True  # 88 >= 60 threshold
        assert result.quality_gates.plan_audit_passed is True
        assert result.quality_gates.all_gates_passed is True

    def test_failing_quality_gates_detected(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Verify failing quality gates are properly detected and reported.

        This ensures the seam doesn't silently swallow gate failures.
        """
        # Arrange: Create failing quality gates
        results = make_task_work_results(
            tests_passed=False,
            failed_count=3,
            total_tests=10,
            coverage_met=False,
            line_coverage=45,  # Below threshold
            arch_score=50,  # Below 60 threshold
            violations=2,  # Plan audit violations
        )
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": ["All tests pass"]}

        # Act: Validate
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
        result = validator.validate(
            task_id="TASK-S6-001",
            turn=1,
            task=task,
        )

        # Assert: Feedback decision with specific failures
        assert result.decision == "feedback"
        assert result.quality_gates is not None
        assert result.quality_gates.tests_passed is False
        assert result.quality_gates.coverage_met is False
        assert result.quality_gates.arch_review_passed is False
        assert result.quality_gates.all_gates_passed is False


# ============================================================================
# Test: Player Results File Reading
# ============================================================================


class TestPlayerResultsFileReading:
    """Verify Player task-work results file is actually read by Coach."""

    def test_task_work_results_file_is_read(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: Player task-work results file is actually read by Coach (not mocked away).

        This is the critical seam test: we write real data to disk and verify
        CoachValidator reads it. No mocking of the file read operation.
        """
        # Arrange: Write specific identifiable data
        unique_requirements = [
            "UNIQUE_REQ_A_12345",
            "UNIQUE_REQ_B_67890",
        ]
        results = make_task_work_results(requirements_met=unique_requirements)
        results_path = write_task_work_results(task_work_results_dir, results)

        # Verify file exists on disk
        assert results_path.exists(), "Results file must exist on disk"

        task = {"acceptance_criteria": unique_requirements}

        # Act: Use real CoachValidator (no mocking of read_quality_gate_results)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")

            # Directly call read_quality_gate_results to verify file read
            loaded_results = validator.read_quality_gate_results("TASK-S6-001")

        # Assert: Verify our unique data was read from the actual file
        assert "error" not in loaded_results, f"Failed to read results: {loaded_results.get('error')}"
        assert loaded_results.get("requirements_met") == unique_requirements, (
            "Requirements from file don't match what we wrote"
        )

    def test_missing_results_file_returns_error(
        self,
        tmp_worktree: Path,
    ):
        """
        Verify CoachValidator returns feedback when results file is missing.

        This tests the error path of the seam.
        """
        # Arrange: No results file written
        task = {"acceptance_criteria": ["Some criterion"]}

        # Act: Validate without results file
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
        result = validator.validate(
            task_id="TASK-S6-001",
            turn=1,
            task=task,
        )

        # Assert: Feedback with missing results error
        assert result.decision == "feedback"
        assert len(result.issues) > 0
        assert any(
            issue.get("category") == "missing_results"
            for issue in result.issues
        ), "Expected 'missing_results' issue category"


# ============================================================================
# Test: Coach Feedback Propagation
# ============================================================================


class TestCoachFeedbackPropagation:
    """Verify Coach feedback propagates back to the turn loop."""

    def test_feedback_decision_with_issues_propagates(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: Coach feedback is propagated back to the turn loop (not silently dropped).

        When Coach returns feedback, the issues must be accessible in the result,
        not lost in the seam between Coach and the orchestrator.
        """
        # Arrange: Create failing results
        results = make_task_work_results(
            tests_passed=False,
            failed_count=5,
            total_tests=20,
        )
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": ["All tests must pass"]}

        # Act: Validate
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
        result = validator.validate(
            task_id="TASK-S6-001",
            turn=1,
            task=task,
        )

        # Assert: Feedback with specific issues
        assert result.decision == "feedback"
        assert len(result.issues) > 0, "Issues must not be empty for feedback"
        assert result.rationale, "Rationale must be provided"

        # Verify specific issue details are preserved
        test_failure_issues = [
            i for i in result.issues
            if i.get("category") == "test_failure"
        ]
        assert len(test_failure_issues) > 0, "Test failure issue must be present"

    def test_approve_decision_includes_quality_data(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Verify approve decisions include quality gate data for transparency.
        """
        # Arrange: Create passing results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": ["OAuth2 authentication flow"]}

        # Act: Validate
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: Approve with full quality data
        assert result.decision == "approve"
        assert result.quality_gates is not None
        assert result.requirements is not None
        assert result.rationale, "Rationale must be provided even for approval"


# ============================================================================
# Test: Zero-Test Anomaly Detection
# ============================================================================


class TestZeroTestAnomalyDetection:
    """Verify zero-test anomaly detection fires when task has no test files."""

    def test_zero_test_anomaly_detected_when_no_tests_written(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        AC: Zero-test anomaly detection fires when task has no test files.

        This catches the scenario where Player claims tests pass but wrote
        no tests. The CoachValidator must detect this anomaly.

        The zero-test anomaly check happens AFTER requirements validation,
        so we must ensure requirements pass first for the test to reach
        the anomaly check.
        """
        # Arrange: Requirements that will pass validation
        feature_criterion = "OAuth2 authentication flow"
        results = make_task_work_results(
            tests_passed=True,
            total_tests=0,
            coverage_met=True,
            tests_written=[],  # No tests written!
            requirements_met=[feature_criterion],  # Matches acceptance criteria
        )
        # Modify quality_gates to trigger zero-test anomaly
        results["quality_gates"]["tests_passed"] = 0
        results["quality_gates"]["coverage"] = None  # No coverage data
        results["quality_gates"]["all_passed"] = True  # But claims all passed

        write_task_work_results(task_work_results_dir, results)

        # Acceptance criteria that matches requirements_met
        task = {"acceptance_criteria": [feature_criterion]}

        # Act: Validate (independent tests will be skipped due to no task-specific tests)
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
        result = validator.validate(
            task_id="TASK-S6-001",
            turn=1,
            task=task,
        )

        # Assert: Zero-test anomaly should be detected
        # The anomaly check triggers on: all_passed=True, tests_passed=0, coverage=None
        assert result.decision == "feedback", (
            f"Zero-test anomaly should result in feedback, not {result.decision}. "
            f"Issues: {result.issues}, Rationale: {result.rationale}"
        )

        zero_test_issues = [
            i for i in result.issues
            if i.get("category") == "zero_test_anomaly"
        ]
        assert len(zero_test_issues) > 0, (
            f"Expected zero_test_anomaly issue, got issues: {result.issues}"
        )

    def test_no_anomaly_when_tests_exist(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Verify no anomaly is flagged when tests are actually written.
        """
        # Arrange: Results with tests written
        results = make_task_work_results(
            tests_passed=True,
            total_tests=10,
            coverage_met=True,
            tests_written=["tests/test_feature.py"],
        )
        write_task_work_results(task_work_results_dir, results)

        # Create actual test file for independent verification
        test_file = tmp_worktree / "tests" / "test_feature.py"
        test_file.write_text("def test_example(): pass\n")

        task = {"acceptance_criteria": ["Feature implemented"]}

        # Act: Validate with real test file
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: No zero-test anomaly
        zero_test_issues = [
            i for i in result.issues
            if i.get("category") == "zero_test_anomaly"
        ]
        assert len(zero_test_issues) == 0, (
            f"Unexpected zero_test_anomaly when tests exist: {zero_test_issues}"
        )


# ============================================================================
# Test: Real CoachValidator with Mocked Agent Invocation
# ============================================================================


class TestRealCoachValidatorIntegration:
    """
    Test using real CoachValidator with mocked agent invocation.

    AC: Tests use real CoachValidator instance with mocked agent invocation
    (mock the Claude API call, not the validator logic).
    """

    def test_coach_validator_used_directly_not_via_sdk(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        mock_worktree: Mock,
    ):
        """
        Verify CoachValidator is used directly in _invoke_coach_safely.

        This test ensures the orchestrator's seam to Coach uses CoachValidator
        (lightweight validation) rather than full SDK invocation.
        """
        # Arrange: Write results
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        # Create orchestrator with mocked dependencies
        mock_worktree_manager = Mock()
        mock_worktree_manager.create.return_value = mock_worktree
        mock_progress_display = Mock()
        mock_progress_display.__enter__ = Mock(return_value=mock_progress_display)
        mock_progress_display.__exit__ = Mock(return_value=False)
        mock_progress_display.start_turn = Mock()
        mock_progress_display.complete_turn = Mock()
        mock_progress_display.console = Mock()
        mock_progress_display.console.print = Mock()

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_worktree.parent.parent,
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            progress_display=mock_progress_display,
            enable_context=False,  # Disable Graphiti context
        )

        player_report = make_player_report()

        # Act: Call _invoke_coach_safely with mocked subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            result = orchestrator._invoke_coach_safely(
                task_id="TASK-S6-001",
                turn=1,
                requirements="Implement OAuth2 flow",
                player_report=player_report,
                worktree=mock_worktree,
                acceptance_criteria=["OAuth2 authentication flow"],
            )

        # Assert: Result came from CoachValidator, not SDK
        assert result.success is True, f"Expected success, got error: {result.error}"
        assert result.agent_type == "coach"

        # Verify the report contains CoachValidator-specific structure
        report = result.report
        assert "validation_results" in report, "CoachValidator report must have validation_results"
        assert report.get("decision") in ["approve", "feedback"]

    def test_orchestrator_passes_acceptance_criteria_to_coach(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        mock_worktree: Mock,
    ):
        """
        Verify orchestrator passes acceptance_criteria through to Coach.

        This is the end-to-end seam test: criteria flow from orchestrator
        through to CoachValidator.validate().
        """
        # Arrange: Write results with specific criteria
        criteria_to_test = [
            "Criterion Alpha",
            "Criterion Beta",
            "Criterion Gamma",
        ]
        results = make_task_work_results(requirements_met=criteria_to_test)
        write_task_work_results(task_work_results_dir, results)

        # Setup orchestrator
        mock_worktree_manager = Mock()
        mock_worktree_manager.create.return_value = mock_worktree
        mock_progress_display = Mock()
        mock_progress_display.__enter__ = Mock(return_value=mock_progress_display)
        mock_progress_display.__exit__ = Mock(return_value=False)
        mock_progress_display.start_turn = Mock()
        mock_progress_display.complete_turn = Mock()
        mock_progress_display.console = Mock()
        mock_progress_display.console.print = Mock()

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_worktree.parent.parent,
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            progress_display=mock_progress_display,
            enable_context=False,
        )

        player_report = make_player_report()

        # Act: Invoke with specific acceptance criteria
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            result = orchestrator._invoke_coach_safely(
                task_id="TASK-S6-001",
                turn=1,
                requirements="Test requirements",
                player_report=player_report,
                worktree=mock_worktree,
                acceptance_criteria=criteria_to_test,
            )

        # Assert: Criteria were processed
        assert result.success
        report = result.report

        # Check criteria verification in report
        validation_results = report.get("validation_results", {})
        requirements = validation_results.get("requirements", {})
        assert requirements.get("criteria_total") == 3, (
            f"Expected 3 criteria, got {requirements.get('criteria_total')}"
        )


# ============================================================================
# Test: Complete Data Flow Verification
# ============================================================================


class TestCompleteDataFlow:
    """
    Integration tests verifying complete data flow across the seam.

    These tests verify the full pipeline from task data to Coach decision,
    ensuring no data is lost at any point in the seam.
    """

    def test_complete_approval_flow(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Test complete flow from task data to approve decision.
        """
        # Arrange: Full passing scenario
        acceptance_criteria = [
            "User can authenticate via OAuth2",
            "Tokens are generated securely",
            "Token refresh works correctly",
        ]

        results = make_task_work_results(
            requirements_met=acceptance_criteria,
            tests_passed=True,
            coverage_met=True,
            arch_score=85,
            violations=0,
        )
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": acceptance_criteria}

        # Act: Full validation
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="15 passed", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        # Assert: Complete approval with all data intact
        assert result.decision == "approve"
        assert result.task_id == "TASK-S6-001"
        assert result.turn == 1
        assert result.quality_gates is not None
        assert result.quality_gates.all_gates_passed is True
        assert result.requirements is not None
        assert result.requirements.criteria_total == 3
        assert result.independent_tests is not None

    def test_complete_feedback_flow(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Test complete flow from failing data to feedback decision.
        """
        # Arrange: Failing scenario
        acceptance_criteria = ["All tests must pass"]

        results = make_task_work_results(
            tests_passed=False,
            failed_count=5,
            coverage_met=False,
            arch_score=40,  # Below threshold
            violations=3,
        )
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": acceptance_criteria}

        # Act: Full validation
        validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
        result = validator.validate(
            task_id="TASK-S6-001",
            turn=1,
            task=task,
        )

        # Assert: Feedback with all failure data intact
        assert result.decision == "feedback"
        assert result.task_id == "TASK-S6-001"
        assert result.quality_gates is not None
        assert result.quality_gates.all_gates_passed is False
        assert len(result.issues) > 0
        assert result.rationale, "Feedback must include rationale"

    def test_serialization_preserves_data(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ):
        """
        Verify to_dict() serialization preserves all validation data.

        This ensures data isn't lost when passing through JSON serialization
        boundaries in the orchestrator.
        """
        # Arrange
        results = make_task_work_results()
        write_task_work_results(task_work_results_dir, results)

        task = {"acceptance_criteria": ["Test criterion"]}

        # Act: Validate and serialize
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            validator = CoachValidator(str(tmp_worktree), task_id="TASK-S6-001")
            result = validator.validate(
                task_id="TASK-S6-001",
                turn=1,
                task=task,
            )

        serialized = result.to_dict()

        # Assert: All required fields present in serialized form
        assert serialized["task_id"] == "TASK-S6-001"
        assert serialized["turn"] == 1
        assert serialized["decision"] in ["approve", "feedback"]
        assert "validation_results" in serialized
        assert "quality_gates" in serialized["validation_results"]
        assert "requirements" in serialized["validation_results"]
        assert "rationale" in serialized
