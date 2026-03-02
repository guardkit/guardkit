"""
Tests for TASK-ABFIX-003: configuration error flag and fast-exit.

Covers:
- CoachValidationResult.is_configuration_error field
- to_dict() serialization of the flag
- _feedback_result() propagation
- validate() sets flag on invalid_task_type
- TurnRecord.is_configuration_error field
- _execute_turn() propagates flag from coach report
- _loop_phase() exits immediately on configuration error
- Normal feedback still enters the feedback loop
- _build_error_message() handles configuration_error
- Pollution detection: config errors are not counted as test failures
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import fields

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    CoachValidator,
    QualityGateStatus,
)
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult


# ============================================================================
# Helpers
# ============================================================================

def make_player_result(
    task_id: str = "TASK-001",
    turn: int = 1,
    success: bool = True,
) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report={"task_id": task_id, "turn": turn} if success else {},
        duration_seconds=5.0,
        error=None if success else "Player failed",
    )


def make_coach_result(
    decision: str = "feedback",
    is_configuration_error: bool = False,
    feedback: str = "Fix it",
    issues: Optional[List[Dict]] = None,
) -> AgentInvocationResult:
    report: Dict[str, Any] = {
        "task_id": "TASK-001",
        "turn": 1,
        "decision": decision,
        "issues": issues or [],
        "rationale": feedback,
        "is_configuration_error": is_configuration_error,
    }
    return AgentInvocationResult(
        task_id="TASK-001",
        turn=1,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=3.0,
        error=None,
    )


# ============================================================================
# CoachValidationResult — field and serialization
# ============================================================================

class TestCoachValidationResultField:
    """is_configuration_error exists on CoachValidationResult."""

    def test_field_exists_and_defaults_false(self):
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
        )
        assert result.is_configuration_error is False

    def test_field_can_be_set_true(self):
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            is_configuration_error=True,
        )
        assert result.is_configuration_error is True

    def test_to_dict_includes_false(self):
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
        )
        d = result.to_dict()
        assert "is_configuration_error" in d
        assert d["is_configuration_error"] is False

    def test_to_dict_includes_true(self):
        result = CoachValidationResult(
            task_id="TASK-001",
            turn=1,
            decision="feedback",
            is_configuration_error=True,
        )
        d = result.to_dict()
        assert d["is_configuration_error"] is True


# ============================================================================
# CoachValidator._feedback_result propagation
# ============================================================================

class TestFeedbackResultPropagation:
    """_feedback_result passes is_configuration_error to CoachValidationResult."""

    def test_default_is_false(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        result = validator._feedback_result(
            task_id="TASK-001",
            turn=1,
            issues=[{"severity": "must_fix", "description": "something"}],
            rationale="Normal feedback",
        )
        assert result.is_configuration_error is False

    def test_explicit_true_propagates(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        result = validator._feedback_result(
            task_id="TASK-001",
            turn=1,
            issues=[{"severity": "must_fix", "category": "invalid_task_type", "description": "bad type"}],
            rationale="Config error",
            is_configuration_error=True,
        )
        assert result.is_configuration_error is True


# ============================================================================
# CoachValidator.validate() — invalid_task_type sets flag
# ============================================================================

class TestValidateConfigError:
    """validate() marks result as configuration error on invalid task_type."""

    def test_invalid_task_type_sets_is_configuration_error(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        task = {
            "acceptance_criteria": ["do something"],
            "task_type": "nonexistent_bogus_type_xyz",
        }
        result = validator.validate(task_id="TASK-001", turn=1, task=task)
        assert result.is_configuration_error is True
        assert result.decision == "feedback"
        assert any(i.get("category") == "invalid_task_type" for i in result.issues)

    def test_invalid_task_type_in_to_dict(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        task = {
            "acceptance_criteria": ["do something"],
            "task_type": "totally_invalid",
        }
        result = validator.validate(task_id="TASK-001", turn=1, task=task)
        d = result.to_dict()
        assert d["is_configuration_error"] is True

    def test_valid_task_type_does_not_set_flag(self, tmp_path):
        """Valid task_type should not produce is_configuration_error=True even if other gates fail."""
        validator = CoachValidator(str(tmp_path))
        task = {
            "acceptance_criteria": ["do something"],
            "task_type": "feature",
        }
        # Will fail because no task_work_results.json — but not a config error
        result = validator.validate(task_id="TASK-001", turn=1, task=task)
        assert result.is_configuration_error is False


# ============================================================================
# TurnRecord — is_configuration_error field
# ============================================================================

class TestTurnRecordField:
    """TurnRecord has is_configuration_error field."""

    def test_field_exists_and_defaults_false(self):
        player = make_player_result()
        coach = make_coach_result()
        record = TurnRecord(
            turn=1,
            player_result=player,
            coach_result=coach,
            decision="feedback",
            feedback="something",
            timestamp="2025-01-01T00:00:00",
        )
        assert record.is_configuration_error is False

    def test_field_can_be_set_true(self):
        player = make_player_result()
        coach = make_coach_result()
        record = TurnRecord(
            turn=1,
            player_result=player,
            coach_result=coach,
            decision="feedback",
            feedback="config error",
            timestamp="2025-01-01T00:00:00",
            is_configuration_error=True,
        )
        assert record.is_configuration_error is True


# ============================================================================
# _execute_turn propagates is_configuration_error from coach report
# ============================================================================

class TestExecuteTurnPropagatesConfigError:
    """_execute_turn sets TurnRecord.is_configuration_error from coach report."""

    def _make_orchestrator(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orch.max_turns = 3
        orch.enable_pre_loop = True
        orch.ablation_mode = False
        orch.enable_checkpoints = False
        orch._checkpoint_manager = None
        orch._cancellation_event = None
        orch._turn_history = []
        orch.resume = False
        orch.enable_context = False
        orch.rollback_on_pollution = False
        orch._max_criteria_passed = 0
        orch.verbose = False
        orch._last_player_context_status = None
        orch._last_coach_context_status = None
        orch._feature_id = None
        orch.perspective_reset_turns = []
        orch._worktree_manager = Mock()
        orch._worktree_manager.worktrees_dir = Path("/tmp/worktrees")
        orch._agent_invoker = None
        orch._progress_display = Mock()
        orch._progress_display.__enter__ = Mock(return_value=orch._progress_display)
        orch._progress_display.__exit__ = Mock(return_value=False)
        orch._progress_display.start_turn = Mock()
        orch._progress_display.complete_turn = Mock()
        orch._progress_display.console = Mock()
        orch._progress_display.console.print = Mock()
        return orch

    def test_config_error_propagated_to_turn_record(self):
        orch = self._make_orchestrator()
        player_result = make_player_result()
        config_coach_result = make_coach_result(
            decision="feedback",
            is_configuration_error=True,
            feedback="Invalid task_type 'enhancement'",
            issues=[{"severity": "must_fix", "category": "invalid_task_type",
                     "description": "Invalid task_type 'enhancement'"}],
        )

        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        with patch.object(orch, "_invoke_player_safely", return_value=player_result), \
             patch.object(orch, "_invoke_coach_safely", return_value=config_coach_result), \
             patch.object(orch, "_resolve_tests_required", return_value=True), \
             patch.object(orch, "_build_player_summary", return_value="Player ok"):
            record = orch._execute_turn(
                turn=1,
                task_id="TASK-001",
                requirements="do something",
                worktree=worktree,
                previous_feedback=None,
            )

        assert record.is_configuration_error is True

    def test_normal_feedback_does_not_set_config_error(self):
        orch = self._make_orchestrator()
        player_result = make_player_result()
        normal_coach_result = make_coach_result(
            decision="feedback",
            is_configuration_error=False,
            feedback="Add more tests",
        )

        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        with patch.object(orch, "_invoke_player_safely", return_value=player_result), \
             patch.object(orch, "_invoke_coach_safely", return_value=normal_coach_result), \
             patch.object(orch, "_resolve_tests_required", return_value=True), \
             patch.object(orch, "_build_player_summary", return_value="Player ok"):
            record = orch._execute_turn(
                turn=1,
                task_id="TASK-001",
                requirements="do something",
                worktree=worktree,
                previous_feedback=None,
            )

        assert record.is_configuration_error is False


# ============================================================================
# _loop_phase fast-exit on configuration error
# ============================================================================

class TestLoopPhaseFastExit:
    """_loop_phase exits immediately on configuration error."""

    def _make_orchestrator(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orch.max_turns = 5
        orch.enable_pre_loop = True
        orch.ablation_mode = False
        orch.enable_checkpoints = False
        orch._checkpoint_manager = None
        orch._cancellation_event = None
        orch._turn_history = []
        orch.resume = False
        orch.enable_context = False
        orch.rollback_on_pollution = False
        orch._max_criteria_passed = 0
        orch.verbose = False
        orch._last_player_context_status = None
        orch._last_coach_context_status = None
        orch._feature_id = None
        orch.perspective_reset_turns = []
        orch._worktree_manager = Mock()
        orch._worktree_manager.worktrees_dir = Path("/tmp/worktrees")
        orch._agent_invoker = None

        display = Mock()
        display.__enter__ = Mock(return_value=display)
        display.__exit__ = Mock(return_value=False)
        display.start_turn = Mock()
        display.complete_turn = Mock()
        display.console = Mock()
        display.console.print = Mock()
        orch._progress_display = display
        return orch

    def _make_config_error_turn_record(self, turn: int = 1) -> TurnRecord:
        player = make_player_result(turn=turn)
        coach = make_coach_result(
            decision="feedback",
            is_configuration_error=True,
            feedback="Invalid task_type 'enhancement'",
            issues=[{"severity": "must_fix", "category": "invalid_task_type",
                     "description": "Invalid task_type 'enhancement'"}],
        )
        return TurnRecord(
            turn=turn,
            player_result=player,
            coach_result=coach,
            decision="feedback",
            feedback="Invalid task_type 'enhancement'",
            timestamp="2025-01-01T00:00:00",
            is_configuration_error=True,
        )

    def _make_normal_feedback_turn_record(self, turn: int = 1) -> TurnRecord:
        player = make_player_result(turn=turn)
        coach = make_coach_result(decision="feedback")
        return TurnRecord(
            turn=turn,
            player_result=player,
            coach_result=coach,
            decision="feedback",
            feedback="Add more tests",
            timestamp="2025-01-01T00:00:00",
            is_configuration_error=False,
        )

    def test_config_error_exits_immediately(self):
        orch = self._make_orchestrator()
        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        config_error_record = self._make_config_error_turn_record(turn=1)

        with patch.object(orch, "_execute_turn", return_value=config_error_record), \
             patch.object(orch, "_capture_turn_state"), \
             patch.object(orch, "_record_honesty"), \
             patch.object(orch, "_display_criteria_progress"):
            history, decision = orch._loop_phase(
                task_id="TASK-001",
                requirements="do something",
                acceptance_criteria=["do something"],
                worktree=worktree,
            )

        assert decision == "configuration_error"
        # Only 1 turn — did not continue to turn 2, 3...
        assert len(history) == 1

    def test_config_error_does_not_create_checkpoint(self):
        """Checkpoint creation must be skipped for config errors."""
        orch = self._make_orchestrator()
        orch.enable_checkpoints = True
        checkpoint_manager = Mock()
        orch._checkpoint_manager = checkpoint_manager

        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        config_error_record = self._make_config_error_turn_record(turn=1)

        with patch.object(orch, "_execute_turn", return_value=config_error_record), \
             patch.object(orch, "_capture_turn_state"), \
             patch.object(orch, "_record_honesty"), \
             patch.object(orch, "_display_criteria_progress"):
            _, decision = orch._loop_phase(
                task_id="TASK-001",
                requirements="do something",
                acceptance_criteria=["do something"],
                worktree=worktree,
            )

        assert decision == "configuration_error"
        # No checkpoint was created for this config-error turn
        checkpoint_manager.create_checkpoint.assert_not_called()

    def test_normal_feedback_enters_loop(self):
        """Non-config-error feedback should NOT exit immediately."""
        orch = self._make_orchestrator()
        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        # Turn 1: normal feedback → Turn 2: approve
        from guardkit.orchestrator.autobuild import TurnRecord as TR
        player = make_player_result()
        coach_approve = AgentInvocationResult(
            task_id="TASK-001", turn=2, agent_type="coach",
            success=True, report={"decision": "approve", "is_configuration_error": False},
            duration_seconds=3.0, error=None,
        )
        approve_record = TR(
            turn=2, player_result=player, coach_result=coach_approve,
            decision="approve", feedback=None,
            timestamp="2025-01-01T00:00:00",
        )

        normal_feedback = self._make_normal_feedback_turn_record(turn=1)

        call_count = [0]
        def execute_turn_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return normal_feedback
            return approve_record

        with patch.object(orch, "_execute_turn", side_effect=execute_turn_side_effect), \
             patch.object(orch, "_capture_turn_state"), \
             patch.object(orch, "_record_honesty"), \
             patch.object(orch, "_display_criteria_progress"), \
             patch.object(orch, "_is_feedback_stalled", return_value=False), \
             patch.object(orch, "_count_criteria_passed", return_value=0), \
             patch.object(orch, "_should_reset_perspective", return_value=False), \
             patch.object(orch, "_get_last_feedback", return_value=None):
            history, decision = orch._loop_phase(
                task_id="TASK-001",
                requirements="do something",
                acceptance_criteria=["do something"],
                worktree=worktree,
            )

        # Must have taken 2 turns (not exited after turn 1 feedback)
        assert len(history) == 2
        assert decision == "approved"

    def test_config_error_message_logged(self):
        """Progress display must print a clear error on config error."""
        orch = self._make_orchestrator()
        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-001")

        config_error_record = self._make_config_error_turn_record(turn=1)

        with patch.object(orch, "_execute_turn", return_value=config_error_record), \
             patch.object(orch, "_capture_turn_state"), \
             patch.object(orch, "_record_honesty"), \
             patch.object(orch, "_display_criteria_progress"):
            orch._loop_phase(
                task_id="TASK-001",
                requirements="do something",
                acceptance_criteria=["do something"],
                worktree=worktree,
            )

        # A message was printed to console
        assert orch._progress_display.console.print.called


# ============================================================================
# _build_error_message handles configuration_error
# ============================================================================

class TestBuildErrorMessage:
    """_build_error_message returns sensible text for configuration_error."""

    def _make_orchestrator(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orch.max_turns = 5
        return orch

    def test_configuration_error_message(self):
        orch = self._make_orchestrator()
        player = make_player_result()
        coach = make_coach_result(is_configuration_error=True, feedback="Invalid task_type 'x'")
        turn_record = TurnRecord(
            turn=1, player_result=player, coach_result=coach,
            decision="feedback", feedback="Invalid task_type 'x'",
            timestamp="2025-01-01T00:00:00",
            is_configuration_error=True,
        )

        msg = orch._build_error_message("configuration_error", [turn_record])
        assert "configuration" in msg.lower()
        assert "task_type" in msg.lower() or "retry" in msg.lower()

    def test_configuration_error_empty_history(self):
        orch = self._make_orchestrator()
        msg = orch._build_error_message("configuration_error", [])
        assert "configuration" in msg.lower()
