"""
Comprehensive test suite for AutoBuildOrchestrator implementation.

Tests cover all three phases (Setup, Loop, Finalize) with comprehensive
error scenarios, edge cases, and integration paths.

Test Organization:
    - TestConstructor: Initialization and dependency injection
    - TestSetupPhase: Worktree creation and initialization
    - TestLoopPhase: Player↔Coach adversarial turns
    - TestFinalizePhase: Worktree preservation and summary
    - TestIntegration: End-to-end workflows
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from dataclasses import dataclass

# Import components under test
import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    OrchestrationError,
    SetupPhaseError,
    LoopPhaseError,
    FinalizePhaseError,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
)

# Import worktree components from guardkit package
from guardkit.worktrees import (
    Worktree,
    WorktreeCreationError,
    WorktreeMergeError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-AB-001"
    worktree.path = Path("/tmp/worktrees/TASK-AB-001")
    worktree.branch_name = "autobuild/TASK-AB-001"
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
    # Mock async methods as AsyncMock
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
    return display


@pytest.fixture
def mock_coach_validator():
    """
    Patch CoachValidator to force SDK fallback.

    The CoachValidator is tried first in _invoke_coach_safely. By making it
    raise an exception, we force the orchestrator to use the mock_agent_invoker
    which the tests control. This maintains backward compatibility with
    existing tests while allowing CoachValidator to work in production.
    """
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        # Make CoachValidator.validate() raise to force SDK fallback
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


@pytest.fixture
def orchestrator_with_mocks(
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display,
    mock_coach_validator,
):
    """Create AutoBuildOrchestrator with all dependencies mocked."""
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
    )


def make_player_result(
    task_id: str = "TASK-AB-001",
    turn: int = 1,
    success: bool = True,
    error: Optional[str] = None,
    files_created: int = 3,
    tests_passed: bool = True,
) -> AgentInvocationResult:
    """Helper to create Player AgentInvocationResult."""
    report = {}
    if success:
        report = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": [f"src/file{i}.py" for i in range(2)],
            "files_created": [f"src/new{i}.py" for i in range(files_created)],
            "tests_written": [f"tests/test_file{i}.py" for i in range(2)],
            "tests_run": True,
            "tests_passed": tests_passed,
            "implementation_notes": "Implemented OAuth2 flow",
            "concerns": [],
            "requirements_addressed": ["OAuth2 support"],
            "requirements_remaining": [],
        }

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report=report,
        duration_seconds=12.5,
        error=error,
    )


def make_coach_result(
    task_id: str = "TASK-AB-001",
    turn: int = 1,
    decision: str = "approve",
    success: bool = True,
    error: Optional[str] = None,
    issues: Optional[list] = None,
) -> AgentInvocationResult:
    """Helper to create Coach AgentInvocationResult."""
    report = {}
    if success:
        if decision == "approve":
            report = {
                "task_id": task_id,
                "turn": turn,
                "decision": "approve",
                "validation_results": {
                    "requirements_met": ["OAuth2 support"],
                    "tests_run": True,
                    "tests_passed": True,
                    "test_command": "pytest tests/",
                    "test_output_summary": "All tests passed",
                    "code_quality": "Excellent",
                    "edge_cases_covered": ["Token refresh", "Error handling"],
                },
                "rationale": "Implementation meets all requirements",
            }
        else:  # feedback
            report = {
                "task_id": task_id,
                "turn": turn,
                "decision": "feedback",
                "issues": issues or [
                    {
                        "type": "missing_requirement",
                        "severity": "major",
                        "description": "Missing HTTPS enforcement",
                        "requirement": "Security",
                        "suggestion": "Add HTTPS validation in auth flow",
                    },
                ],
                "rationale": "Implementation needs improvements",
            }

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=success,
        report=report,
        duration_seconds=8.3,
        error=error,
    )


# ============================================================================
# Test Constructor and Dependency Injection
# ============================================================================


class TestConstructor:
    """Test AutoBuildOrchestrator initialization."""

    def test_constructor_defaults(self):
        """Test constructor creates default dependencies."""
        # Use current working directory (which is a git repo)
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        assert orchestrator.repo_root == Path.cwd().resolve()
        assert orchestrator.max_turns == 5
        assert orchestrator._worktree_manager is not None
        assert orchestrator._agent_invoker is None  # Lazy initialization
        assert orchestrator._progress_display is not None

    def test_constructor_with_dependency_injection(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test constructor accepts injected dependencies."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=3,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        assert orchestrator._worktree_manager is mock_worktree_manager
        assert orchestrator._agent_invoker is mock_agent_invoker
        assert orchestrator._progress_display is mock_progress_display

    def test_constructor_validates_max_turns(self):
        """Test constructor raises ValueError for invalid max_turns."""
        with pytest.raises(ValueError, match="max_turns must be at least 1"):
            AutoBuildOrchestrator(
                repo_root=Path("/tmp/test"),
                max_turns=0,
            )

    def test_constructor_resolves_repo_root(self):
        """Test constructor resolves relative paths."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("."),
            max_turns=5,
        )

        assert orchestrator.repo_root.is_absolute()

    def test_constructor_custom_max_turns(self):
        """Test constructor accepts custom max_turns."""
        # Use current working directory (which is a git repo)
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        assert orchestrator.max_turns == 10


