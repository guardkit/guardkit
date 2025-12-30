"""
Shared fixtures for quality gates integration tests.

This module provides parametrized fixtures for testing different complexity
scenarios with the AutoBuild quality gates system.

Fixtures:
    - task_scenario: Parametrized task scenarios (simple, medium, complex)
    - mock_orchestrator: Fully mocked AutoBuildOrchestrator
    - mock_pre_loop_gates: Mocked PreLoopQualityGates
    - mock_task_work_results: Simulated task-work quality gate results

Architecture:
    - Uses pytest parametrize for scenario-based testing
    - Mocks all external dependencies (worktrees, agents, file I/O)
    - Provides realistic task-work result data structures
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from dataclasses import dataclass

# Import test dependencies
import sys
_test_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates import (
    PreLoopQualityGates,
    CoachValidator,
    CoachValidationResult,
    QualityGateStatus,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Parametrized Task Scenarios
# ============================================================================


@pytest.fixture(
    params=[
        pytest.param(
            {
                "complexity": 2,
                "files": 2,
                "loc": 50,
                "max_turns": 3,
                "description": "Simple CRUD endpoint",
            },
            id="simple",
        ),
        pytest.param(
            {
                "complexity": 5,
                "files": 5,
                "loc": 250,
                "max_turns": 5,
                "description": "Medium authentication service",
            },
            id="medium",
        ),
        pytest.param(
            {
                "complexity": 8,
                "files": 10,
                "loc": 500,
                "max_turns": 7,
                "description": "Complex state machine with parallel execution",
            },
            id="complex",
        ),
    ]
)
def task_scenario(request, tmp_path):
    """
    Parametrized fixture providing task scenarios of varying complexity.

    Scenarios:
        - simple (complexity 2): 2 files, 50 LOC, 3 max turns
        - medium (complexity 5): 5 files, 250 LOC, 5 max turns
        - complex (complexity 8): 10 files, 500 LOC, 7 max turns

    Returns:
        Dict[str, Any]: Task scenario with complexity, files, LOC, max_turns
    """
    scenario = request.param
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

    # Create worktree structure
    worktree_dir = tmp_path / ".guardkit" / "worktrees" / task_id
    worktree_dir.mkdir(parents=True)

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
    """Create mock AgentInvoker with AsyncMock."""
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


@pytest.fixture
def mock_task_work_results(task_scenario, mock_worktree):
    """
    Create simulated task-work quality gate results.

    Simulates the results files that would be created by task-work during
    implementation, including test results, coverage, and architectural scores.
    """
    results_dir = mock_worktree.path / ".guardkit" / "autobuild" / task_scenario["task_id"]
    results_dir.mkdir(parents=True, exist_ok=True)

    # Generate realistic results based on complexity
    complexity = task_scenario["complexity"]

    task_work_results = {
        "task_id": task_scenario["task_id"],
        "phase_4_5_tests": {
            "status": "passed",
            "tests_total": 10 + complexity * 2,
            "tests_passed": 10 + complexity * 2,
            "tests_failed": 0,
            "coverage": {
                "lines": 85 + (complexity if complexity <= 5 else 5),
                "branches": 80,
                "functions": 90,
            },
        },
        "phase_5_review": {
            "code_quality_score": 88,
            "maintainability": "good",
        },
        "phase_5_5_plan_audit": {
            "files_match": True,
            "loc_variance_percent": 5,
            "scope_creep_detected": False,
        },
        "files_created": [f"src/file{i}.py" for i in range(task_scenario["files"])],
        "files_modified": [],
        "architectural_score": 85 if complexity <= 6 else 92,
    }

    # Write results to file
    results_file = results_dir / "task_work_results.json"
    results_file.write_text(json.dumps(task_work_results, indent=2))

    return task_work_results


# ============================================================================
# Mock Coach Validator
# ============================================================================


@pytest.fixture
def mock_coach_validator(task_scenario, mock_task_work_results):
    """
    Mock CoachValidator that validates task-work results.

    Returns realistic validation results based on the simulated
    task-work quality gate results.
    """
    with patch("guardkit.orchestrator.autobuild.CoachValidator") as mock_validator_class:
        mock_instance = MagicMock()

        # Build validation result
        quality_gate_status = QualityGateStatus(
            tests_passed=True,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )

        validation_result = CoachValidationResult(
            task_id=task_scenario["task_id"],
            turn=1,
            decision="approve",
            quality_gates=quality_gate_status,
            independent_tests=None,
            requirements=None,
            issues=[],
            rationale="Implementation meets all quality gates",
        )

        mock_instance.validate.return_value = validation_result
        mock_instance.save_decision.return_value = None
        mock_validator_class.return_value = mock_instance

        yield mock_validator_class


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
