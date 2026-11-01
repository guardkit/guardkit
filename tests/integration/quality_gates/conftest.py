"""
Shared fixtures for quality gates integration tests.

This module provides parametrized fixtures for testing different complexity
scenarios with the AutoBuild quality gates system.

Fixtures:
    - task_scenario: Parametrized task scenarios (simple, medium, complex).
      A test module that is about one scenario selects it with
      ``pytest.mark.parametrize("task_scenario", ["simple"], indirect=True)``,
      so the other scenarios are never generated for it.
    - mock_orchestrator: Fully mocked AutoBuildOrchestrator
    - mock_pre_loop_gates: Mocked PreLoopQualityGates
    - mock_coach_validator: Mocked CoachValidator whose evidence says the
      project's own tests ran (passing unless a test says otherwise)

Architecture:
    - Uses pytest parametrize for scenario-based testing
    - Mocks all external dependencies (worktrees, agents, file I/O)
"""

import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock

# Import test dependencies
import sys
_test_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates import PreLoopQualityGates
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult
from guardkit.worktrees import Worktree


# ============================================================================
# Helpers
# ============================================================================


def _git_init_seeded(path: Path, branch: str = "main") -> None:
    """Make ``path`` a real git repo with a `main` branch and one commit.

    The orchestrator writes evidence commits into the worktree it is handed.
    A directory that is not a git repo — or an initialised repo with no HEAD —
    makes those calls fail, which surfaces as an unrelated-looking scenario
    failure. Local identity is set so the seed commit works on a machine with
    no global git user.
    """
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        env=env,
    )
    run("init", "-b", "main")
    run("config", "user.email", "test@guardkit.local")
    run("config", "user.name", "GuardKit Test")
    run("commit", "--allow-empty", "-m", "seed")
    if branch != "main":
        run("checkout", "-q", "-b", branch)


# ============================================================================
# Parametrized Task Scenarios
# ============================================================================


SCENARIOS = {
    "simple": {
        "complexity": 2,
        "files": 2,
        "loc": 50,
        "max_turns": 3,
        "description": "Simple CRUD endpoint",
    },
    "medium": {
        "complexity": 5,
        "files": 5,
        "loc": 250,
        "max_turns": 5,
        "description": "Medium authentication service",
    },
    "complex": {
        "complexity": 8,
        "files": 10,
        "loc": 500,
        "max_turns": 7,
        "description": "Complex state machine with parallel execution",
    },
}


@pytest.fixture(params=list(SCENARIOS), ids=list(SCENARIOS))
def task_scenario(request, tmp_path):
    """
    Parametrized fixture providing task scenarios of varying complexity.

    Scenarios:
        - simple (complexity 2): 2 files, 50 LOC, 3 max turns
        - medium (complexity 5): 5 files, 250 LOC, 5 max turns
        - complex (complexity 8): 10 files, 500 LOC, 7 max turns

    The parameter is the scenario's name; a module about one scenario
    narrows it with an indirect parametrize (see the module docstring).

    Returns:
        Dict[str, Any]: Task scenario with complexity, files, LOC, max_turns
    """
    scenario = SCENARIOS[request.param]
    task_id = f"TASK-QG-{scenario['complexity']:02d}"

    # Create task file structure
    task_dir = tmp_path / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)

    task_file = task_dir / f"{task_id}.md"
    task_file.write_text(
        f"""---
id: {task_id}
title: {scenario['description']}
status: in_progress
complexity: {scenario['complexity']}
---

# {scenario['description']}

## Acceptance Criteria
- Implement core functionality
- Add comprehensive tests
- Pass quality gates
"""
    )

    # Create worktree structure.
    #
    # The orchestrator now commits evidence into the worktree, so the directory
    # has to be a real git repo or every scenario dies on the first git call.
    # A bare `git init` is not enough: the default branch name varies by git
    # config and an empty repo has no HEAD, so we pin `-b main` and seed one
    # commit.
    worktree_dir = tmp_path / ".guardkit" / "worktrees" / task_id
    worktree_dir.mkdir(parents=True)
    # A real AutoBuild worktree is checked out on its own branch, and the
    # orchestrator refuses to checkpoint anywhere else (worktree_checkpoints,
    # head identity), so the fixture repo is on the branch mock_worktree
    # declares, branched from the seeded main.
    _git_init_seeded(worktree_dir, branch=f"autobuild/{task_id}")

    return {
        "task_id": task_id,
        "task_file": task_file,
        "worktree_dir": worktree_dir,
        "tmp_path": tmp_path,
        **scenario,
    }