# ============================================================================
# Test Setup Phase
# ============================================================================


class TestSetupPhase:
    """Test Setup Phase (worktree creation and initialization)."""

    def test_setup_phase_success(self, orchestrator_with_mocks, mock_worktree):
        """Test successful setup phase."""
        # Execute setup phase
        result = orchestrator_with_mocks._setup_phase(
            task_id="TASK-AB-001",
            base_branch="main",
        )

        # Verify worktree creation
        orchestrator_with_mocks._worktree_manager.create.assert_called_once_with(
            task_id="TASK-AB-001",
            base_branch="main",
        )

        # Verify result
        assert result == mock_worktree
        assert result.task_id == "TASK-AB-001"

    def test_setup_phase_initializes_agent_invoker(
        self,
        orchestrator_with_mocks,
        mock_worktree,
    ):
        """Test setup phase initializes AgentInvoker if None."""
        # Set agent_invoker to None to test lazy initialization
        orchestrator_with_mocks._agent_invoker = None

        # Execute setup phase
        result = orchestrator_with_mocks._setup_phase(
            task_id="TASK-AB-001",
            base_branch="main",
        )

        # Verify AgentInvoker was initialized
        assert orchestrator_with_mocks._agent_invoker is not None

    def test_setup_phase_worktree_creation_failure(self, orchestrator_with_mocks):
        """Test setup phase raises SetupPhaseError on worktree creation failure."""
        # Mock worktree creation failure
        orchestrator_with_mocks._worktree_manager.create.side_effect = (
            WorktreeCreationError("Git worktree creation failed")
        )

        # Execute and verify exception
        with pytest.raises(SetupPhaseError, match="Failed to create worktree"):
            orchestrator_with_mocks._setup_phase(
                task_id="TASK-AB-001",
                base_branch="main",
            )


# ============================================================================
# Test Loop Phase
# ============================================================================


