"""
Integration tests for failure scenarios in quality gates workflow.

These tests verify that the quality gates system properly handles
and reports failures at various stages of the workflow.

Test Coverage:
    - Test failure auto-fix loops (Phase 4.5)
    - Scope creep detection (Phase 5.5)
    - Low architectural scores blocking execution
    - Checkpoint rejection handling
    - Max turns exceeded scenarios

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from guardkit.orchestrator.quality_gates import (
    QualityGateBlocked,
    CheckpointRejectedError,
)

from .conftest import (
    make_player_result,
    make_coach_result,
    assert_worktree_preserved,
)


# ============================================================================
# Test Failure Tests (Phase 4.5)
# ============================================================================


class TestTestFailureScenarios:
    """Test quality gate behavior when tests fail."""

    @pytest.mark.integration
    def test_test_failures_trigger_coach_feedback(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test that failing tests trigger Coach feedback for fixes.

        When Player reports test failures, Coach should provide
        specific feedback to address the failures.

        Scenario:
            - Turn 1: Tests fail, Coach provides feedback
            - Turn 2: Tests pass, Coach approves

        Assertions:
            - Turn 1 decision = "feedback"
            - Feedback mentions test failures
            - Turn 2 decision = "approve"
        """
        # Mock Turn 1: Player with failing tests
        player_result_1 = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],
        )
        # Override to simulate test failure
        player_result_1.report["tests_passed"] = False

        coach_result_1 = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
            issues=[
                {
                    "type": "test_failure",
                    "severity": "critical",
                    "description": "3 unit tests failing",
                    "suggestion": "Fix assertion errors in test_authentication",
                }
            ],
        )

        # Mock Turn 2: Player fixes tests
        player_result_2 = make_player_result(
            task_id=task_scenario["task_id"],
            turn=2,
        )

        coach_result_2 = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=2,
            decision="approve",
        )

        mock_agent_invoker.invoke_player.side_effect = [
            player_result_1,
            player_result_2,
        ]

        mock_agent_invoker.invoke_coach.side_effect = [
            coach_result_1,
            coach_result_2,
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature with tests",
            acceptance_criteria=["All tests passing"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify auto-fix cycle
        assert result.total_turns == 2
        assert result.turn_history[0].decision == "feedback"
        assert "test" in result.turn_history[0].feedback.lower()
        assert result.turn_history[1].decision == "approve"
        assert result.final_decision == "approved"

    @pytest.mark.integration
    def test_persistent_test_failures_block_task(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test that persistent test failures eventually block the task.

        If tests keep failing after multiple attempts, task should
        reach max_turns and be blocked for manual intervention.

        Scenario:
            - All turns result in test failures
            - Max turns reached
            - Task blocked

        Assertions:
            - Success = False
            - Final decision = "max_turns_exceeded"
            - Error mentions test failures
        """
        # Mock all turns with test failures
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        player_result.report["tests_passed"] = False

        coach_result = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
            issues=[
                {
                    "type": "test_failure",
                    "description": "Tests still failing",
                    "suggestion": "Debug test failures",
                }
            ],
        )

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["All tests passing"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify task blocked
        assert result.success is False
        assert result.final_decision == "max_turns_exceeded"
        assert result.total_turns == task_scenario["max_turns"]

        # Verify worktree preserved for debugging
        assert_worktree_preserved(result)

    @pytest.mark.integration
    def test_low_coverage_triggers_feedback(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_task_work_results,
    ):
        """
        Test that low test coverage triggers Coach feedback.

        Coverage below thresholds should result in feedback
        requesting additional tests.

        Scenario:
            - Turn 1: Coverage 70% (below 80% threshold)
            - Coach requests more tests
            - Turn 2: Coverage 85%, approved

        Assertions:
            - Turn 1 decision = "feedback"
            - Feedback mentions coverage
            - Turn 2 decision = "approve"
        """
        # Modify task-work results to simulate low coverage
        mock_task_work_results["phase_4_5_tests"]["coverage"]["lines"] = 70

        # Mock Turn 1: Low coverage
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(task_id=task_scenario["task_id"], turn=1),
            make_player_result(task_id=task_scenario["task_id"], turn=2),
        ]

        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=1,
                decision="feedback",
                issues=[
                    {
                        "type": "coverage",
                        "description": "Line coverage 70% below threshold (80%)",
                        "suggestion": "Add tests for uncovered branches",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=2,
                decision="approve",
            ),
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Coverage >= 80%"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify coverage feedback cycle
        assert result.total_turns == 2
        assert result.turn_history[0].decision == "feedback"
        assert "coverage" in result.turn_history[0].feedback.lower()


# ============================================================================
# Scope Creep Tests (Phase 5.5)
# ============================================================================


class TestScopeCreepDetection:
    """Test scope creep detection in Phase 5.5 plan audit."""

    @pytest.mark.integration
    def test_scope_creep_detected_triggers_feedback(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_task_work_results,
    ):
        """
        Test that scope creep detection triggers Coach feedback.

        When implementation deviates significantly from plan
        (file count mismatch, excessive LOC variance), Coach
        should flag scope creep.

        Scenario:
            - Plan: 5 files, 250 LOC
            - Implementation: 8 files, 400 LOC
            - Scope creep detected

        Assertions:
            - Coach provides feedback about scope creep
            - Requests plan update or justification
        """
        # Modify task-work results to simulate scope creep
        mock_task_work_results["phase_5_5_plan_audit"]["scope_creep_detected"] = True
        mock_task_work_results["phase_5_5_plan_audit"]["loc_variance_percent"] = 60

        # Mock Player and Coach
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(task_id=task_scenario["task_id"], turn=1),
            make_player_result(task_id=task_scenario["task_id"], turn=2),
        ]

        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=1,
                decision="feedback",
                issues=[
                    {
                        "type": "scope_creep",
                        "severity": "major",
                        "description": "Implementation 60% larger than planned",
                        "suggestion": "Update plan or reduce scope",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=2,
                decision="approve",
            ),
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Match implementation plan"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify scope creep feedback
        assert result.total_turns == 2
        assert result.turn_history[0].decision == "feedback"
        assert "scope" in result.turn_history[0].feedback.lower() or "60" in result.turn_history[0].feedback

    @pytest.mark.integration
    def test_acceptable_variance_passes(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_task_work_results,
    ):
        """
        Test that acceptable LOC variance (within ±20%) passes audit.

        Small deviations from plan should be acceptable.

        Assertions:
            - LOC variance 5% passes
            - No scope creep detected
            - Coach approves
        """
        # Ensure task-work results show acceptable variance
        assert mock_task_work_results["phase_5_5_plan_audit"]["loc_variance_percent"] == 5
        assert mock_task_work_results["phase_5_5_plan_audit"]["scope_creep_detected"] is False

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
            requirements="Implement feature",
            acceptance_criteria=["Match plan within variance"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify passed without scope creep feedback
        assert result.success is True
        assert result.final_decision == "approved"


# ============================================================================
# Architectural Review Failures (Phase 2.5B)
# ============================================================================


class TestArchitecturalReviewFailures:
    """Test failures in architectural review quality gate."""

    @pytest.mark.integration
    def test_low_architectural_score_blocks_execution(
        self,
        task_scenario,
        mock_orchestrator,
        mock_pre_loop_gates,
    ):
        """
        Test that low architectural scores block task execution.

        If SOLID/DRY/YAGNI score is below threshold (< 60),
        pre-loop should block and prevent Player-Coach loop.

        Scenario:
            - Architectural score: 45 (below 60 threshold)
            - Pre-loop raises QualityGateBlocked
            - Task blocked before implementation

        Assertions:
            - Orchestration exits early
            - Final decision = "pre_loop_blocked"
            - Error mentions architectural review failure
        """
        from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

        # Configure pre-loop to raise QualityGateBlocked
        mock_pre_loop_gates.execute.side_effect = QualityGateBlocked(
            gate_name="architectural_review",
            score=45,
            threshold=60,
            message="SOLID/DRY/YAGNI score 45/100 below threshold (60)",
        )

        # Execute orchestration (should fail in pre-loop)
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Pass architectural review"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify pre-loop blocked
        assert result.success is False
        assert result.final_decision == "pre_loop_blocked"
        assert result.total_turns == 0  # No turns executed
        assert "architectural" in result.error.lower() or "score" in result.error.lower()

        # Verify worktree preserved for review
        assert_worktree_preserved(result)


# ============================================================================
# Checkpoint Rejection Tests (Phase 2.8)
# ============================================================================


class TestCheckpointRejection:
    """Test human checkpoint rejection scenarios."""

    @pytest.mark.integration
    def test_checkpoint_rejection_blocks_implementation(
        self,
        task_scenario,
        mock_orchestrator,
        mock_pre_loop_gates,
    ):
        """
        Test that human checkpoint rejection blocks implementation.

        When human rejects the plan at Phase 2.8 checkpoint,
        orchestration should exit without executing Player-Coach loop.

        Scenario:
            - Complex task triggers checkpoint
            - Human rejects plan
            - Implementation blocked

        Assertions:
            - Orchestration exits early
            - Final decision = "pre_loop_blocked"
            - No implementation turns executed
            - Error mentions checkpoint rejection
        """
        # Configure pre-loop to raise CheckpointRejectedError
        mock_pre_loop_gates.execute.side_effect = CheckpointRejectedError(
            reason="Human checkpoint rejected the implementation plan"
        )

        # Execute orchestration (should fail at checkpoint)
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement complex feature",
            acceptance_criteria=["Checkpoint approval required"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify checkpoint rejection
        assert result.success is False
        assert result.final_decision == "pre_loop_blocked"
        assert result.total_turns == 0
        assert "checkpoint" in result.error.lower() or "rejected" in result.error.lower()

        # Verify worktree preserved
        assert_worktree_preserved(result)


# ============================================================================
# Player/Coach Errors
# ============================================================================


class TestAgentErrors:
    """Test error handling for Player and Coach failures."""

    @pytest.mark.integration
    def test_player_error_exits_turn(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test that Player errors cause turn to exit with error decision.

        When Player fails (SDK timeout, file write error, etc.),
        the turn should exit immediately with error decision.

        Scenario:
            - Player fails on turn 1
            - Coach not invoked
            - Turn marked as error

        Assertions:
            - Total turns = 1
            - Turn decision = "error"
            - Coach result = None (not invoked)
            - Final decision = "error"
        """
        # Mock Player failure
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            success=False,
        )
        player_result.error = "SDK timeout after 300 seconds"

        mock_agent_invoker.invoke_player.return_value = player_result

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Complete successfully"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify Player error handling
        assert result.success is False
        assert result.final_decision == "error"
        assert result.total_turns == 1
        assert result.turn_history[0].decision == "error"
        assert result.turn_history[0].coach_result is None
        assert "SDK timeout" in result.error

        # Verify worktree preserved for debugging
        assert_worktree_preserved(result)

    @pytest.mark.integration
    def test_coach_error_exits_turn(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test that Coach errors cause turn to exit with error decision.

        When Coach fails (validation error, test execution failure, etc.),
        the turn should exit with error decision.

        Scenario:
            - Player succeeds
            - Coach fails
            - Turn marked as error

        Assertions:
            - Total turns = 1
            - Turn decision = "error"
            - Both Player and Coach results present
            - Final decision = "error"
        """
        # Mock Player success, Coach failure
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )

        coach_result = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
        )
        # Override success
        coach_result.success = False
        coach_result.error = "Test execution failed: timeout running pytest"

        mock_agent_invoker.invoke_player.return_value = player_result
        mock_agent_invoker.invoke_coach.return_value = coach_result

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Complete successfully"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify Coach error handling
        assert result.success is False
        assert result.final_decision == "error"
        assert result.total_turns == 1
        assert result.turn_history[0].decision == "error"
        assert result.turn_history[0].player_result is not None
        assert result.turn_history[0].coach_result is not None
        assert "Test execution failed" in result.error


# ============================================================================
# Max Turns Exceeded Tests
# ============================================================================


class TestMaxTurnsExceeded:
    """Test max_turns exceeded scenarios across complexities."""

    @pytest.mark.integration
    def test_max_turns_exceeded_preserves_worktree(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test that reaching max_turns preserves worktree for inspection.

        When max_turns is reached without approval, worktree should
        be preserved with all implementation work intact.

        Assertions:
            - Final decision = "max_turns_exceeded"
            - Worktree exists and preserved
            - All turns recorded in history
            - Error message helpful
        """
        # Mock all turns with feedback (never approve)
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )

        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement feature",
            acceptance_criteria=["Complete successfully"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify max_turns exceeded
        assert result.success is False
        assert result.final_decision == "max_turns_exceeded"
        assert result.total_turns == task_scenario["max_turns"]

        # Verify worktree preserved
        assert_worktree_preserved(result)

        # Verify helpful error message
        assert "Maximum turns" in result.error
        assert str(task_scenario["max_turns"]) in result.error


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
