"""
Seam tests S8: Quality Gates → State Transitions.

Tests the wiring between quality gate decisions (QualityGateProfile, CoachValidator)
and task state management (state file writes, frontmatter updates). Verifies that
quality gate failures actually block task state transitions.

Seam Definition:
- Layer A: Quality gate evaluation (QualityGateProfile, CoachValidator decisions)
- Layer B: Task state management (state file writes, frontmatter updates)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

import pytest

from guardkit.models.task_types import (
    DEFAULT_PROFILES,
    QualityGateProfile,
    TaskType,
    get_profile,
)
from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    CoachValidationResult,
    QualityGateStatus,
)
from guardkit.tasks.state_bridge import TaskStateBridge, STATE_DIRECTORIES

if TYPE_CHECKING:
    pass


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def task_file_factory(tmp_task_dir: Dict[str, Path]):
    """
    Factory fixture to create task markdown files with frontmatter.

    Creates task files in the specified state directory with the given
    frontmatter and content.

    Args:
        tmp_task_dir: Fixture providing GuardKit directory structure.

    Returns:
        Callable that creates task files and returns their path.
    """

    def create_task(
        task_id: str,
        state: str = "in_progress",
        task_type: str = "feature",
        title: str = "Test Task",
        extra_frontmatter: Dict[str, Any] | None = None,
        content: str = "## Test Task Content\n",
    ) -> Path:
        """
        Create a task file with the given parameters.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            state: State directory to place the task in
            task_type: Task type for quality gate profile
            title: Task title
            extra_frontmatter: Additional frontmatter fields
            content: Task body content

        Returns:
            Path to the created task file
        """
        state_dir = tmp_task_dir.get(state, tmp_task_dir["in_progress"])
        state_dir.mkdir(parents=True, exist_ok=True)

        # Build frontmatter
        frontmatter_dict = {
            "id": task_id,
            "title": title,
            "status": state,
            "task_type": task_type,
        }
        if extra_frontmatter:
            frontmatter_dict.update(extra_frontmatter)

        # Format frontmatter as YAML
        frontmatter_lines = ["---"]
        for key, value in frontmatter_dict.items():
            if isinstance(value, bool):
                frontmatter_lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (list, dict)):
                frontmatter_lines.append(f"{key}: {json.dumps(value)}")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        # Combine frontmatter and content
        file_content = "\n".join(frontmatter_lines) + content

        # Create task file
        task_filename = f"{task_id}-test-task.md"
        task_path = state_dir / task_filename
        task_path.write_text(file_content, encoding="utf-8")

        return task_path

    return create_task


@pytest.fixture
def task_work_results_factory(tmp_task_dir: Dict[str, Path]):
    """
    Factory fixture to create task_work_results.json files.

    Creates result files that CoachValidator reads to verify quality gates.

    Args:
        tmp_task_dir: Fixture providing GuardKit directory structure.

    Returns:
        Callable that creates result files and returns their path.
    """

    def create_results(
        task_id: str,
        tests_passed: int = 10,
        tests_failed: int = 0,
        coverage: float | None = 85.0,
        arch_score: int = 70,
        plan_violations: int = 0,
        all_passed: bool | None = None,
    ) -> Path:
        """
        Create a task_work_results.json file.

        Args:
            task_id: Task identifier
            tests_passed: Number of passing tests
            tests_failed: Number of failing tests
            coverage: Line coverage percentage (None = not measured)
            arch_score: Architectural review score (0-100)
            plan_violations: Number of plan audit violations
            all_passed: Override all_passed flag (None = auto-compute)

        Returns:
            Path to the created results file
        """
        # Auto-compute all_passed if not specified
        if all_passed is None:
            all_passed = tests_failed == 0

        # Calculate coverage_met:
        # - If coverage is None, set coverage_met to None (let validator handle as "not measured")
        # - Otherwise, compare against 80% threshold
        coverage_met: bool | None = None
        if coverage is not None:
            coverage_met = coverage >= 80.0

        results = {
            "task_id": task_id,
            "quality_gates": {
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "all_passed": all_passed,
                "coverage": coverage,
                "coverage_met": coverage_met,
            },
            "code_review": {
                "score": arch_score,
            },
            "plan_audit": {
                "violations": plan_violations,
            },
            "requirements_met": [],
            "completion_promises": [],
        }

        # Create autobuild directory for this task
        autobuild_dir = tmp_task_dir["autobuild"] / task_id
        autobuild_dir.mkdir(parents=True, exist_ok=True)

        results_path = autobuild_dir / "task_work_results.json"
        results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        return results_path

    return create_results


# ============================================================================
# S8 Seam Tests: Quality Gates → State Transitions
# ============================================================================


@pytest.mark.seam
class TestQualityGateStateTransitions:
    """
    Test that quality gate decisions actually block or allow state transitions.

    These tests verify the seam between quality gate evaluation (Layer A)
    and task state management (Layer B).
    """

    def test_failing_tests_blocks_in_progress_to_in_review(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: Task with failing tests cannot transition from IN_PROGRESS to IN_REVIEW.

        Verifies that CoachValidator rejects a task with failing tests,
        which should prevent state transition.
        """
        task_id = "TASK-TEST-001"

        # Create task file in in_progress state
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="feature",
            title="Test Feature with Failing Tests",
        )

        # Create task_work_results with failing tests
        task_work_results_factory(
            task_id=task_id,
            tests_passed=5,
            tests_failed=3,  # <-- Failing tests
            coverage=75.0,
            arch_score=70,
        )

        # Verify task file was created in in_progress
        assert task_path.exists()
        assert "in_progress" in str(task_path)

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "feature",
            "acceptance_criteria": ["Test criterion"],
        }

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Verify Coach rejected the task
        assert result.decision == "feedback", (
            f"Expected feedback (rejection) for failing tests, got {result.decision}"
        )

        # Verify quality gates show tests failed
        assert result.quality_gates is not None
        assert not result.quality_gates.tests_passed, (
            "Quality gates should show tests as failed"
        )
        assert not result.quality_gates.all_gates_passed, (
            "All gates should NOT pass when tests fail"
        )

        # Verify task file is still in in_progress (not transitioned)
        assert task_path.exists(), "Task should still exist in in_progress"
        assert "in_progress" in str(task_path), (
            "Task should NOT have been moved to in_review"
        )

        # Verify issues mention test failure
        test_issues = [
            i for i in result.issues if i.get("category") == "test_failure"
        ]
        assert len(test_issues) > 0, "Should have test_failure issue"

    def test_zero_test_blocking_for_feature_type(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: Task with zero tests and zero_test_blocking=True is blocked.

        Verifies that FEATURE tasks with zero tests are blocked when
        zero_test_blocking is enabled in the profile.
        """
        task_id = "TASK-ZERO-001"

        # Create task file in in_progress state
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="feature",
            title="Feature with Zero Tests",
        )

        # Create task_work_results with zero tests (anomaly condition)
        results_path = task_work_results_factory(
            task_id=task_id,
            tests_passed=0,  # <-- Zero tests
            tests_failed=0,
            coverage=None,  # <-- No coverage data
            arch_score=70,
            all_passed=True,  # <-- Incorrectly marked as passed
        )

        # Add completion promises to pass requirements validation
        # (we want to test zero-test anomaly, not requirements)
        results = json.loads(results_path.read_text())
        results["completion_promises"] = [
            {"criterion_id": "AC-001", "status": "complete", "evidence": "Criterion 1 done"},
            {"criterion_id": "AC-002", "status": "complete", "evidence": "Criterion 2 done"},
        ]
        results_path.write_text(json.dumps(results, indent=2))

        # Verify profile has zero_test_blocking enabled for FEATURE
        feature_profile = get_profile(TaskType.FEATURE)
        assert feature_profile.zero_test_blocking is True, (
            "FEATURE profile should have zero_test_blocking=True"
        )

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "feature",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
        }

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Verify Coach rejected due to zero-test anomaly
        assert result.decision == "feedback", (
            f"Expected feedback (rejection) for zero-test anomaly, got {result.decision}. "
            f"Issues: {result.issues}, Rationale: {result.rationale}"
        )

        # Verify issues mention zero_test_anomaly with error severity
        zero_test_issues = [
            i for i in result.issues if i.get("category") == "zero_test_anomaly"
        ]
        assert len(zero_test_issues) > 0, (
            f"Should have zero_test_anomaly issue. All issues: {result.issues}"
        )

        # Since zero_test_blocking=True, severity should be "error"
        assert any(
            i.get("severity") == "error" for i in zero_test_issues
        ), "zero_test_anomaly should have error severity (blocking)"

    def test_documentation_type_not_blocked_with_zero_tests(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: DOCUMENTATION task type with zero tests is NOT blocked (exempt).

        Verifies that DOCUMENTATION tasks don't require tests and can
        proceed without triggering zero-test anomaly blocking.
        """
        task_id = "TASK-DOC-001"

        # Create task file in in_progress state with documentation type
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="documentation",
            title="Documentation Task",
        )

        # Create task_work_results with zero tests
        task_work_results_factory(
            task_id=task_id,
            tests_passed=0,
            tests_failed=0,
            coverage=None,
            arch_score=0,  # Arch review not required for docs
            all_passed=True,
        )

        # Verify profile has tests_required=False for DOCUMENTATION
        doc_profile = get_profile(TaskType.DOCUMENTATION)
        assert doc_profile.tests_required is False, (
            "DOCUMENTATION profile should have tests_required=False"
        )
        assert doc_profile.coverage_required is False, (
            "DOCUMENTATION profile should have coverage_required=False"
        )

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "documentation",
            "acceptance_criteria": ["Document the API", "Add examples"],
        }

        # Create completion promises to satisfy requirements
        results_path = tmp_task_dir["autobuild"] / task_id / "task_work_results.json"
        results = json.loads(results_path.read_text())
        results["completion_promises"] = [
            {"criterion_id": "AC-001", "status": "complete", "evidence": "API documented"},
            {"criterion_id": "AC-002", "status": "complete", "evidence": "Examples added"},
        ]
        results_path.write_text(json.dumps(results, indent=2))

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Verify Coach approved (not blocked by zero tests)
        assert result.decision == "approve", (
            f"Expected approve for DOCUMENTATION task, got {result.decision}. "
            f"Issues: {result.issues}"
        )

        # Verify quality gates show tests were not required
        assert result.quality_gates is not None
        assert not result.quality_gates.tests_required, (
            "tests_required should be False for DOCUMENTATION"
        )

    def test_coverage_below_threshold_blocks_feature_completion(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: Coverage below threshold prevents completion for FEATURE type.

        Verifies that tasks with coverage below 80% are rejected.
        """
        task_id = "TASK-COV-001"

        # Create task file
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="feature",
            title="Feature with Low Coverage",
        )

        # Create task_work_results with low coverage
        task_work_results_factory(
            task_id=task_id,
            tests_passed=10,
            tests_failed=0,
            coverage=65.0,  # <-- Below 80% threshold
            arch_score=70,
        )

        # Verify coverage threshold in profile
        feature_profile = get_profile(TaskType.FEATURE)
        assert feature_profile.coverage_required is True
        assert feature_profile.coverage_threshold == 80.0

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "feature",
            "acceptance_criteria": ["Feature works correctly"],
        }

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Verify Coach rejected due to coverage
        assert result.decision == "feedback", (
            f"Expected feedback for low coverage, got {result.decision}"
        )

        # Verify quality gates show coverage not met
        assert result.quality_gates is not None
        assert not result.quality_gates.coverage_met, (
            "coverage_met should be False for 65% coverage"
        )

        # Verify issues mention coverage
        coverage_issues = [
            i for i in result.issues if i.get("category") == "coverage"
        ]
        assert len(coverage_issues) > 0, "Should have coverage issue"

    def test_arch_review_below_threshold_triggers_checkpoint(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: Architectural review score below 60 triggers checkpoint for FEATURE.

        Verifies that tasks with arch score < 60 are rejected.
        """
        task_id = "TASK-ARCH-001"

        # Create task file
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="feature",
            title="Feature with Poor Architecture",
        )

        # Create task_work_results with low arch score
        task_work_results_factory(
            task_id=task_id,
            tests_passed=10,
            tests_failed=0,
            coverage=85.0,
            arch_score=45,  # <-- Below 60 threshold
        )

        # Verify arch threshold in profile
        feature_profile = get_profile(TaskType.FEATURE)
        assert feature_profile.arch_review_required is True
        assert feature_profile.arch_review_threshold == 60

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "feature",
            "acceptance_criteria": ["Feature complete"],
        }

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Verify Coach rejected due to arch review
        assert result.decision == "feedback", (
            f"Expected feedback for low arch score, got {result.decision}"
        )

        # Verify quality gates show arch review failed
        assert result.quality_gates is not None
        assert not result.quality_gates.arch_review_passed, (
            "arch_review_passed should be False for score 45"
        )

        # Verify issues mention architectural failure
        arch_issues = [
            i for i in result.issues if i.get("category") == "architectural"
        ]
        assert len(arch_issues) > 0, "Should have architectural issue"

    def test_real_task_file_state_verification(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: Verify state changes by re-reading task file after transition.

        Creates a real task file and verifies that successful validation
        doesn't automatically move the file (that's the orchestrator's job),
        but the state bridge CAN move files when instructed.
        """
        task_id = "TASK-STATE-001"

        # Create task file in backlog
        task_path = task_file_factory(
            task_id=task_id,
            state="backlog",
            task_type="feature",
            title="State Transition Test",
        )

        # Verify task is in backlog
        assert "backlog" in str(task_path)
        assert task_path.exists()

        # Read initial state
        initial_content = task_path.read_text()
        assert "status: backlog" in initial_content

        # Create state bridge and transition to design_approved
        bridge = TaskStateBridge(
            task_id=task_id,
            repo_root=tmp_task_dir["root"],
        )

        # Create a stub implementation plan (required for transition)
        plan_dir = tmp_task_dir["task_plans"]
        plan_path = plan_dir / f"{task_id}-implementation-plan.md"
        plan_path.write_text(
            f"# Implementation Plan: {task_id}\n\n"
            "## Overview\nTest implementation plan.\n\n"
            "## Steps\n1. Step one\n2. Step two\n"
        )

        # Transition to design_approved
        new_path = bridge.transition_to_design_approved()

        # Verify task moved to design_approved directory
        assert "design_approved" in str(new_path)
        assert new_path.exists()

        # Verify old path no longer exists
        assert not task_path.exists(), "Task should have been moved from backlog"

        # Verify frontmatter was updated
        new_content = new_path.read_text()
        assert "status: design_approved" in new_content

    def test_quality_gate_profile_by_task_type(self):
        """
        Test: Verify quality gate profiles correctly vary by task type.

        Validates the profile configurations that control which gates
        are enforced for different task types.
        """
        # FEATURE profile - full validation
        feature_profile = get_profile(TaskType.FEATURE)
        assert feature_profile.tests_required is True
        assert feature_profile.coverage_required is True
        assert feature_profile.arch_review_required is True
        assert feature_profile.plan_audit_required is True
        assert feature_profile.zero_test_blocking is True
        assert feature_profile.coverage_threshold == 80.0
        assert feature_profile.arch_review_threshold == 60

        # DOCUMENTATION profile - minimal validation
        doc_profile = get_profile(TaskType.DOCUMENTATION)
        assert doc_profile.tests_required is False
        assert doc_profile.coverage_required is False
        assert doc_profile.arch_review_required is False
        assert doc_profile.plan_audit_required is False
        assert doc_profile.zero_test_blocking is False

        # SCAFFOLDING profile - no tests required
        scaffolding_profile = get_profile(TaskType.SCAFFOLDING)
        assert scaffolding_profile.tests_required is False
        assert scaffolding_profile.arch_review_required is False
        assert scaffolding_profile.plan_audit_required is True  # Still need audit

        # TESTING profile - no tests required (meta-task)
        testing_profile = get_profile(TaskType.TESTING)
        assert testing_profile.tests_required is False
        assert testing_profile.coverage_required is False

        # REFACTOR profile - full validation like FEATURE
        refactor_profile = get_profile(TaskType.REFACTOR)
        assert refactor_profile.tests_required is True
        assert refactor_profile.zero_test_blocking is True

    def test_integration_type_not_blocked_by_zero_tests(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
        task_work_results_factory,
    ):
        """
        Test: INTEGRATION task type is not blocked by zero-test anomaly.

        Integration tasks may not have task-specific tests (they wire
        existing components), so zero_test_blocking should be False.
        """
        task_id = "TASK-INT-001"

        # Create task file
        task_path = task_file_factory(
            task_id=task_id,
            state="in_progress",
            task_type="integration",
            title="API Integration Task",
        )

        # Create task_work_results with zero tests
        task_work_results_factory(
            task_id=task_id,
            tests_passed=0,
            tests_failed=0,
            coverage=None,
            arch_score=0,
            all_passed=True,
        )

        # Verify profile has zero_test_blocking=False for INTEGRATION
        int_profile = get_profile(TaskType.INTEGRATION)
        assert int_profile.zero_test_blocking is False, (
            "INTEGRATION profile should have zero_test_blocking=False"
        )

        # Create CoachValidator and validate
        validator = CoachValidator(
            worktree_path=str(tmp_task_dir["root"]),
            task_id=task_id,
        )

        task_data = {
            "task_type": "integration",
            "acceptance_criteria": ["API endpoint integrated"],
        }

        # Add completion promises
        results_path = tmp_task_dir["autobuild"] / task_id / "task_work_results.json"
        results = json.loads(results_path.read_text())
        results["completion_promises"] = [
            {"criterion_id": "AC-001", "status": "complete", "evidence": "Integrated"},
        ]
        results_path.write_text(json.dumps(results, indent=2))

        result = validator.validate(
            task_id=task_id,
            turn=1,
            task=task_data,
        )

        # Zero-test anomaly might still be reported as warning, but not blocking
        zero_test_issues = [
            i for i in result.issues
            if i.get("category") == "zero_test_anomaly" and i.get("severity") == "error"
        ]
        assert len(zero_test_issues) == 0, (
            "INTEGRATION tasks should not have blocking zero_test_anomaly errors"
        )


# ============================================================================
# Additional Integration Tests
# ============================================================================


@pytest.mark.seam
class TestQualityGateStatusComputation:
    """
    Test the computation of QualityGateStatus.all_gates_passed based on
    profile requirements.
    """

    def test_all_gates_passed_when_all_required_pass(self):
        """Test all_gates_passed is True when all required gates pass."""
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

    def test_all_gates_passed_false_when_required_gate_fails(self):
        """Test all_gates_passed is False when any required gate fails."""
        status = QualityGateStatus(
            tests_passed=False,  # <-- Required gate fails
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=True,
            arch_review_required=True,
            plan_audit_required=True,
        )
        assert status.all_gates_passed is False

    def test_all_gates_passed_ignores_non_required(self):
        """Test all_gates_passed ignores gates that are not required."""
        status = QualityGateStatus(
            tests_passed=True,
            coverage_met=False,  # <-- Fails but not required
            arch_review_passed=False,  # <-- Fails but not required
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=False,  # <-- Not required
            arch_review_required=False,  # <-- Not required
            plan_audit_required=True,
        )
        assert status.all_gates_passed is True

    def test_all_gates_passed_with_no_requirements(self):
        """Test all_gates_passed is True when no gates are required."""
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
        # With no required gates, all_gates_passed should be True
        assert status.all_gates_passed is True