class TestLoopPhase:
    """Test Loop Phase (Player↔Coach adversarial turns)."""

    def test_loop_phase_single_turn_approval(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test loop phase with immediate Coach approval on turn 1."""
        # Mock Player and Coach responses
        player_result = make_player_result(turn=1)
        coach_result = make_coach_result(turn=1, decision="approve")

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        # Execute loop phase
        turn_history, final_decision = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify results
        assert final_decision == "approved"
        assert len(turn_history) == 1
        assert turn_history[0].turn == 1
        assert turn_history[0].decision == "approve"
        assert turn_history[0].player_result == player_result
        assert turn_history[0].coach_result == coach_result

    def test_loop_phase_multi_turn_with_feedback(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test loop phase with feedback on turn 1, approval on turn 2."""
        # Mock Turn 1: Player implements, Coach provides feedback
        player_result_1 = make_player_result(turn=1)
        coach_result_1 = make_coach_result(
            turn=1,
            decision="feedback",
            issues=[
                {
                    "type": "missing_requirement",
                    "severity": "major",
                    "description": "Missing HTTPS enforcement",
                    "requirement": "Security",
                    "suggestion": "Add HTTPS validation",
                }
            ],
        )

        # Mock Turn 2: Player addresses feedback, Coach approves
        player_result_2 = make_player_result(turn=2)
        coach_result_2 = make_coach_result(turn=2, decision="approve")

        mock_agent_invoker.invoke_player.side_effect = [
            player_result_1,
            player_result_2,
        ]
        mock_agent_invoker.invoke_coach.side_effect = [
            coach_result_1,
            coach_result_2,
        ]

        # Execute loop phase
        turn_history, final_decision = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify results
        assert final_decision == "approved"
        assert len(turn_history) == 2

        # Verify turn 1 (feedback)
        assert turn_history[0].turn == 1
        assert turn_history[0].decision == "feedback"
        assert turn_history[0].feedback is not None
        assert "HTTPS" in turn_history[0].feedback

        # Verify turn 2 (approved)
        assert turn_history[1].turn == 2
        assert turn_history[1].decision == "approve"
        assert turn_history[1].feedback is None

    def test_loop_phase_max_turns_exceeded(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test loop phase exits with max_turns_exceeded after 5 turns."""
        # Mock all 5 turns with feedback (never approve)
        mock_agent_invoker.invoke_player.return_value = make_player_result()
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            decision="feedback"
        )

        # Execute loop phase (max_turns=5)
        turn_history, final_decision = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify max turns reached
        assert final_decision == "max_turns_exceeded"
        assert len(turn_history) == 5
        assert all(turn.decision == "feedback" for turn in turn_history)

    def test_loop_phase_player_error_returns_early(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test loop phase returns error when Player fails."""
        # Mock Player failure
        player_result = make_player_result(
            success=False,
            error="SDK timeout",
        )
        mock_agent_invoker.invoke_player.return_value = player_result

        # Execute loop phase
        turn_history, final_decision = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify error exit
        assert final_decision == "error"
        assert len(turn_history) == 1
        assert turn_history[0].decision == "error"
        assert turn_history[0].coach_result is None  # Coach not invoked

    def test_loop_phase_coach_error_exits_loop(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test loop phase exits on Coach error."""
        # Mock Player success, Coach failure
        player_result = make_player_result()
        coach_result = make_coach_result(
            success=False,
            error="Coach validation failed",
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        # Execute loop phase
        turn_history, final_decision = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify error exit
        assert final_decision == "error"
        assert len(turn_history) == 1
        assert turn_history[0].decision == "error"

    def test_loop_phase_progress_display_integration(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test loop phase integrates with ProgressDisplay."""
        # Mock single turn approval
        mock_agent_invoker.invoke_player.return_value = make_player_result()
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            decision="approve"
        )

        # Execute loop phase
        orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify progress display calls
        assert mock_progress_display.start_turn.call_count == 2  # Player + Coach
        assert mock_progress_display.complete_turn.call_count == 2

    def test_loop_phase_turn_immutability(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_agent_invoker,
    ):
        """Test TurnRecord immutability (frozen dataclass)."""
        # Mock single turn
        mock_agent_invoker.invoke_player.return_value = make_player_result()
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            decision="approve"
        )

        # Execute loop phase
        turn_history, _ = orchestrator_with_mocks._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
            worktree=mock_worktree,
        )

        # Verify TurnRecord is frozen (can't modify)
        turn_record = turn_history[0]
        with pytest.raises(Exception):  # FrozenInstanceError
            turn_record.decision = "feedback"


# ============================================================================
# Test Finalize Phase
# ============================================================================


class TestFinalizePhase:
    """Test Finalize Phase (worktree preservation and summary)."""

    def test_finalize_phase_preserves_on_approval(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_worktree_manager,
    ):
        """Test finalize phase preserves worktree on approval."""
        turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(),
                coach_result=make_coach_result(decision="approve"),
                decision="approve",
                feedback=None,
                timestamp="2025-12-23T10:00:00Z",
            )
        ]

        orchestrator_with_mocks._finalize_phase(
            worktree=mock_worktree,
            final_decision="approved",
            turn_history=turn_history,
        )

        # Verify preservation
        mock_worktree_manager.preserve_on_failure.assert_called_once_with(
            mock_worktree
        )

    def test_finalize_phase_preserves_on_max_turns(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_worktree_manager,
    ):
        """Test finalize phase preserves worktree on max_turns_exceeded."""
        turn_history = [
            TurnRecord(
                turn=i,
                player_result=make_player_result(turn=i),
                coach_result=make_coach_result(turn=i, decision="feedback"),
                decision="feedback",
                feedback="Improve implementation",
                timestamp=f"2025-12-23T10:0{i}:00Z",
            )
            for i in range(1, 6)
        ]

        orchestrator_with_mocks._finalize_phase(
            worktree=mock_worktree,
            final_decision="max_turns_exceeded",
            turn_history=turn_history,
        )

        # Verify preservation
        mock_worktree_manager.preserve_on_failure.assert_called_once()

    def test_finalize_phase_preserves_on_error(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_worktree_manager,
    ):
        """Test finalize phase preserves worktree on error."""
        turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(success=False, error="SDK timeout"),
                coach_result=None,
                decision="error",
                feedback=None,
                timestamp="2025-12-23T10:00:00Z",
            )
        ]

        orchestrator_with_mocks._finalize_phase(
            worktree=mock_worktree,
            final_decision="error",
            turn_history=turn_history,
        )

        # Verify preservation
        mock_worktree_manager.preserve_on_failure.assert_called_once()

    def test_finalize_phase_renders_summary(
        self,
        orchestrator_with_mocks,
        mock_worktree,
        mock_progress_display,
    ):
        """Test finalize phase renders final summary."""
        turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(),
                coach_result=make_coach_result(decision="approve"),
                decision="approve",
                feedback=None,
                timestamp="2025-12-23T10:00:00Z",
            )
        ]

        orchestrator_with_mocks._finalize_phase(
            worktree=mock_worktree,
            final_decision="approved",
            turn_history=turn_history,
        )

        # Verify summary rendered
        mock_progress_display.render_summary.assert_called_once()
        call_args = mock_progress_display.render_summary.call_args
        assert call_args[1]["total_turns"] == 1
        assert call_args[1]["final_status"] == "approved"


