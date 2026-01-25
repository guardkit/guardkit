"""
Integration tests for medium task scenarios (complexity 4-6).

These tests verify that medium-complexity tasks go through appropriate
feedback loops while still completing efficiently.

Test Coverage:
    - Feedback loop execution (2-3 turns)
    - Architectural review with standard thresholds
    - Turn history tracking
    - Quality gate enforcement

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
# Medium Scenario Tests (Complexity 4-6)
# ============================================================================


class TestMediumTaskScenarios:
    """Test medium complexity tasks requiring feedback loops."""

    @pytest.mark.integration
    def test_medium_task_two_turn_workflow(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test medium task completes in 2 turns with one feedback cycle.

        Scenario:
            - Complexity: 5 (authentication service)
            - Turn 1: Coach provides feedback
            - Turn 2: Player addresses feedback, Coach approves
            - Expected turns: 2
            - Expected outcome: Approved

        Quality Gates:
            - Pre-loop: Standard architectural review
            - Loop: Feedback → Approve
            - Post-loop: Worktree preserved

        Assertions:
            - Success = True
            - Total turns = 2
            - Turn 1 decision = "feedback"
            - Turn 2 decision = "approve"
            - Final decision = "approved"
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Mock Turn 1: Player implements, Coach provides feedback
        player_result_1 = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],
        )

        coach_result_1 = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
            issues=[
                {
                    "type": "missing_requirement",
                    "severity": "medium",
                    "description": "Token refresh not implemented",
                    "suggestion": "Add token refresh logic to handle expiration",
                }
            ],
        )

        # Mock Turn 2: Player addresses feedback, Coach approves
        player_result_2 = make_player_result(
            task_id=task_scenario["task_id"],
            turn=2,
            files_created=1,  # Added token refresh file
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
            requirements="Implement authentication service with token management",
            acceptance_criteria=[
                "Support OAuth2 flow",
                "Handle token refresh",
                "Implement session management",
            ],
            task_file_path=task_scenario["task_file"],
        )

        # Verify quality gates passed
        assert_quality_gates_passed(result)

        # Verify 2-turn workflow
        assert result.total_turns == 2
        assert result.turn_history[0].decision == "feedback"
        assert result.turn_history[1].decision == "approve"

        # Verify feedback provided in turn 1
        assert result.turn_history[0].feedback is not None
        assert "Token refresh" in result.turn_history[0].feedback

    @pytest.mark.integration
    def test_medium_task_three_turn_workflow(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test medium task requiring multiple feedback cycles.

        Scenario:
            - Turn 1: Initial implementation, feedback on architecture
            - Turn 2: Architecture improved, feedback on edge cases
            - Turn 3: Edge cases covered, approved

        Assertions:
            - Total turns = 3
            - All turns tracked in history
            - Different feedback each turn
            - Final decision = "approved"
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Mock Turn 1: Feedback on architecture
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(task_id=task_scenario["task_id"], turn=1),
            make_player_result(task_id=task_scenario["task_id"], turn=2),
            make_player_result(task_id=task_scenario["task_id"], turn=3),
        ]

        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=1,
                decision="feedback",
                issues=[
                    {
                        "type": "architecture",
                        "description": "Tight coupling detected",
                        "suggestion": "Extract interface for dependency injection",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=2,
                decision="feedback",
                issues=[
                    {
                        "type": "testing",
                        "description": "Edge case coverage incomplete",
                        "suggestion": "Add tests for concurrent access",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=3,
                decision="approve",
            ),
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support", "Token management"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify 3-turn workflow
        assert result.total_turns == 3
        assert result.turn_history[0].decision == "feedback"
        assert result.turn_history[1].decision == "feedback"
        assert result.turn_history[2].decision == "approve"

        # Verify different feedback each turn
        assert "coupling" in result.turn_history[0].feedback.lower()
        assert "edge case" in result.turn_history[1].feedback.lower()

        # Verify final approval
        assert result.final_decision == "approved"

    @pytest.mark.integration
    def test_medium_task_architectural_review(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_pre_loop_gates,
    ):
        """
        Test architectural review for medium complexity task.

        Medium tasks should undergo standard architectural review
        with reasonable SOLID/DRY/YAGNI thresholds.

        Assertions:
            - Architectural review executed in pre-loop
            - Score >= 85 (standard threshold)
            - Review influences implementation plan
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify pre-loop gates executed
        mock_pre_loop_gates.execute.assert_called_once()

        # Verify architectural review results
        assert result.pre_loop_result["architectural_score"] >= 85
        assert result.pre_loop_result["complexity"] == 5

    @pytest.mark.integration
    def test_medium_task_turn_history_tracking(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complete turn history tracking for medium task.

        Verifies that all turns are tracked with:
        - Player and Coach results
        - Timestamps
        - Decisions and feedback
        - Complete audit trail

        Assertions:
            - Turn history length matches total turns
            - Each turn has all required fields
            - Feedback properly tracked across turns
            - Timestamps in correct order
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Mock 2-turn workflow
        mock_agent_invoker.invoke_player.side_effect = [
            make_player_result(task_id=task_scenario["task_id"], turn=1),
            make_player_result(task_id=task_scenario["task_id"], turn=2),
        ]

        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=1,
                decision="feedback",
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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify complete turn history
        assert len(result.turn_history) == 2

        # Verify Turn 1 fields
        turn1 = result.turn_history[0]
        assert turn1.turn == 1
        assert turn1.player_result is not None
        assert turn1.coach_result is not None
        assert turn1.decision == "feedback"
        assert turn1.feedback is not None
        assert turn1.timestamp is not None

        # Verify Turn 2 fields
        turn2 = result.turn_history[1]
        assert turn2.turn == 2
        assert turn2.player_result is not None
        assert turn2.coach_result is not None
        assert turn2.decision == "approve"
        assert turn2.feedback is None  # No feedback on approval
        assert turn2.timestamp is not None

        # Verify timestamp ordering
        assert turn1.timestamp < turn2.timestamp

    @pytest.mark.integration
    def test_medium_task_complexity_to_max_turns(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complexity-to-max_turns mapping for medium tasks.

        Medium tasks (complexity 4-6) should be assigned max_turns = 5,
        allowing adequate feedback cycles without excessive iteration.

        Assertions:
            - Pre-loop determines max_turns = 5
            - Task completes within max_turns
            - Orchestrator respects dynamic max_turns
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify max_turns mapping
        assert result.pre_loop_result["max_turns"] == 5

        # Verify completion within max_turns
        assert result.total_turns <= 5


# ============================================================================
# Quality Gate Tests for Medium Tasks
# ============================================================================


class TestMediumTaskQualityGates:
    """Test quality gate enforcement for medium tasks."""

    @pytest.mark.integration
    def test_medium_task_test_coverage_enforcement(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_task_work_results,
    ):
        """
        Test that test coverage quality gates are enforced.

        Medium tasks should achieve:
        - Line coverage >= 85%
        - Branch coverage >= 80%
        - All tests passing

        Assertions:
            - task_work_results contains coverage data
            - Coverage meets thresholds
            - Coach validates coverage via task-work results
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Verify task-work results structure
        assert "phase_4_5_tests" in mock_task_work_results
        coverage = mock_task_work_results["phase_4_5_tests"]["coverage"]

        # Verify coverage thresholds
        assert coverage["lines"] >= 85, "Line coverage should be >= 85%"
        assert coverage["branches"] >= 80, "Branch coverage should be >= 80%"

        # Mock Player and Coach (Coach validates via task-work results)
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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify orchestration succeeded with quality gates
        assert result.success is True
        assert result.final_decision == "approved"

    @pytest.mark.integration
    def test_medium_task_plan_audit(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_task_work_results,
    ):
        """
        Test plan audit quality gate for medium tasks.

        Phase 5.5 plan audit should verify:
        - Implementation matches plan
        - No scope creep detected
        - LOC variance within acceptable range (±20%)

        Assertions:
            - task_work_results contains plan audit data
            - Files match plan
            - LOC variance acceptable
            - No scope creep
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Verify plan audit results
        assert "phase_5_5_plan_audit" in mock_task_work_results
        plan_audit = mock_task_work_results["phase_5_5_plan_audit"]

        assert plan_audit["files_match"] is True
        assert plan_audit["loc_variance_percent"] <= 20
        assert plan_audit["scope_creep_detected"] is False

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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify orchestration succeeded
        assert result.success is True


# ============================================================================
# Edge Cases for Medium Tasks
# ============================================================================


class TestMediumTaskEdgeCases:
    """Test edge cases specific to medium tasks."""

    @pytest.mark.integration
    def test_medium_task_reaches_max_turns(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test medium task that reaches max_turns without approval.

        Scenario:
            - All 5 turns result in feedback
            - Task never approved
            - Expected outcome: max_turns_exceeded

        Assertions:
            - Success = False
            - Final decision = "max_turns_exceeded"
            - Total turns = 5
            - Worktree preserved for inspection
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Mock all turns with feedback (never approve)
        mock_agent_invoker.invoke_player.return_value = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        mock_agent_invoker.invoke_coach.return_value = make_coach_result(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="feedback",
            issues=[
                {
                    "type": "ongoing",
                    "description": "Issues persist",
                    "suggestion": "Continue improvements",
                }
            ],
        )

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify max turns exceeded
        assert result.success is False
        assert result.final_decision == "max_turns_exceeded"
        assert result.total_turns == 5
        assert result.error is not None
        assert "Maximum turns" in result.error

        # Verify worktree preserved
        assert_worktree_preserved(result)

    @pytest.mark.integration
    def test_medium_task_moderate_file_count(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test medium task with moderate file changes (5 files).

        Verifies that quality gates handle moderate-sized changes
        appropriate to medium complexity tasks.

        Assertions:
            - Files created = 5 (per medium scenario)
            - Quality gates pass
            - 2-3 turn completion
        """
        # Skip if not medium scenario
        if task_scenario["complexity"] != 5:
            pytest.skip("Test requires medium scenario")

        # Mock Player with moderate files
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],  # 5 files
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
            requirements="Implement authentication service",
            acceptance_criteria=["OAuth2 support"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify moderate file changes handled
        assert result.success is True
        assert len(player_result.report["files_created"]) == task_scenario["files"]


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
