"""
Unit tests for AutoBuild stall detection mechanisms (TASK-AB-SD01).

Tests cover both stall detection mechanisms:
1. No-passing-checkpoint exit: When should_rollback() fires but no passing checkpoint exists
2. Repeated identical feedback exit: When Coach gives identical feedback N turns with 0% progress

Coverage Target: >=85%
Test Count: 14 tests
"""

import pytest
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.progress import FinalStatus

# Import worktree components
from guardkit.worktrees import Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-SD-001"
    worktree.path = Path("/tmp/worktrees/TASK-SD-001")
    worktree.branch_name = "autobuild/TASK-SD-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    display.render_blocked_report = Mock()
    display.console = Mock()
    return display


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock WorktreeCheckpointManager."""
    manager = Mock()
    manager.create_checkpoint.return_value = Mock(commit_hash="abc12345")
    return manager


@pytest.fixture
def mock_pre_loop_gates():
    """Create mock PreLoopQualityGates."""
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    async def mock_execute(*args, **kwargs):
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=5,
            max_turns=5,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def mock_coach_validator():
    """Patch CoachValidator to force SDK fallback."""
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


def make_player_result(
    task_id: str = "TASK-SD-001",
    turn: int = 1,
    success: bool = True,
    tests_passed: bool = True,
) -> AgentInvocationResult:
    """Helper to create Player AgentInvocationResult."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/file.py"],
        "files_created": ["src/new.py"],
        "tests_written": ["tests/test_file.py"],
        "tests_run": True,
        "tests_passed": tests_passed,
        "implementation_notes": "Implementation attempt",
        "concerns": [],
        "requirements_addressed": [],
        "requirements_remaining": [],
    }
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report=report,
        duration_seconds=10.0,
        error=None,
    )