# ============================================================================
# Test Integration (End-to-End)
# ============================================================================


class TestIntegration:
    """Test complete orchestration workflows."""

    def test_integration_happy_path_single_turn(
        self,
        orchestrator_with_mocks,
        mock_agent_invoker,
    ):
        """Test complete orchestration with single-turn approval."""
        # Mock successful single turn
        mock_agent_invoker.invoke_player.return_value = make_player_result()
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            decision="approve"
        )

        # Execute orchestration
        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-AB-001",
            requirements="Implement OAuth2 authentication",
            acceptance_criteria=["Support authorization code flow"],
            base_branch="main",
        )

        # Verify result
        assert result.success is True
        assert result.total_turns == 1
        assert result.final_decision == "approved"
        assert len(result.turn_history) == 1
        assert result.error is None
        assert result.worktree.task_id == "TASK-AB-001"

    def test_integration_multi_turn_with_feedback(
        self,
        orchestrator_with_mocks,
        mock_agent_invoker,
    ):
        """Test complete orchestration with multi-turn feedback loop."""
        # Mock 3-turn workflow: feedback → feedback → approve
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(turn=1),
            make_player_result(turn=2),
            make_player_result(turn=3),
        ]
        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(turn=1, decision="feedback"),
            make_coach_result(turn=2, decision="feedback"),
            make_coach_result(turn=3, decision="approve"),
        ]

        # Execute orchestration
        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-AB-002",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
        )

        # Verify result
        assert result.success is True
        assert result.total_turns == 3
        assert result.final_decision == "approved"
        assert len(result.turn_history) == 3

        # Verify turn progression
        assert result.turn_history[0].decision == "feedback"
        assert result.turn_history[1].decision == "feedback"
        assert result.turn_history[2].decision == "approve"

    def test_integration_max_turns_exceeded(
        self,
        orchestrator_with_mocks,
        mock_agent_invoker,
    ):
        """Test orchestration exits after max_turns."""
        # Mock all turns with feedback (never approve)
        mock_agent_invoker.invoke_player.return_value = make_player_result()
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            decision="feedback"
        )

        # Execute orchestration
        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-AB-003",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
        )

        # Verify result
        assert result.success is False
        assert result.total_turns == 5  # max_turns
        assert result.final_decision == "max_turns_exceeded"
        assert result.error is not None
        assert "Maximum turns" in result.error

    def test_integration_error_handling(
        self,
        orchestrator_with_mocks,
        mock_agent_invoker,
    ):
        """Test orchestration handles errors gracefully."""
        # Mock Player failure
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            success=False,
            error="SDK timeout after 300s",
        )

        # Execute orchestration
        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-AB-004",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
        )

        # Verify error result
        assert result.success is False
        assert result.total_turns == 1
        assert result.final_decision == "error"
        assert result.error is not None
        assert "SDK timeout" in result.error

    def test_integration_worktree_creation_failure(
        self,
        orchestrator_with_mocks,
        mock_worktree_manager,
    ):
        """Test orchestration raises SetupPhaseError on worktree creation failure."""
        # Mock worktree creation failure
        mock_worktree_manager.create.side_effect = WorktreeCreationError(
            "Git worktree add failed"
        )

        # Execute and verify exception
        with pytest.raises(SetupPhaseError, match="Failed to create worktree"):
            orchestrator_with_mocks.orchestrate(
                task_id="TASK-AB-005",
                requirements="Implement OAuth2",
                acceptance_criteria=["Support auth code flow"],
            )

    def test_integration_complete_turn_history(
        self,
        orchestrator_with_mocks,
        mock_agent_invoker,
    ):
        """Test orchestration maintains complete turn history."""
        # Mock 2-turn workflow with different outcomes
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(turn=1, files_created=2),
            make_player_result(turn=2, files_created=1),
        ]
        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(turn=1, decision="feedback"),
            make_coach_result(turn=2, decision="approve"),
        ]

        # Execute orchestration
        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-AB-006",
            requirements="Implement OAuth2",
            acceptance_criteria=["Support auth code flow"],
        )

        # Verify complete history
        assert len(result.turn_history) == 2

        # Turn 1: feedback
        turn1 = result.turn_history[0]
        assert turn1.turn == 1
        assert turn1.decision == "feedback"
        assert turn1.player_result.success is True
        assert turn1.coach_result.success is True
        assert turn1.feedback is not None
        assert turn1.timestamp is not None

        # Turn 2: approved
        turn2 = result.turn_history[1]
        assert turn2.turn == 2
        assert turn2.decision == "approve"
        assert turn2.feedback is None


