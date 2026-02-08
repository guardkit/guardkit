"""
Unit tests for TASK-FIX-CKPT: Fix checkpoint test extraction and stall ordering.

Tests cover:
1. _extract_tests_passed reads quality_gates.tests_passed (primary path)
2. _extract_tests_passed falls back to top-level tests_passed (backward compat)
3. Coach approval takes precedence over stall detection
4. Existing stall detection still works for legitimate stall cases

Coverage Target: >=85%
Test Count: 8 tests
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
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-FIX-001"
    worktree.path = Path("/tmp/worktrees/TASK-FIX-001")
    worktree.branch_name = "autobuild/TASK-FIX-001"
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


# ============================================================================
# Test Helpers
# ============================================================================


def make_player_result(
    task_id: str = "TASK-FIX-001",
    turn: int = 1,
    success: bool = True,
    tests_passed: bool = True,
) -> AgentInvocationResult:
    """Helper to create Player AgentInvocationResult."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "files_modified": ["src/file.py"],
        "files_created": [],
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


def make_coach_result_nested(
    task_id: str = "TASK-FIX-001",
    turn: int = 1,
    decision: str = "approve",
    tests_passed: bool = True,
    feedback_text: str = "Fix issues",
    criteria_results: Optional[list] = None,
) -> AgentInvocationResult:
    """Helper to create Coach result with nested quality_gates.tests_passed (actual Coach format)."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
        "acceptance_criteria_verification": {
            "criteria_results": criteria_results or [],
        },
    }
    if decision == "approve":
        report["validation_results"] = {
            "quality_gates": {
                "tests_passed": tests_passed,
                "tests_run": True,
            },
        }
        report["rationale"] = "All requirements met"
    elif decision == "feedback":
        report["issues"] = [
            {
                "type": "missing_requirement",
                "severity": "major",
                "description": feedback_text,
                "suggestion": feedback_text,
            }
        ]
        report["rationale"] = feedback_text

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=5.0,
        error=None,
    )


def make_coach_result_legacy(
    task_id: str = "TASK-FIX-001",
    turn: int = 1,
    decision: str = "approve",
    tests_passed: bool = True,
) -> AgentInvocationResult:
    """Helper to create Coach result with legacy top-level tests_passed format."""
    report = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
    }
    if decision == "approve":
        report["validation_results"] = {
            "tests_run": True,
            "tests_passed": tests_passed,
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
# Bug 1: _extract_tests_passed JSON path tests
# ============================================================================


class TestExtractTestsPassed:
    """Test _extract_tests_passed reads correct JSON path."""

    def test_reads_nested_quality_gates_path(self):
        """Primary path: reads validation_results.quality_gates.tests_passed."""
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

    def test_reads_nested_quality_gates_false(self):
        """Primary path: reads false value from quality_gates."""
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
                    "tests_run": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is False

    def test_falls_back_to_top_level_tests_passed(self):
        """Fallback: reads validation_results.tests_passed when quality_gates missing."""
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

    def test_returns_false_when_no_coach_result(self):
        """Returns False when coach_result is None."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = None

        assert orchestrator._extract_tests_passed(turn_record) is False

    def test_returns_false_when_no_validation_results(self):
        """Returns False when validation_results key is missing."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {}

        assert orchestrator._extract_tests_passed(turn_record) is False


# ============================================================================
# Bug 2: Approval precedence over stall detection
# ============================================================================


class TestApprovalPrecedenceOverStall:
    """Test that Coach approval takes precedence over stall detection."""

    def test_approval_returned_despite_stall_conditions(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """Coach approval should be returned even when stall conditions are met.

        Scenario: should_rollback fires on turn 2 (after 2 consecutive failures)
        with no passing checkpoint, BUT Coach approves on turn 2. Since approval
        is checked before stall detection, it should take precedence.

        Before the fix (old code flow):
          checkpoint -> stall check -> unrecoverable_stall (approval never checked)
        After the fix (new code flow):
          decision check -> approve -> return "approved" (stall never reached)
        """
        # should_rollback: False on turn 1 (only 1 failure), True on turn 2 (2 failures)
        mock_checkpoint_manager.should_rollback.side_effect = [False, True]
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

        player_result = make_player_result(tests_passed=True)

        # Turn 1: feedback (should_rollback=False, loop continues)
        # Turn 2: approve (should_rollback would be True, but approval checked first)
        coach_feedback = make_coach_result_nested(
            decision="feedback",
            feedback_text="Fix issues",
            criteria_results=[{"criterion_id": "c1", "status": "not_started"}],
        )
        coach_approve = make_coach_result_nested(decision="approve", tests_passed=True)

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.side_effect = [coach_feedback, coach_approve]

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-FIX-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        # Approval should take precedence over stall detection
        assert final_decision == "approved"
        assert len(turn_history) == 2

    def test_stall_still_triggers_on_feedback(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """Stall detection should still work when Coach gives feedback (not approve).

        This verifies we haven't broken existing stall detection for legitimate cases.
        """
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

        player_result = make_player_result(tests_passed=False)
        coach_feedback = make_coach_result_nested(
            decision="feedback",
            feedback_text="Fix type hints",
            criteria_results=[],
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_feedback

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-FIX-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        # Stall detection should still fire when Coach gives feedback
        assert final_decision == "unrecoverable_stall"

    def test_checkpoint_records_correct_tests_passed_with_nested_format(
        self,
        mock_worktree,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_pre_loop_gates,
        mock_coach_validator,
        mock_checkpoint_manager,
    ):
        """Checkpoint should record tests_passed=True when Coach uses nested quality_gates format."""
        # Don't trigger rollback
        mock_checkpoint_manager.should_rollback.return_value = False

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=2,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
            enable_checkpoints=True,
            rollback_on_pollution=True,
        )
        orchestrator._checkpoint_manager = mock_checkpoint_manager

        player_result = make_player_result(tests_passed=True)
        # Coach approves with nested quality_gates format
        coach_approve = make_coach_result_nested(
            decision="approve",
            tests_passed=True,
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_approve

        turn_history, final_decision = orchestrator._loop_phase(
            task_id="TASK-FIX-001",
            requirements="Test requirements",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

        assert final_decision == "approved"

        # Verify checkpoint was created with tests_passed=True
        mock_checkpoint_manager.create_checkpoint.assert_called_once_with(
            turn=1,
            tests_passed=True,
            test_count=0,  # _extract_test_count returns 0 since coach report doesn't have test_count at expected path
        )
