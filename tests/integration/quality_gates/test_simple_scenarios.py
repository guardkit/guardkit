"""
Integration tests for simple task scenarios (complexity 1-3).

These tests verify that simple tasks complete efficiently through
the quality gates workflow with minimal iterations.

Test Coverage:
    - Auto-proceed through pre-loop gates
    - Single-turn approval by Coach
    - Worktree preservation
    - Minimal overhead for straightforward tasks

Coverage Target: >=85%
"""

import pytest
from pathlib import Path

from .conftest import (
    make_player_result,
    make_coach_result,
    assert_quality_gates_passed,
    assert_complexity_based_turns,
    assert_worktree_preserved,
)


# ============================================================================
# Simple Scenario Tests (Complexity 1-3)
# ============================================================================


class TestSimpleTaskScenarios:
    """Test simple tasks that should complete in 1-2 turns."""

    @pytest.mark.integration
    def test_simple_task_single_turn_approval(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test simple task completes in single turn with Coach approval.

        Scenario:
            - Complexity: 2 (simple CRUD endpoint)
            - Files: 2
            - Expected turns: 1
            - Expected outcome: Approved

        Quality Gates:
            - Pre-loop: Auto-proceed (complexity < 3)
            - Loop: Single turn approval
            - Post-loop: Worktree preserved

        Assertions:
            - Success = True
            - Total turns = 1
            - Final decision = "approved"
            - Worktree preserved
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player implements successfully
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],
        )

        # Mock Coach approves immediately
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple CRUD endpoint",
            acceptance_criteria=["Add GET endpoint", "Add POST endpoint"],
            base_branch="main",
            task_file_path=task_scenario["task_file"],
        )

        # Verify quality gates passed
        assert_quality_gates_passed(result)

        # Verify single turn completion
        assert result.total_turns == 1, "Simple task should complete in 1 turn"
        assert result.turn_history[0].decision == "approve"

        # Verify worktree preserved
        assert_worktree_preserved(result)

    @pytest.mark.integration
    def test_simple_task_with_pre_loop_gates(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_pre_loop_gates,
    ):
        """
        Test pre-loop quality gates execute for simple task.

        Verifies that even simple tasks go through pre-loop quality gates:
        - Implementation planning (Phase 2)
        - Architectural review (Phase 2.5B)
        - Complexity evaluation (Phase 2.7)

        Assertions:
            - Pre-loop gates executed
            - Complexity score = 2
            - Max turns = 3 (based on complexity)
            - Checkpoint auto-approved (no human intervention)
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player and Coach
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify pre-loop gates executed
        mock_pre_loop_gates.execute.assert_called_once()
        call_args = mock_pre_loop_gates.execute.call_args

        assert call_args[0][0] == task_scenario["task_id"]

        # Verify pre-loop results
        assert result.pre_loop_result is not None
        assert result.pre_loop_result["complexity"] == 2
        assert result.pre_loop_result["max_turns"] == 3
        assert result.pre_loop_result["checkpoint_passed"] is True

    @pytest.mark.integration
    def test_simple_task_worktree_preserved(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_worktree_manager,
    ):
        """
        Test worktree preservation for simple task.

        Even though simple tasks complete quickly, the worktree should
        be preserved for human review before merging.

        Assertions:
            - Worktree exists at expected path
            - preserve_on_failure called (despite success)
            - Worktree not auto-merged
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player and Coach
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify worktree preserved
        mock_worktree_manager.preserve_on_failure.assert_called_once()

        # Verify worktree details in result
        assert result.worktree is not None
        assert result.worktree.task_id == task_scenario["task_id"]
        assert result.worktree.path == task_scenario["worktree_dir"]

    @pytest.mark.integration
    def test_simple_task_turn_history(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test turn history accuracy for simple task.

        Verifies that turn history contains complete and accurate
        information about the single-turn execution.

        Assertions:
            - Turn history length = 1
            - Turn record contains Player and Coach results
            - Timestamp recorded
            - Decision = "approve"
            - Feedback = None (approved on first turn)
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player and Coach
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        coach_result = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify turn history
        assert len(result.turn_history) == 1

        turn_record = result.turn_history[0]
        assert turn_record.turn == 1
        assert turn_record.player_result == player_result
        # Note: Coach result may have different structure due to CoachValidator
        # integration, but key fields should match
        assert turn_record.coach_result.task_id == coach_result.task_id
        assert turn_record.coach_result.turn == coach_result.turn
        assert turn_record.coach_result.agent_type == "coach"
        assert turn_record.coach_result.report["decision"] == "approve"
        assert turn_record.decision == "approve"
        assert turn_record.feedback is None  # No feedback on approval
        assert turn_record.timestamp is not None

    @pytest.mark.integration
    def test_simple_task_progress_display(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Test progress display integration for simple task.

        Verifies that progress display shows turn-by-turn updates
        even for simple single-turn tasks.

        Assertions:
            - start_turn called for Player and Coach
            - complete_turn called for Player and Coach
            - render_summary called with final status
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player and Coach
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify progress display calls
        assert mock_progress_display.start_turn.call_count == 2  # Player + Coach
        assert mock_progress_display.complete_turn.call_count == 2

        # Verify summary rendered
        mock_progress_display.render_summary.assert_called_once()
        call_args = mock_progress_display.render_summary.call_args
        assert call_args[1]["total_turns"] == 1
        assert call_args[1]["final_status"] == "approved"

    @pytest.mark.integration
    def test_simple_task_complexity_to_turns_mapping(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complexity-to-max_turns mapping for simple tasks.

        Verifies that simple tasks (complexity 1-3) are assigned
        max_turns = 3, allowing quick completion without excessive
        iteration overhead.

        Assertions:
            - Pre-loop determines max_turns = 3
            - Orchestrator updates max_turns based on pre-loop
            - Simple task completes well within max_turns
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player and Coach
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify max_turns set correctly
        assert result.pre_loop_result["max_turns"] == 3

        # Verify simple task completes efficiently
        assert result.total_turns <= 2, "Simple tasks should complete in 1-2 turns"


# ============================================================================
# Edge Cases for Simple Tasks
# ============================================================================


class TestSimpleTaskEdgeCases:
    """Test edge cases specific to simple tasks."""

    @pytest.mark.integration
    def test_simple_task_with_two_turn_feedback(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_coach_validator,
    ):
        """
        Test simple task that requires one round of feedback.

        Even simple tasks may need minor adjustments before approval.

        Scenario:
            - Turn 1: Coach provides minor feedback
            - Turn 2: Player addresses feedback, Coach approves

        Assertions:
            - Total turns = 2
            - Both turns recorded in history
            - Final decision = "approved"

        Note:
            This test requires overriding the CoachValidator mock to return
            feedback on the first turn and approve on the second turn.
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Import data classes for CoachValidator results
        from guardkit.orchestrator.quality_gates import (
            CoachValidationResult,
            QualityGateStatus,
        )

        # Override CoachValidator mock to provide feedback on first turn
        quality_gates_passed = QualityGateStatus(
            tests_passed=True,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )

        quality_gates_needs_work = QualityGateStatus(
            tests_passed=True,
            coverage_met=False,  # Coverage not met - needs feedback
            arch_review_passed=True,
            plan_audit_passed=True,
        )

        turn_1_result = CoachValidationResult(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
            quality_gates=quality_gates_needs_work,
            independent_tests=None,
            requirements=None,
            issues=[{"type": "coverage", "description": "Add more tests"}],
            rationale="Coverage below threshold",
        )

        turn_2_result = CoachValidationResult(
            task_id=task_scenario["task_id"],
            turn=2,
            decision="approve",
            quality_gates=quality_gates_passed,
            independent_tests=None,
            requirements=None,
            issues=[],
            rationale="All quality gates passed",
        )

        # Mock CoachValidator to return feedback on turn 1, approve on turn 2
        mock_coach_validator.return_value.validate.side_effect = [
            turn_1_result,
            turn_2_result,
        ]

        # Mock Player for both turns
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(task_id=task_scenario["task_id"], turn=1),
            make_player_result(task_id=task_scenario["task_id"], turn=2),
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify 2-turn completion
        assert result.total_turns == 2
        assert result.turn_history[0].decision == "feedback"
        assert result.turn_history[1].decision == "approve"
        assert result.final_decision == "approved"

    @pytest.mark.integration
    def test_simple_task_minimal_files(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test simple task with minimal file changes (1-2 files).

        Verifies that quality gates handle small changes efficiently.

        Assertions:
            - Files created = 2 (per simple scenario)
            - Quality gates pass
            - Single turn approval
        """
        # Skip if not simple scenario
        if task_scenario["complexity"] != 2:
            pytest.skip("Test requires simple scenario")

        # Mock Player with minimal files
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],  # 2 files
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement simple feature",
            acceptance_criteria=["Add functionality"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify minimal file changes handled
        assert result.success is True
        assert len(player_result.report["files_created"]) == task_scenario["files"]
        assert result.total_turns == 1


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