# ============================================================================
# Mock Orchestrator Components
# ============================================================================


@pytest.fixture
def mock_worktree(task_scenario):
    """Create mock Worktree instance for scenario."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = task_scenario["task_id"]
    worktree.path = task_scenario["worktree_dir"]
    worktree.branch_name = f"autobuild/{task_scenario['task_id']}"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = mock_worktree.path.parent
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker with AsyncMock.

    The orchestrator reads three things off the invoker that a bare ``Mock``
    answers with another ``Mock``, which then blows up downstream:

    - ``_calculate_sdk_timeout(...)`` is compared against / arithmetic'd with
      numbers, so it must return a real ``int``.
    - ``sdk_timeout_seconds`` is the base the orchestrator budgets against.
    - ``_invoke_with_role(...)`` is awaited, so it must be an ``AsyncMock``;
      a plain ``Mock`` returns a non-awaitable.
    """
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    invoker.sdk_timeout_seconds = 1200
    invoker._calculate_sdk_timeout = Mock(return_value=1200)
    invoker._invoke_with_role = AsyncMock()
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


# ============================================================================
# Mock Quality Gates
# ============================================================================


@pytest.fixture
def mock_pre_loop_gates(task_scenario):
    """
    Create mock PreLoopQualityGates with scenario-based results.

    Generates realistic pre-loop results based on task complexity:
    - Simple tasks: Auto-proceed, low architectural score requirement
    - Medium tasks: Quick checkpoint, standard architectural review
    - Complex tasks: Full checkpoint required, comprehensive review
    """
    gates = Mock(spec=PreLoopQualityGates)

    # Build pre-loop result based on complexity
    complexity = task_scenario["complexity"]

    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    pre_loop_result = PreLoopResult(
        plan={
            "files_to_create": [f"src/file{i}.py" for i in range(task_scenario["files"])],
            "files_to_modify": [],
            "estimated_loc": task_scenario["loc"],
            "phases": ["Phase 1: Setup", "Phase 2: Implementation", "Phase 3: Tests"],
        },
        plan_path=str(
            task_scenario["worktree_dir"]
            / ".claude"
            / "task-plans"
            / f"{task_scenario['task_id']}-implementation-plan.md"
        ),
        complexity=complexity,
        max_turns=task_scenario["max_turns"],
        checkpoint_passed=True,
        architectural_score=85 if complexity <= 6 else 92,
        clarifications={
            "scope": "standard",
            "testing": "comprehensive" if complexity >= 7 else "standard",
        },
    )

    gates.execute.return_value = pre_loop_result
    gates.validate_prerequisites.return_value = True
    gates.supported_options = {
        "no_questions": "Skip clarification questions",
        "with_questions": "Force clarification",
    }

    return gates


# ============================================================================
# Mock Coach Validator
# ============================================================================


def make_evidence_bundle(tests_passed: bool = True) -> CoachEvidenceBundle:
    """A complete evidence bundle whose changed parts' tests ran.

    ``tests_passed`` says whether the project's own tests passed. A bundle
    with no test result, or one whose check could not run, stops the turn as
    a Coach failure (31 October 2026), so the check here always ran.
    """
    return CoachEvidenceBundle(
        gathering_status="complete",
        task_type="feature",
        profile_name="feature",
        independent_tests=IndependentTestResult(
            tests_passed=tests_passed,
            test_command="true" if tests_passed else "false",
            test_output_summary="passed" if tests_passed else "3 tests failed",
            duration_seconds=0.0,
        ),
    )



@pytest.fixture
def mock_coach_validator(task_scenario):
    """
    Mock CoachValidator, so the project's checks are not run.

    The orchestrator asks this validator only for evidence
    (``gather_evidence``), and stops the turn when the bundle says the
    project's check could not run (31 October 2026). Here the bundle says the
    changed parts' tests ran and passed, keeping the run hermetic; the turn's
    decision is the one the test's ``invoke_coach`` mock returns.

    A test whose project tests fail on some turns sets
    ``mock_coach_validator.return_value.gather_evidence.side_effect`` to
    :func:`evidence_for_turns` with one entry per turn.
    """
    with patch("guardkit.orchestrator.autobuild.CoachValidator") as mock_validator_class:
        mock_instance = MagicMock()
        mock_instance.gather_evidence.return_value = make_evidence_bundle()
        mock_validator_class.return_value = mock_instance

        yield mock_validator_class


def evidence_for_turns(*tests_passed: bool) -> list:
    """One evidence bundle per turn, in order: whether the project's own
    tests passed on that turn."""
    return [make_evidence_bundle(tests_passed=passed) for passed in tests_passed]


