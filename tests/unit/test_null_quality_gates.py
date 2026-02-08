"""
Unit tests for TASK-FIX-64EE: Fix null quality gate handling, stall threshold,
and incomplete session feedback.

Tests cover:
1. verify_quality_gates() handles all_passed: null by falling through to tests_failed
2. _extract_tests_passed() returns False (not None) when tests_passed is null
3. should_rollback() default threshold is 3 consecutive failures
4. Coach feedback for incomplete sessions mentions exhausted turns
5. No regression of TASK-FIX-CKPT fixes (approval-before-stall ordering)
6. No regression of TASK-AB-SD01 (both stall mechanisms still active)

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    QualityGateStatus,
)
from guardkit.orchestrator.worktree_checkpoints import (
    Checkpoint,
    WorktreeCheckpointManager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-NULL-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def mock_git_executor():
    """Create mock git executor."""
    executor = Mock()
    executor.execute.return_value = Mock(
        returncode=0,
        stdout="abc123\n",
        stderr="",
    )
    return executor


@pytest.fixture
def checkpoint_manager(tmp_path, mock_git_executor):
    """Create checkpoint manager with mock git executor."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-NULL-001"
    autobuild_dir.mkdir(parents=True)
    return WorktreeCheckpointManager(
        worktree_path=worktree_path,
        task_id="TASK-NULL-001",
        git_executor=mock_git_executor,
    )


# ============================================================================
# Fix 1: verify_quality_gates() null handling
# ============================================================================