# ============================================================================
# Test State Persistence
# ============================================================================


class TestStatePersistence:
    """Test state persistence and resume functionality."""

    @pytest.fixture
    def temp_task_file(self, tmp_path):
        """Create a temporary task file with frontmatter."""
        task_file = tmp_path / "TASK-AB-001.md"
        content = """---
id: TASK-AB-001
title: Test Task
status: backlog
---

# Test Task

Requirements here.
"""
        task_file.write_text(content)
        return task_file

    @pytest.fixture
    def temp_task_file_with_state(self, tmp_path):
        """Create a task file with existing autobuild state."""
        task_file = tmp_path / "TASK-AB-002.md"
        worktree_path = tmp_path / "worktrees" / "TASK-AB-002"
        worktree_path.mkdir(parents=True)

        content = f"""---
id: TASK-AB-002
title: Test Task with State
status: in_progress
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: {worktree_path}
  base_branch: main
  started_at: '2025-12-24T10:00:00'
  last_updated: '2025-12-24T10:10:00'
  turns:
  - turn: 1
    decision: feedback
    feedback: Add more tests
    timestamp: '2025-12-24T10:05:00'
    player_summary: Implemented initial feature
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: Fix edge cases
    timestamp: '2025-12-24T10:10:00'
    player_summary: Added test coverage
    player_success: true
    coach_success: true
---

# Test Task with State

Requirements here.
"""
        task_file.write_text(content)
        return task_file, worktree_path

    def test_save_state_creates_autobuild_state(
        self,
        temp_task_file,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _save_state creates autobuild_state in frontmatter."""
        import yaml

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Add a turn to history
        orchestrator._turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(turn=1),
                coach_result=make_coach_result(turn=1, decision="feedback"),
                decision="feedback",
                feedback="Add more tests",
                timestamp="2025-12-24T10:00:00",
            )
        ]

        # Mock worktree
        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-AB-001")
        worktree.base_branch = "main"

        # Save state
        orchestrator._save_state(temp_task_file, worktree, "in_progress")

        # Verify state was saved
        content = temp_task_file.read_text()
        assert "autobuild_state:" in content
        assert "current_turn: 1" in content
        assert "worktree_path:" in content
        assert "status: in_progress" in content

    def test_resume_from_state_restores_turn_history(
        self,
        temp_task_file_with_state,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _resume_from_state restores turn history correctly."""
        task_file, worktree_path = temp_task_file_with_state

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            resume=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Resume from state
        worktree, start_turn = orchestrator._resume_from_state(
            "TASK-AB-002",
            task_file,
        )

        # Verify turn history restored
        assert len(orchestrator._turn_history) == 2
        assert orchestrator._turn_history[0].turn == 1
        assert orchestrator._turn_history[0].decision == "feedback"
        assert orchestrator._turn_history[0].feedback == "Add more tests"
        assert orchestrator._turn_history[1].turn == 2
        assert orchestrator._turn_history[1].feedback == "Fix edge cases"

        # Verify start turn
        assert start_turn == 3  # Continue from turn 3

        # Verify worktree
        assert worktree.task_id == "TASK-AB-002"
        assert worktree.path == worktree_path

    def test_resume_from_state_no_state_raises_error(
        self,
        temp_task_file,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _resume_from_state raises error when no state exists."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            resume=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        with pytest.raises(SetupPhaseError, match="No saved state found"):
            orchestrator._resume_from_state("TASK-AB-001", temp_task_file)

    def test_resume_from_state_missing_worktree_raises_error(
        self,
        tmp_path,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _resume_from_state raises error when worktree doesn't exist."""
        task_file = tmp_path / "TASK-AB-003.md"
        content = """---
id: TASK-AB-003
title: Test Task
status: in_progress
autobuild_state:
  current_turn: 1
  worktree_path: /nonexistent/path
  turns:
  - turn: 1
    decision: feedback
    feedback: Test feedback
    timestamp: '2025-12-24T10:00:00'
    player_success: true
    coach_success: true
---

# Test Task
"""
        task_file.write_text(content)

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            resume=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        with pytest.raises(SetupPhaseError, match="Worktree not found"):
            orchestrator._resume_from_state("TASK-AB-003", task_file)

    def test_get_last_feedback_returns_last_turn_feedback(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _get_last_feedback returns feedback from last turn."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Set turn history
        orchestrator._turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(turn=1),
                coach_result=make_coach_result(turn=1, decision="feedback"),
                decision="feedback",
                feedback="First feedback",
                timestamp="2025-12-24T10:00:00",
            ),
            TurnRecord(
                turn=2,
                player_result=make_player_result(turn=2),
                coach_result=make_coach_result(turn=2, decision="feedback"),
                decision="feedback",
                feedback="Last feedback",
                timestamp="2025-12-24T10:05:00",
            ),
        ]

        # Verify last feedback returned
        assert orchestrator._get_last_feedback() == "Last feedback"

    def test_get_last_feedback_returns_none_when_no_history(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _get_last_feedback returns None when no turn history."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        assert orchestrator._get_last_feedback() is None

    def test_serialize_turn_history(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _serialize_turn_history produces correct format."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Set turn history
        orchestrator._turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(turn=1),
                coach_result=make_coach_result(turn=1, decision="approve"),
                decision="approve",
                feedback=None,
                timestamp="2025-12-24T10:00:00",
            )
        ]

        # Serialize
        serialized = orchestrator._serialize_turn_history()

        # Verify format
        assert len(serialized) == 1
        assert serialized[0]["turn"] == 1
        assert serialized[0]["decision"] == "approve"
        assert serialized[0]["feedback"] is None
        assert serialized[0]["timestamp"] == "2025-12-24T10:00:00"
        assert serialized[0]["player_success"] is True
        assert serialized[0]["coach_success"] is True

    def test_deserialize_turn_history(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """Test _deserialize_turn_history restores TurnRecords."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        saved_turns = [
            {
                "turn": 1,
                "decision": "feedback",
                "feedback": "Test feedback",
                "timestamp": "2025-12-24T10:00:00",
                "player_summary": "Initial implementation",
                "player_success": True,
                "coach_success": True,
            }
        ]

        # Deserialize
        records = orchestrator._deserialize_turn_history(saved_turns)

        # Verify records
        assert len(records) == 1
        assert records[0].turn == 1
        assert records[0].decision == "feedback"
        assert records[0].feedback == "Test feedback"
        assert records[0].timestamp == "2025-12-24T10:00:00"
        assert records[0].player_result.success is True
        assert records[0].coach_result.success is True

    def test_orchestrate_saves_state_after_each_turn(
        self,
        temp_task_file,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_worktree,
        mock_coach_validator,
    ):
        """Test orchestrate saves state after each turn."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Mock 2 turns: feedback then approve
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(turn=1),
            make_player_result(turn=2),
        ]
        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(turn=1, decision="feedback"),
            make_coach_result(turn=2, decision="approve"),
        ]

        # Execute orchestration with task file path
        result = orchestrator.orchestrate(
            task_id="TASK-AB-001",
            requirements="Test requirements",
            acceptance_criteria=["Test criteria"],
            task_file_path=temp_task_file,
        )

        # Verify result
        assert result.success is True
        assert result.total_turns == 2

        # Verify state was saved (check file content)
        content = temp_task_file.read_text()
        assert "autobuild_state:" in content
        assert "current_turn: 2" in content

    def test_resume_parameter_passed_to_orchestrator(self):
        """Test resume parameter is stored correctly."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            resume=True,
        )
        assert orchestrator.resume is True

        orchestrator_no_resume = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
            resume=False,
        )
        assert orchestrator_no_resume.resume is False


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
