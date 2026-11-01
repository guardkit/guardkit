"""
Integration tests for complex task scenarios (complexity 7+).

These tests verify that complex tasks trigger human checkpoints
and support extended feedback loops for iterative refinement.

Test Coverage:
    - Human checkpoint triggering (Phase 2.8)
    - Extended feedback loops (3+ turns)
    - Complex quality gate orchestration

Coverage Target: >=85%
"""

import pytest

from .conftest import (
    make_player_result,
    make_coach_result,
    evidence_for_turns,
)

# Every test here is about the complex scenario, so only that scenario is
# generated (the shared fixture also offers the other two).
pytestmark = pytest.mark.parametrize("task_scenario", ["complex"], indirect=True)


# ============================================================================
# Complex Scenario Tests (Complexity 7+)
# ============================================================================


class TestComplexTaskScenarios:
    """Test complex tasks requiring checkpoints and extended loops."""

    @pytest.mark.integration
    def test_complex_task_human_checkpoint_triggered(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_pre_loop_gates,
    ):
        """
        Test that complex tasks trigger Phase 2.8 human checkpoint.

        Complex tasks (complexity >= 7) should pause at Phase 2.8
        for human review and approval before proceeding to implementation.

        Scenario:
            - Complexity: 8 (complex state machine)
            - Human checkpoint triggered in pre-loop
            - Checkpoint passed (simulated approval)
            - Implementation proceeds

        Assertions:
            - Pre-loop gates executed
            - Checkpoint triggered (complexity >= 7)
            - checkpoint_passed = True
            - Implementation proceeds after approval
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
            requirements="Implement complex state machine with parallel execution",
            acceptance_criteria=[
                "State transitions",
                "Parallel execution support",
                "Error handling",
            ],
            task_file_path=task_scenario["task_file"],
        )

        # Verify pre-loop gates executed
        mock_pre_loop_gates.execute.assert_called_once()

        # Verify checkpoint triggered and passed
        assert result.pre_loop_result is not None
        assert result.pre_loop_result["complexity"] == 8
        assert result.pre_loop_result["checkpoint_passed"] is True

        # Verify implementation proceeded
        assert result.success is True
        assert result.final_decision == "approved"

    @pytest.mark.integration
    def test_complex_task_extended_feedback_loop(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_coach_validator,
    ):
        """
        Test complex task requiring 4+ turns for completion.

        The reviewer's verdict is advice: its located findings get one repair
        turn per task, and after that only real failures (here the project's
        own tests) send a turn back.

        Scenario:
            - Turn 1: the reviewer's located finding on coupling (the one
              repair turn)
            - Turn 2: the project's parallel-execution test fails
            - Turn 3: the project's lock-contention test fails
            - Turn 4: tests pass, approved

        Assertions:
            - Total turns = 4
            - Different feedback each turn
            - Final decision = "approved"
        """

        # Mock 4-turn workflow. The project's own tests: pass, fail, fail,
        # pass. The simulated Player writes a file on each turn: this test's
        # premise is a build that IS making progress.
        mock_coach_validator.return_value.gather_evidence.side_effect = (
            evidence_for_turns(True, False, False, True)
        )
        _player_results = iter(
            [
                make_player_result(task_id=task_scenario["task_id"], turn=i)
                for i in range(1, 5)
            ]
        )
        _worktree_dir = task_scenario["worktree_dir"]

        def _player_that_writes_something(*args, **kwargs):
            result = next(_player_results)
            (_worktree_dir / f"state_machine_turn_{result.turn}.py").write_text(
                f"# turn {result.turn} implementation\n"
            )
            return result

        mock_agent_invoker.invoke_player.side_effect = (
            _player_that_writes_something
        )

        mock_agent_invoker.invoke_coach.side_effect = [
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=1,
                decision="feedback",
                issues=[
                    {
                        "type": "review_finding",
                        "severity": "major",
                        "location": "src/state_machine.py:57",
                        "description": (
                            "State machine coupling too tight at "
                            "src/state_machine.py:57"
                        ),
                        "suggestion": "Extract state interface",
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
                            "The project's tests failed: "
                            "test_parallel_execution fails"
                        ),
                        "suggestion": "Fix the parallel execution path",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=3,
                decision="feedback",
                issues=[
                    {
                        "type": "test_failure",
                        "severity": "must_fix",
                        "description": (
                            "The project's tests failed: "
                            "test_lock_contention times out"
                        ),
                        "suggestion": "Use lock-free data structures",
                    }
                ],
            ),
            make_coach_result(
                task_id=task_scenario["task_id"],
                turn=4,
                decision="approve",
            ),
        ]

        # Execute orchestration
        result = mock_orchestrator.orchestrate(
            task_id=task_scenario["task_id"],
            requirements="Implement complex state machine",
            acceptance_criteria=["State transitions", "Parallel execution"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify 4-turn workflow
        assert result.total_turns == 4
        assert result.final_decision == "approved"

        # Verify different feedback each turn
        assert "coupling" in result.turn_history[0].feedback.lower()
        assert "parallel" in result.turn_history[1].feedback.lower()
        assert "lock" in result.turn_history[2].feedback.lower()

    @pytest.mark.integration
    def test_complex_task_max_turns_increased(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complex tasks assigned higher max_turns.

        Complex tasks (complexity 7-10) should be assigned max_turns = 7
        to allow adequate time for iterative refinement.

        Assertions:
            - max_turns = 7 (based on complexity mapping)
            - Orchestrator respects dynamic max_turns
            - Adequate iterations allowed
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
            requirements="Implement complex state machine",
            acceptance_criteria=["State transitions"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify max_turns increased for complex task
        assert result.pre_loop_result["max_turns"] == 7

# ============================================================================
# Checkpoint Scenarios
# ============================================================================


class TestComplexTaskCheckpoints:
    """Test human checkpoint behavior for complex tasks."""

    @pytest.mark.integration
    def test_checkpoint_approval_proceeds_to_implementation(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
        mock_pre_loop_gates,
    ):
        """
        Test checkpoint approval allows implementation to proceed.

        When human approves at Phase 2.8 checkpoint, orchestration
        should continue to Player-Coach loop.

        Assertions:
            - Checkpoint passed
            - Implementation loop executed
            - Final decision = "approved"
        """

        # Pre-loop gates will return checkpoint_passed = True (simulated approval)

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
            requirements="Implement complex state machine",
            acceptance_criteria=["State transitions"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify checkpoint approved and implementation proceeded
        assert result.pre_loop_result["checkpoint_passed"] is True
        assert result.total_turns >= 1, "Implementation should execute"
        assert result.final_decision == "approved"


# ============================================================================
# Large File Count Tests
# ============================================================================


class TestComplexTaskScaling:
    """Test complex tasks with large file counts."""

    @pytest.mark.integration
    def test_complex_task_many_files(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complex task with many file changes (10+ files).

        Complex tasks often modify/create many files.
        Quality gates should handle this efficiently.

        Assertions:
            - Files created = 10 (per complex scenario)
            - Quality gates pass
            - Extended feedback loop completes
        """

        # Mock Player with many files
        player_result = make_player_result(
            task_id=task_scenario["task_id"],
            turn=1,
            files_created=task_scenario["files"],  # 10 files
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
            requirements="Implement complex state machine",
            acceptance_criteria=["State transitions"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify many files handled
        assert result.success is True
        assert len(player_result.report["files_created"]) == task_scenario["files"]

    @pytest.mark.integration
    def test_complex_task_high_loc_count(
        self,
        task_scenario,
        mock_orchestrator,
        mock_agent_invoker,
    ):
        """
        Test complex task with high LOC count (500+ lines).

        Verifies that quality gates handle large implementations
        without performance degradation.

        Assertions:
            - Estimated LOC = 500+ (the plan reaches the result)
            - Orchestration completes successfully
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
            requirements="Implement complex state machine",
            acceptance_criteria=["State transitions"],
            task_file_path=task_scenario["task_file"],
        )

        # Verify high LOC handled
        assert result.success is True
        plan = result.pre_loop_result["plan"]
        assert plan["estimated_loc"] == task_scenario["loc"]  # 500 LOC


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
