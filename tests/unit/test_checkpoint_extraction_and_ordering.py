"""
Unit tests for TASK-FIX-CKPT: Fix checkpoint test extraction and stall ordering.

Tests cover:
1. _extract_tests_passed reads quality_gates.tests_passed (primary path)
2. _extract_tests_passed falls back to top-level tests_passed (backward compat)
3. An approved turn's checkpoint records the nested tests_passed value

The stall detectors and the pollution rollback were deleted in the 27 October
2026 cull (628d22ac), and with them the two tests of approval-versus-stall
ordering (1 November 2026).
"""

import pytest
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from tests.task_scope_fixtures import passing_evidence_bundle
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
def mock_worktree(tmp_path):
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-FIX-001"
    # The task's checkout is admitted under its writer lease, which reads its
    # Git identity, so the stand-in worktree is a real checkout (1 November 2026).
    from tests.task_scope_fixtures import init_checkout

    worktree.path = init_checkout(tmp_path / "worktree")
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
        mock_instance.gather_evidence.return_value = passing_evidence_bundle()
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

    def test_returns_none_when_no_validation_results(self):
        """Returns None (UNKNOWN) when validation_results key is missing.

        TASK-FIX-CKPTTESTRED01 supersedes the prior ``→ False`` behaviour for
        this case. A Coach report with no ``validation_results`` (the default
        LLM-Coach report shape: decision/issues/criteria_verification/rationale)
        carries no authoritative test verdict — that is *absent* evidence, not
        a failure. Collapsing it to ``False`` recorded every LLM-Coach feedback
        turn as ``tests: fail`` and produced FEAT-9DDE run 5's false-red
        ``unrecoverable_stall``. See
        ``.claude/rules/absence-of-failure-is-not-success.md``.
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {}

        assert orchestrator._extract_tests_passed(turn_record) is None


# ============================================================================
# Bug 2: Approved turns record their checkpoint (stall ordering went in 628d22ac)
# ============================================================================


class TestApprovalPrecedenceOverStall:
    """An approved turn records its checkpoint with the nested tests_passed."""

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
