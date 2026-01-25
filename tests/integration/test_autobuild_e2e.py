"""
End-to-End Integration Tests for AutoBuild Orchestration

Tests complete AutoBuild workflow from task creation to worktree preservation,
using real file fixtures and mocked agent invocations for deterministic results.

Coverage Target: >=75%
Test Organization:
    - Test Simple Task: Single-turn approval workflow
    - Test Iterative Task: Multi-turn feedback workflow
    - Test Max Turns: Exhaustion scenario
    - Test Error Handling: Player/Coach failures

Architecture:
    - Uses real task fixtures (TEST-SIMPLE.md, TEST-ITERATION.md)
    - Mocks AgentInvoker for deterministic Player/Coach responses
    - Real WorktreeManager integration (uses temporary git repos)
    - Real ProgressDisplay integration (output suppressed in tests)
"""

import pytest
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult

# Import worktree components
from guardkit.worktrees import WorktreeManager


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_repo_root(tmp_path):
    """
    Create a temporary git repository for testing.

    Returns:
        Path: Root of temporary git repository
    """
    import subprocess

    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    # Create initial commit
    readme = repo_dir / "README.md"
    readme.write_text("# Test Repo", encoding='utf-8')
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    return repo_dir


@pytest.fixture
def simple_task_fixture(test_repo_root):
    """
    Load TEST-SIMPLE.md fixture and parse frontmatter.

    Returns:
        Dict[str, Any]: Task metadata and content
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "TEST-SIMPLE.md"
    content = fixture_path.read_text(encoding='utf-8')

    # Parse frontmatter
    parts = content.split('---', 2)
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()

    # Extract acceptance criteria
    criteria = []
    for line in body.split('\n'):
        if line.strip().startswith('- [ ]'):
            criteria.append(line.strip()[6:])

    return {
        'task_id': frontmatter['id'],
        'requirements': body.split('## Description')[1].split('##')[0].strip(),
        'acceptance_criteria': criteria,
        'expected_turns': frontmatter['autobuild']['expected_turns'],
        'complexity': frontmatter['complexity'],
    }


@pytest.fixture
def iteration_task_fixture(test_repo_root):
    """
    Load TEST-ITERATION.md fixture and parse frontmatter.

    Returns:
        Dict[str, Any]: Task metadata and content
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "TEST-ITERATION.md"
    content = fixture_path.read_text(encoding='utf-8')

    # Parse frontmatter
    parts = content.split('---', 2)
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()

    # Extract acceptance criteria
    criteria = []
    for line in body.split('\n'):
        if line.strip().startswith('- [ ]'):
            criteria.append(line.strip()[6:])

    return {
        'task_id': frontmatter['id'],
        'requirements': body.split('## Description')[1].split('##')[0].strip(),
        'acceptance_criteria': criteria,
        'expected_turns': frontmatter['autobuild']['expected_turns'],
        'complexity': frontmatter['complexity'],
    }