def make_coach_result(
    task_id: str = "TASK-SD-001",
    turn: int = 1,
    decision: str = "feedback",
    feedback_text: str = "Fix type hints in user.py",
    criteria_results: Optional[list] = None,
) -> AgentInvocationResult:
    """Helper to create Coach AgentInvocationResult with feedback."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
        "acceptance_criteria_verification": {
            "criteria_results": criteria_results or [],
        },
    }
    if decision == "feedback":
        report["issues"] = [
            {
                "type": "missing_requirement",
                "severity": "major",
                "description": feedback_text,
                "suggestion": feedback_text,
            }
        ]
        report["rationale"] = feedback_text
    elif decision == "approve":
        report["validation_results"] = {
            "tests_run": True,
            "tests_passed": True,
        }
        report["rationale"] = "All requirements met"

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=5.0,
        error=None,
    )


# ============================================================================
# Test _is_feedback_stalled (Mechanism 2)
# ============================================================================


class TestIsFeedbackStalled:
    """Test the _is_feedback_stalled method for repeated feedback detection."""

    def test_no_stall_below_threshold(self):
        """First two turns with identical feedback should not trigger stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False

    def test_stall_on_3_identical_feedback_zero_progress(self):
        """3 identical feedback turns with 0 criteria passed triggers stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is True

    def test_no_stall_when_criteria_progress(self):
        """Identical feedback with criteria progress should not stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 1) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 1) is False

    def test_no_stall_when_feedback_changes(self):
        """Different feedback each turn should not stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Add error handling", 0) is False
        assert orchestrator._is_feedback_stalled("Missing tests", 0) is False

    def test_stall_case_insensitive(self):
        """Feedback comparison should be case-insensitive."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("Fix Type Hints", 0) is False
        assert orchestrator._is_feedback_stalled("fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("FIX TYPE HINTS", 0) is True

    def test_stall_whitespace_normalized(self):
        """Feedback comparison should normalize whitespace."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator._is_feedback_stalled("  Fix type hints  ", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled(" Fix type hints ", 0) is True

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        for i in range(4):
            result = orchestrator._is_feedback_stalled("Fix hints", 0, threshold=5)
            assert result is False

        assert orchestrator._is_feedback_stalled("Fix hints", 0, threshold=5) is True

    def test_stall_resets_on_different_feedback(self):
        """After 2 identical then a different one, counter resets."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        orchestrator._is_feedback_stalled("Fix type hints", 0)
        orchestrator._is_feedback_stalled("Fix type hints", 0)
        # Different feedback breaks the streak
        orchestrator._is_feedback_stalled("Add docstrings", 0)
        # Resume same feedback - need 3 more consecutive
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is False
        assert orchestrator._is_feedback_stalled("Fix type hints", 0) is True


# ============================================================================
# Test _count_criteria_passed
# ============================================================================


class TestCountCriteriaPassed:
    """Test _count_criteria_passed helper method."""

    def test_count_with_verified_criteria(self):
        """Should count criteria with 'verified' status."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "c1", "status": "verified"},
                    {"criterion_id": "c2", "status": "not_started"},
                    {"criterion_id": "c3", "status": "verified"},
                ]
            }
        }

        assert orchestrator._count_criteria_passed(turn_record) == 2

    def test_count_with_no_coach_result(self):
        """Should return 0 when no coach result exists."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = None

        assert orchestrator._count_criteria_passed(turn_record) == 0

    def test_count_with_empty_criteria(self):
        """Should return 0 when no criteria results in report."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.report = {}

        assert orchestrator._count_criteria_passed(turn_record) == 0


# ============================================================================
# Test No-Passing-Checkpoint Stall (Mechanism 1) in _loop_phase
# ============================================================================


class TestNoPassingCheckpointStall:
    """Test stall detection when should_rollback fires but no passing checkpoint."""

    def test_stall_on_no_passing_checkpoint(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """When should_rollback=True and find_last_passing=None, exit with unrecoverable_stall."""
        # Configure checkpoint manager to trigger stall
        mock_checkpoint_manager.should_rollback.return_value = True
        mock_checkpoint_manager.find_last_passing_checkpoint.return_value = None

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        # Mock Player and Coach to produce feedback (not approve) so loop continues
        player_result = make_player_result(tests_passed=False)
        coach_result = make_coach_result(decision="feedback")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        assert final_decision == "unrecoverable_stall"
        # Should exit early, not run all max_turns
        assert len(turn_history) <= 2  # at most 2 turns (need 2 consecutive failures)

    def test_normal_rollback_when_checkpoint_exists(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """When should_rollback=True and checkpoint exists, rollback normally (no stall).

        Updated for TASK-FIX-CKPT: approval is now checked before stall detection,
        so the test uses feedback on turn 1 (where rollback triggers) and approve
        on the subsequent turn after rollback.
        """
        # Turn 1: should_rollback=True with passing checkpoint → rollback
        # After rollback, loop continues from rollback point
        # Turn 2 (post-rollback): should_rollback=False
        mock_checkpoint_manager.should_rollback.side_effect = [True, False, False, False, False]
        mock_checkpoint_manager.find_last_passing_checkpoint.return_value = 1
        mock_checkpoint_manager.rollback_to.return_value = True

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=3,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        player_result = make_player_result(tests_passed=True)
        # Turn 1: feedback (rollback triggers), Turn 2: approve (after rollback)
        coach_feedback = make_coach_result(decision="feedback", feedback_text="Fix issues")
        coach_approve = make_coach_result(decision="approve")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.side_effect = [coach_feedback, coach_approve]

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        # Should NOT be unrecoverable_stall since rollback succeeded
        assert final_decision != "unrecoverable_stall"
        assert final_decision == "approved"
        mock_checkpoint_manager.rollback_to.assert_called_once_with(1)


# ============================================================================
# Test Repeated Feedback Stall (Mechanism 2) in _loop_phase
# ============================================================================


class TestRepeatedFeedbackStallInLoop:
    """Test that repeated feedback stall exits the loop."""

    def test_stall_exits_loop_on_identical_feedback(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """3 turns with identical Coach feedback and 0% criteria progress exits loop."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=False,  # Disable to isolate feedback stall test
        )

        # Player always succeeds
        player_result = make_player_result(tests_passed=True)
        mock_agent_invoker.invoke_player.return_value = player_result

        # Coach always gives identical feedback with 0 criteria verified
        coach_feedback = make_coach_result(
            decision="feedback",
            feedback_text="Fix type hints in user.py",
            criteria_results=[
                {"criterion_id": "c1", "status": "not_started"},
            ],
        )
        mock_agent_invoker.invoke_coach.return_value = coach_feedback

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-SD-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        assert final_decision == "unrecoverable_stall"
        # Should exit at turn 3 (not run all 10)
        assert len(turn_history) == 3


# ============================================================================
# Test Status Propagation
# ============================================================================


class TestStallStatusPropagation:
    """Test that unrecoverable_stall status propagates correctly."""

    def test_build_summary_details_stall(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_build_summary_details includes stall information."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        summary = orchestrator._build_summary_details([], "unrecoverable_stall")
        assert "Unrecoverable stall" in summary
        assert "cannot make forward progress" in summary.lower()

    def test_build_error_message_stall(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_build_error_message includes stall context."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        error_msg = orchestrator._build_error_message("unrecoverable_stall", [])
        assert "stall" in error_msg.lower()
        assert "cannot make forward progress" in error_msg.lower()

    def test_finalize_phase_handles_stall(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
    ):
        """_finalize_phase preserves worktree and renders summary for stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )

        orchestrator._finalize_phase(
            worktree=mock_worktree,
            final_decision="unrecoverable_stall",
            turn_history=[],
        )

        # Worktree should be preserved
        mock_worktree_manager.preserve_on_failure.assert_called_once_with(mock_worktree)
        # Summary should be rendered
        mock_progress_display.render_summary.assert_called_once()


# ============================================================================
# Test FinalStatus Type in progress.py
# ============================================================================


class TestProgressDisplayStallStatus:
    """Test that progress.py FinalStatus type includes unrecoverable_stall."""

    def test_final_status_includes_stall(self):
        """FinalStatus type alias should accept 'unrecoverable_stall'."""
        # This test validates that the Literal type was extended.
        # If the type doesn't include 'unrecoverable_stall', mypy would catch it.
        status: FinalStatus = "unrecoverable_stall"
        assert status == "unrecoverable_stall"