# ============================================================================
# Agent Result Helpers
# ============================================================================


def make_player_result(
    task_id: str,
    turn: int = 1,
    success: bool = True,
    files_created: int = 3,
) -> AgentInvocationResult:
    """
    Create realistic Player AgentInvocationResult.

    Args:
        task_id: Task identifier
        turn: Turn number
        success: Whether Player succeeded
        files_created: Number of files created

    Returns:
        AgentInvocationResult: Player agent result
    """
    report = {}
    if success:
        report = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": [f"src/file{i}.py" for i in range(2)],
            "files_created": [f"src/new{i}.py" for i in range(files_created)],
            "tests_written": [f"tests/test_file{i}.py" for i in range(3)],
            "tests_run": True,
            "tests_passed": True,
            "implementation_notes": "Implemented feature according to plan",
            "concerns": [],
            "requirements_addressed": ["All acceptance criteria met"],
            "requirements_remaining": [],
        }

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report=report,
        duration_seconds=15.0,
        error=None if success else "Player error",
    )


def make_coach_result(
    task_id: str,
    turn: int = 1,
    decision: str = "approve",
    issues: list = None,
) -> AgentInvocationResult:
    """
    Create realistic Coach AgentInvocationResult.

    Args:
        task_id: Task identifier
        turn: Turn number
        decision: "approve" or "feedback"
        issues: List of issues (for feedback decision)

    Returns:
        AgentInvocationResult: Coach agent result
    """
    report = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
    }

    if decision == "approve":
        report["validation_results"] = {
            "requirements_met": ["All acceptance criteria"],
            "tests_run": True,
            "tests_passed": True,
            "code_quality": "Excellent",
        }
        report["rationale"] = "Implementation meets all quality gates"
    else:  # feedback
        report["issues"] = issues or [
            {
                "type": "missing_test",
                "severity": "medium",
                "description": "Edge case coverage incomplete",
                "suggestion": "Add tests for null input handling",
            }
        ]
        report["rationale"] = "Implementation needs improvements"

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=8.0,
        error=None,
    )


# ============================================================================
# Integrated Orchestrator Fixture
# ============================================================================


@pytest.fixture
def mock_orchestrator(
    task_scenario,
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display,
    mock_pre_loop_gates,
    mock_coach_validator,
):
    """
    Create fully mocked AutoBuildOrchestrator with all dependencies.

    This fixture provides a complete orchestrator setup ready for
    integration testing with all components mocked.
    """
    orchestrator = AutoBuildOrchestrator(
        repo_root=task_scenario["tmp_path"],
        max_turns=task_scenario["max_turns"],
        enable_pre_loop=True,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
    )

    return orchestrator


# ============================================================================
# Helper Functions for Test Assertions
# ============================================================================


def assert_quality_gates_passed(result: OrchestrationResult):
    """
    Assert that all quality gates passed in orchestration result.

    Args:
        result: OrchestrationResult to validate

    Raises:
        AssertionError: If any quality gate failed
    """
    assert result.success is True, "Orchestration should succeed"
    assert result.pre_loop_result is not None, "Pre-loop results should exist"
    assert result.pre_loop_result.get("checkpoint_passed") is True, "Checkpoint should pass"
    assert len(result.turn_history) > 0, "Should have turn history"
    assert result.final_decision == "approved", "Should be approved by Coach"


def assert_complexity_based_turns(result: OrchestrationResult, complexity: int):
    """
    Assert that turn count aligns with task complexity.

    Args:
        result: OrchestrationResult to validate
        complexity: Expected task complexity

    Raises:
        AssertionError: If turn count doesn't match complexity expectations
    """
    if complexity <= 3:
        # Simple tasks should complete in 1-2 turns
        assert result.total_turns <= 2, f"Simple tasks should complete quickly, got {result.total_turns} turns"
    elif complexity <= 6:
        # Medium tasks may need 2-3 turns
        assert result.total_turns <= 3, f"Medium tasks should complete in 2-3 turns, got {result.total_turns} turns"
    else:
        # Complex tasks may need 3+ turns
        assert result.total_turns >= 1, f"Complex tasks should execute at least 1 turn, got {result.total_turns} turns"


def assert_worktree_preserved(result: OrchestrationResult):
    """
    Assert that worktree was preserved for human review.

    Args:
        result: OrchestrationResult to validate

    Raises:
        AssertionError: If worktree wasn't preserved
    """
    assert result.worktree is not None, "Worktree should exist"
    assert result.worktree.path.exists(), "Worktree path should exist"