@pytest.fixture
def mock_agent_invoker_simple():
    """
    Mock AgentInvoker for simple single-turn approval workflow.

    Returns:
        Mock: Configured AgentInvoker mock with single-turn responses
    """
    invoker = Mock()

    # Turn 1: Player implements, Coach approves
    player_result = AgentInvocationResult(
        task_id="TEST-SIMPLE",
        turn=1,
        agent_type="player",
        success=True,
        report={
            "task_id": "TEST-SIMPLE",
            "turn": 1,
            "files_modified": [],
            "files_created": ["src/utils.py"],
            "tests_written": ["tests/test_utils.py"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "1 test passed",
            "implementation_notes": "Created simple utility function",
            "concerns": [],
            "requirements_addressed": ["Create utility function", "Add tests"],
            "requirements_remaining": [],
        },
        duration_seconds=8.5,
    )

    coach_result = AgentInvocationResult(
        task_id="TEST-SIMPLE",
        turn=1,
        agent_type="coach",
        success=True,
        report={
            "task_id": "TEST-SIMPLE",
            "turn": 1,
            "decision": "approve",
            "validation_results": {
                "requirements_met": ["Create utility function", "Add tests"],
                "tests_run": True,
                "tests_passed": True,
                "test_command": "pytest tests/test_utils.py",
                "test_output_summary": "All tests passed",
                "code_quality": "Good",
                "edge_cases_covered": [],
            },
            "rationale": "Simple implementation meets all requirements",
        },
        duration_seconds=5.2,
    )

    invoker.invoke_player = AsyncMock(return_value=player_result)
    invoker.invoke_coach = AsyncMock(return_value=coach_result)

    return invoker


@pytest.fixture
def mock_agent_invoker_iteration():
    """
    Mock AgentInvoker for multi-turn iterative workflow.

    Returns:
        Mock: Configured AgentInvoker mock with 3-turn workflow
    """
    invoker = Mock()

    # Turn 1: Player implements, Coach provides feedback
    player_result_1 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=1,
        agent_type="player",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 1,
            "files_modified": [],
            "files_created": ["src/auth.py", "tests/test_auth.py"],
            "tests_written": ["tests/test_auth.py"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "5 tests passed",
            "implementation_notes": "Implemented basic OAuth2 flow",
            "concerns": [],
            "requirements_addressed": ["OAuth2 flow", "Basic tests"],
            "requirements_remaining": ["Token refresh", "Error handling", "Edge cases"],
        },
        duration_seconds=15.3,
    )

    coach_result_1 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=1,
        agent_type="coach",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 1,
            "decision": "feedback",
            "issues": [
                {
                    "type": "missing_requirement",
                    "severity": "major",
                    "description": "Missing token refresh logic",
                    "requirement": "Handle token refresh logic",
                    "suggestion": "Add token refresh endpoint and logic",
                }
            ],
            "rationale": "Basic implementation good, but missing token refresh",
        },
        duration_seconds=6.8,
    )

    # Turn 2: Player addresses feedback, Coach provides more feedback
    player_result_2 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=2,
        agent_type="player",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 2,
            "files_modified": ["src/auth.py"],
            "files_created": [],
            "tests_written": ["tests/test_auth.py"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "8 tests passed",
            "implementation_notes": "Added token refresh logic",
            "concerns": [],
            "requirements_addressed": ["Token refresh"],
            "requirements_remaining": ["Security best practices", "Edge case coverage"],
        },
        duration_seconds=12.7,
    )

    coach_result_2 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=2,
        agent_type="coach",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 2,
            "decision": "feedback",
            "issues": [
                {
                    "type": "edge_case",
                    "severity": "minor",
                    "description": "Missing edge case: expired token handling",
                    "requirement": "Cover edge cases",
                    "suggestion": "Add test for expired token scenario",
                }
            ],
            "rationale": "Token refresh added, but edge case coverage incomplete",
        },
        duration_seconds=7.1,
    )

    # Turn 3: Player completes implementation, Coach approves
    player_result_3 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=3,
        agent_type="player",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 3,
            "files_modified": ["src/auth.py", "tests/test_auth.py"],
            "files_created": [],
            "tests_written": ["tests/test_auth.py"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "12 tests passed",
            "implementation_notes": "Added edge case handling and security improvements",
            "concerns": [],
            "requirements_addressed": ["Edge cases", "Security best practices"],
            "requirements_remaining": [],
        },
        duration_seconds=10.2,
    )

    coach_result_3 = AgentInvocationResult(
        task_id="TEST-ITERATION",
        turn=3,
        agent_type="coach",
        success=True,
        report={
            "task_id": "TEST-ITERATION",
            "turn": 3,
            "decision": "approve",
            "validation_results": {
                "requirements_met": [
                    "OAuth2 flow",
                    "Token refresh",
                    "Error handling",
                    "Security best practices",
                    "Edge case coverage",
                ],
                "tests_run": True,
                "tests_passed": True,
                "test_command": "pytest tests/test_auth.py",
                "test_output_summary": "All 12 tests passed",
                "code_quality": "Excellent",
                "edge_cases_covered": ["Expired tokens", "Invalid grants", "Network errors"],
            },
            "rationale": "Complete implementation with comprehensive testing",
        },
        duration_seconds=8.9,
    )

    # Configure mock to return results in sequence
    invoker.invoke_player = AsyncMock(
        side_effect=[player_result_1, player_result_2, player_result_3]
    )
    invoker.invoke_coach = AsyncMock(
        side_effect=[coach_result_1, coach_result_2, coach_result_3]
    )

    return invoker


