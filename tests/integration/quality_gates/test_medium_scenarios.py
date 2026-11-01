"""
Integration tests for medium task scenarios (complexity 4-6).

These tests verify that medium-complexity tasks go through appropriate
feedback loops while still completing efficiently.

Test Coverage:
    - Feedback loop execution (2-3 turns)
    - Turn history tracking
    - Max turns exceeded

Coverage Target: >=85%
"""

import itertools

import pytest

from .conftest import (
    make_player_result,
    make_coach_result,
    evidence_for_turns,
    assert_quality_gates_passed,
    assert_worktree_preserved,
)

# Every test here is about the medium scenario, so only that scenario is
# generated (the shared fixture also offers the other two).
pytestmark = pytest.mark.parametrize("task_scenario", ["medium"], indirect=True)


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
            # The reviewer's one repair turn for a located finding
            # (AgentInvoker._apply_review_repair_turn).
            issues=[
                {
                    "type": "review_finding",
                    "severity": "major",
                    "location": "src/auth/tokens.py:40",
                    "description": (
                        "missing case at src/auth/tokens.py:40: Token refresh "
                        "not implemented"
                    ),
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
        mock_coach_validator,
    ):
        """
        Test medium task requiring multiple feedback cycles.

        The reviewer's verdict is advice: its located findings get one repair
        turn per task, and after that only real failures (here the project's
        own tests) send a turn back.

        Scenario:
            - Turn 1: Initial implementation, the reviewer's located finding
              on coupling (the one repair turn)
            - Turn 2: Coupling fixed, the project's edge-case test fails
            - Turn 3: Edge cases covered, tests pass, approved

        Assertions:
            - Total turns = 3
            - All turns tracked in history
            - Different feedback each turn
            - Final decision = "approved"
        """

        # The project's own tests: pass, fail, pass.
        mock_coach_validator.return_value.gather_evidence.side_effect = (
            evidence_for_turns(True, False, True)
        )

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
                        "type": "review_finding",
                        "severity": "major",
                        "location": "src/auth/service.py:18",
                        "description": (
                            "Tight coupling detected at src/auth/service.py:18"
                        ),
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
                        "type": "test_failure",
                        "severity": "must_fix",
                        "description": (
                            "The project's tests failed: the edge case "
                            "test_concurrent_access fails"
                        ),
                        "suggestion": "Handle concurrent access",
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
        mock_coach_validator,
    ):
        """
        Test medium task that reaches max_turns without approval.

        Scenario:
            - The project's own tests fail on all 5 turns, so every turn
              is sent back (the reviewer's verdict alone is advice)
            - Task never approved
            - Expected outcome: max_turns_exceeded

        Assertions:
            - Success = False
            - Final decision = "max_turns_exceeded"
            - Total turns = 5
            - Worktree preserved for inspection
        """

        # Mock all turns with feedback (never approve): the project's own
        # tests fail every turn, naming a different failing test each time,
        # and the simulated Player writes a real file on every turn (five
        # turns of real work that never earns approval).
        mock_coach_validator.return_value.gather_evidence.side_effect = (
            evidence_for_turns(*[False] * task_scenario["max_turns"])
        )
        _player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
        )
        _worktree_dir = task_scenario["worktree_dir"]
        _player_turns = itertools.count(1)
        _coach_turns = itertools.count(1)

        def _player_that_writes_something(*args, **kwargs):
            turn = next(_player_turns)
            (_worktree_dir / f"auth_service_turn_{turn}.py").write_text(
                f"# turn {turn} of the authentication service\n"
            )
            return _player_result

        def _coach_with_a_fresh_point(*args, **kwargs):
            turn = next(_coach_turns)
            return make_coach_result(
                task_id=task_scenario["task_id"],
                turn=turn,
                decision="feedback",
                issues=[
                    {
                        "type": "test_failure",
                        "severity": "must_fix",
                        "description": (
                            f"The project's tests failed: test_auth_case_{turn} "
                            f"still fails after the turn-{turn} changes"
                        ),
                        "suggestion": "Continue improvements",
                    }
                ],
            )

        mock_agent_invoker.invoke_player.side_effect = (
            _player_that_writes_something
        )
        mock_agent_invoker.invoke_coach.side_effect = _coach_with_a_fresh_point

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