class TestVerifyQualityGatesNullHandling:
    """Test verify_quality_gates() handles all_passed: null correctly."""

    def test_all_passed_null_falls_through_to_tests_failed_zero(self, tmp_worktree):
        """When all_passed is null and tests_failed=0, tests_passed should be True."""
        task_work_results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": None,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        # tests_failed=0 means tests_passed should be True
        assert status.tests_passed is True

    def test_all_passed_null_falls_through_to_tests_failed_nonzero(self, tmp_worktree):
        """When all_passed is null and tests_failed>0, tests_passed should be False."""
        task_work_results = {
            "quality_gates": {
                "tests_passing": False,
                "tests_passed": 3,
                "tests_failed": 2,
                "coverage": None,
                "coverage_met": None,
                "all_passed": None,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        assert status.tests_passed is False

    def test_all_passed_null_no_tests_failed_key(self, tmp_worktree):
        """When all_passed is null and no tests_failed key, defaults to False."""
        task_work_results = {
            "quality_gates": {
                "all_passed": None,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        assert status.tests_passed is False

    def test_all_passed_true_still_works(self, tmp_worktree):
        """Regression: all_passed=True still works correctly."""
        task_work_results = {
            "quality_gates": {
                "all_passed": True,
                "tests_passed": 15,
                "tests_failed": 0,
                "coverage_met": True,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        assert status.tests_passed is True
        assert status.all_gates_passed is True

    def test_all_passed_false_still_works(self, tmp_worktree):
        """Regression: all_passed=False still works correctly."""
        task_work_results = {
            "quality_gates": {
                "all_passed": False,
                "tests_passed": 10,
                "tests_failed": 3,
                "coverage_met": True,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        assert status.tests_passed is False

    def test_dm008_scenario_exact_data(self, tmp_worktree):
        """Reproduce exact DM-008 task_work_results.json data."""
        task_work_results = {
            "task_id": "TASK-DM-008",
            "timestamp": "2026-02-08T08:22:12.866927",
            "completed": False,
            "phases": {
                "phase_0": {
                    "detected": True,
                    "text": "Looking at the existing code:",
                    "completed": False,
                }
            },
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": None,
            },
            "files_modified": [],
            "files_created": [],
            "summary": "Implementation completed",
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        status = validator.verify_quality_gates(task_work_results)

        # With null all_passed, falls through to tests_failed=0 → True
        assert status.tests_passed is True


# ============================================================================
# Fix 2: _extract_tests_passed() null coercion
# ============================================================================


class TestExtractTestsPassedNullCoercion:
    """Test _extract_tests_passed() returns False (not None) for null values."""

    def test_null_tests_passed_returns_false(self):
        """When quality_gates.tests_passed is None, returns False not None."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": None,
                    "tests_run": True,
                },
            },
        }

        result = orchestrator._extract_tests_passed(turn_record)
        assert result is False
        assert result is not None

    def test_true_tests_passed_returns_true(self):
        """Regression: True values still work."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True

    def test_false_tests_passed_returns_false(self):
        """Regression: False values still work."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": False,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is False


# ============================================================================
# Fix 3: should_rollback() default threshold = 3
# ============================================================================


class TestShouldRollbackThreshold:
    """Test should_rollback() default threshold is now 3."""

    def test_default_threshold_is_three(self, checkpoint_manager, mock_git_executor):
        """Default threshold should be 3, not 2."""
        # Create 2 consecutive failures
        mock_git_executor.execute.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        ]

        checkpoint_manager.create_checkpoint(1, False, 0)
        checkpoint_manager.create_checkpoint(2, False, 0)

        # With default threshold=3, 2 failures should NOT trigger rollback
        assert checkpoint_manager.should_rollback() is False

    def test_three_failures_triggers_rollback(self, checkpoint_manager, mock_git_executor):
        """3 consecutive failures should trigger rollback with default threshold."""
        mock_git_executor.execute.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit3\n", stderr=""),  # rev-parse
        ]

        checkpoint_manager.create_checkpoint(1, False, 0)
        checkpoint_manager.create_checkpoint(2, False, 0)
        checkpoint_manager.create_checkpoint(3, False, 0)

        # With default threshold=3, 3 failures should trigger rollback
        assert checkpoint_manager.should_rollback() is True

    def test_caller_can_override_threshold(self, checkpoint_manager, mock_git_executor):
        """Callers can still pass custom threshold values."""
        mock_git_executor.execute.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit1\n", stderr=""),  # rev-parse
            Mock(returncode=0, stdout="", stderr=""),  # add
            Mock(returncode=0, stdout="", stderr=""),  # commit
            Mock(returncode=0, stdout="commit2\n", stderr=""),  # rev-parse
        ]

        checkpoint_manager.create_checkpoint(1, False, 0)
        checkpoint_manager.create_checkpoint(2, False, 0)

        # With explicit threshold=2, should trigger
        assert checkpoint_manager.should_rollback(consecutive_failures=2) is True
        # With default threshold=3, should not trigger
        assert checkpoint_manager.should_rollback() is False

    def test_null_tests_passed_treated_as_failure(self, checkpoint_manager):
        """Checkpoints with tests_passed=None are treated as failures."""
        # Directly set checkpoints to simulate null scenario
        checkpoint_manager.checkpoints = [
            Checkpoint(turn=1, tests_passed=None, test_count=0, commit_hash="a1", timestamp="2026-01-01T00:00:00Z", message="Turn 1"),
            Checkpoint(turn=2, tests_passed=None, test_count=0, commit_hash="a2", timestamp="2026-01-01T00:01:00Z", message="Turn 2"),
            Checkpoint(turn=3, tests_passed=None, test_count=0, commit_hash="a3", timestamp="2026-01-01T00:02:00Z", message="Turn 3"),
        ]

        # None is falsy, so 3 Nones should trigger rollback
        assert checkpoint_manager.should_rollback() is True


# ============================================================================
# Fix 4: Coach feedback for incomplete sessions
# ============================================================================


class TestIncompletSessionFeedback:
    """Test Coach provides actionable feedback for incomplete Player sessions."""

    def test_incomplete_session_feedback_mentions_sdk_turns(self, tmp_worktree):
        """When all_passed is null with zero test counts, feedback mentions SDK turns."""
        task_work_results = {
            "quality_gates": {
                "tests_passing": True,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": None,
                "coverage_met": None,
                "all_passed": None,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))

        # verify_quality_gates with our fix now returns tests_passed=True
        # because tests_failed=0. But we need to test the feedback path
        # where gates.tests_passed is False (when tests_required but not passed).
        # Create a QualityGateStatus with tests_passed=False to test feedback
        gates = QualityGateStatus(
            tests_passed=False,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=False,
            arch_review_required=False,
            plan_audit_required=False,
        )

        result = validator._feedback_from_gates(
            task_id="TASK-NULL-001",
            turn=1,
            gates=gates,
            task_work_results=task_work_results,
        )

        assert result.decision == "feedback"
        assert len(result.issues) >= 1
        test_issue = next(i for i in result.issues if i["category"] == "test_failure")
        assert "SDK turns" in test_issue["description"]
        assert "Phase 4.5" in test_issue["description"]
        assert test_issue["details"]["incomplete_session"] is True

    def test_normal_test_failure_feedback_unchanged(self, tmp_worktree):
        """When tests genuinely failed (not incomplete), feedback is unchanged."""
        task_work_results = {
            "quality_gates": {
                "tests_passing": False,
                "tests_passed": 10,
                "tests_failed": 3,
                "coverage": 80.0,
                "coverage_met": True,
                "all_passed": False,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        gates = QualityGateStatus(
            tests_passed=False,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=False,
            arch_review_required=False,
            plan_audit_required=False,
        )

        result = validator._feedback_from_gates(
            task_id="TASK-NULL-001",
            turn=1,
            gates=gates,
            task_work_results=task_work_results,
        )

        assert result.decision == "feedback"
        test_issue = next(i for i in result.issues if i["category"] == "test_failure")
        assert "Tests did not pass" in test_issue["description"]
        assert "incomplete_session" not in test_issue["details"]

    def test_incomplete_session_with_null_all_passed_and_some_tests(self, tmp_worktree):
        """When all_passed is null but tests ran, use normal feedback."""
        task_work_results = {
            "quality_gates": {
                "tests_passing": False,
                "tests_passed": 5,
                "tests_failed": 2,
                "coverage": None,
                "coverage_met": None,
                "all_passed": None,
            },
            "code_review": {"score": 75},
        }

        validator = CoachValidator(str(tmp_worktree))
        gates = QualityGateStatus(
            tests_passed=False,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
            tests_required=True,
            coverage_required=False,
            arch_review_required=False,
            plan_audit_required=False,
        )

        result = validator._feedback_from_gates(
            task_id="TASK-NULL-001",
            turn=1,
            gates=gates,
            task_work_results=task_work_results,
        )

        test_issue = next(i for i in result.issues if i["category"] == "test_failure")
        # Has test counts, so use normal failure message
        assert "Tests did not pass" in test_issue["description"]


# ============================================================================
# Regression: TASK-FIX-CKPT fixes preserved
# ============================================================================


class TestTaskFixCkptRegression:
    """Ensure TASK-FIX-CKPT fixes are not regressed."""

    def test_extract_tests_passed_reads_quality_gates_path(self):
        """TASK-FIX-CKPT: Primary path reads quality_gates.tests_passed."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": True,
                    "tests_run": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True

    def test_extract_tests_passed_falls_back_to_top_level(self):
        """TASK-FIX-CKPT: Fallback to top-level tests_passed."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "tests_run": True,
                "tests_passed": True,
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True