@pytest.fixture
def mock_agent_invoker_max_turns():
    """
    Mock AgentInvoker that never approves (tests max_turns exhaustion).

    Returns:
        Mock: Configured AgentInvoker mock with perpetual feedback
    """
    invoker = Mock()

    # Create player result (always success)
    player_result = AgentInvocationResult(
        task_id="TEST-MAX-TURNS",
        turn=0,  # Will be overridden in side_effect
        agent_type="player",
        success=True,
        report={
            "task_id": "TEST-MAX-TURNS",
            "turn": 0,
            "files_modified": ["src/feature.py"],
            "files_created": [],
            "tests_written": ["tests/test_feature.py"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "Tests passing",
            "implementation_notes": "Implemented feature",
            "concerns": [],
            "requirements_addressed": ["Feature"],
            "requirements_remaining": [],
        },
        duration_seconds=10.0,
    )

    # Create coach result (always feedback, never approve)
    coach_result = AgentInvocationResult(
        task_id="TEST-MAX-TURNS",
        turn=0,  # Will be overridden in side_effect
        agent_type="coach",
        success=True,
        report={
            "task_id": "TEST-MAX-TURNS",
            "turn": 0,
            "decision": "feedback",
            "issues": [
                {
                    "type": "code_quality",
                    "severity": "minor",
                    "description": "Could be improved further",
                    "requirement": "Quality",
                    "suggestion": "Refine implementation",
                }
            ],
            "rationale": "Needs more refinement",
        },
        duration_seconds=7.0,
    )

    invoker.invoke_player = AsyncMock(return_value=player_result)
    invoker.invoke_coach = AsyncMock(return_value=coach_result)

    return invoker


@pytest.fixture
def mock_agent_invoker_player_error():
    """
    Mock AgentInvoker where Player fails immediately.

    Returns:
        Mock: Configured AgentInvoker mock with Player failure
    """
    invoker = Mock()

    player_result = AgentInvocationResult(
        task_id="TEST-ERROR",
        turn=1,
        agent_type="player",
        success=False,
        report={},
        duration_seconds=2.5,
        error="SDK timeout after 300 seconds",
    )

    invoker.invoke_player = AsyncMock(return_value=player_result)
    invoker.invoke_coach = AsyncMock()  # Should never be called

    return invoker


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestSimpleTaskWorkflow:
    """Test simple single-turn approval workflow."""

    def test_simple_task_single_turn_approval(
        self,
        test_repo_root,
        simple_task_fixture,
        mock_agent_invoker_simple,
    ):
        """Test complete workflow with simple task (1 turn, approval)."""
        # Create orchestrator
        orchestrator = AutoBuildOrchestrator(
            repo_root=test_repo_root,
            max_turns=5,
            agent_invoker=mock_agent_invoker_simple,
        )

        # Execute orchestration
        result = orchestrator.orchestrate(
            task_id=simple_task_fixture['task_id'],
            requirements=simple_task_fixture['requirements'],
            acceptance_criteria=simple_task_fixture['acceptance_criteria'],
        )

        # Verify result
        assert result.success is True
        assert result.task_id == simple_task_fixture['task_id']
        assert result.total_turns == 1
        assert result.final_decision == "approved"
        assert result.error is None

        # Verify turn history
        assert len(result.turn_history) == 1
        turn = result.turn_history[0]
        assert turn.turn == 1
        assert turn.decision == "approve"
        assert turn.player_result.success is True
        assert turn.coach_result.success is True

        # Verify worktree preserved
        assert result.worktree is not None
        assert result.worktree.task_id == simple_task_fixture['task_id']

        # Verify agent invocations
        mock_agent_invoker_simple.invoke_player.assert_called_once()
        mock_agent_invoker_simple.invoke_coach.assert_called_once()


@pytest.mark.integration
class TestIterativeTaskWorkflow:
    """Test multi-turn iterative workflow with feedback."""

    def test_iteration_task_multi_turn_feedback(
        self,
        test_repo_root,
        iteration_task_fixture,
        mock_agent_invoker_iteration,
    ):
        """Test complete workflow with iterative task (3 turns, feedback → approval)."""
        # Create orchestrator
        orchestrator = AutoBuildOrchestrator(
            repo_root=test_repo_root,
            max_turns=5,
            agent_invoker=mock_agent_invoker_iteration,
        )

        # Execute orchestration
        result = orchestrator.orchestrate(
            task_id=iteration_task_fixture['task_id'],
            requirements=iteration_task_fixture['requirements'],
            acceptance_criteria=iteration_task_fixture['acceptance_criteria'],
        )

        # Verify result
        assert result.success is True
        assert result.task_id == iteration_task_fixture['task_id']
        assert result.total_turns == 3
        assert result.final_decision == "approved"
        assert result.error is None

        # Verify turn progression
        assert len(result.turn_history) == 3

        # Turn 1: feedback
        turn1 = result.turn_history[0]
        assert turn1.turn == 1
        assert turn1.decision == "feedback"
        assert turn1.feedback is not None
        assert "token refresh" in turn1.feedback.lower()

        # Turn 2: feedback
        turn2 = result.turn_history[1]
        assert turn2.turn == 2
        assert turn2.decision == "feedback"
        assert turn2.feedback is not None

        # Turn 3: approved
        turn3 = result.turn_history[2]
        assert turn3.turn == 3
        assert turn3.decision == "approve"
        assert turn3.feedback is None

        # Verify worktree preserved
        assert result.worktree is not None

        # Verify agent invocations
        assert mock_agent_invoker_iteration.invoke_player.call_count == 3
        assert mock_agent_invoker_iteration.invoke_coach.call_count == 3


@pytest.mark.integration
class TestMaxTurnsExhaustion:
    """Test max_turns exceeded scenario."""

    def test_max_turns_exceeded(
        self,
        test_repo_root,
        simple_task_fixture,
        mock_agent_invoker_max_turns,
    ):
        """Test orchestration exits after max_turns without approval."""
        # Create orchestrator with low max_turns
        orchestrator = AutoBuildOrchestrator(
            repo_root=test_repo_root,
            max_turns=3,  # Low limit to test exhaustion
            agent_invoker=mock_agent_invoker_max_turns,
        )

        # Execute orchestration
        result = orchestrator.orchestrate(
            task_id="TEST-MAX-TURNS",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
        )

        # Verify result
        assert result.success is False
        assert result.task_id == "TEST-MAX-TURNS"
        assert result.total_turns == 3  # Should hit max_turns
        assert result.final_decision == "max_turns_exceeded"
        assert result.error is not None
        assert "Maximum turns" in result.error

        # Verify all turns had feedback (never approved)
        assert len(result.turn_history) == 3
        for turn in result.turn_history:
            assert turn.decision == "feedback"

        # Verify worktree still preserved
        assert result.worktree is not None


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling scenarios."""

    def test_player_error_exits_early(
        self,
        test_repo_root,
        mock_agent_invoker_player_error,
    ):
        """Test orchestration handles Player errors gracefully."""
        # Create orchestrator
        orchestrator = AutoBuildOrchestrator(
            repo_root=test_repo_root,
            max_turns=5,
            agent_invoker=mock_agent_invoker_player_error,
        )

        # Execute orchestration
        result = orchestrator.orchestrate(
            task_id="TEST-ERROR",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
        )

        # Verify result
        assert result.success is False
        assert result.task_id == "TEST-ERROR"
        assert result.total_turns == 1
        assert result.final_decision == "error"
        assert result.error is not None
        assert "SDK timeout" in result.error

        # Verify turn history
        assert len(result.turn_history) == 1
        turn = result.turn_history[0]
        assert turn.decision == "error"
        assert turn.coach_result is None  # Coach not invoked

        # Verify worktree preserved for debugging
        assert result.worktree is not None

        # Verify Coach was never invoked
        mock_agent_invoker_player_error.invoke_coach.assert_not_called()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
