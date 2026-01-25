"""
Integration Tests for Pre-loop + Player Flow in AutoBuild

Tests the complete pre-loop quality gates flow and its integration with the Player agent,
verifying that design phase creates plans that the Player can consume.

Test Coverage:
    - Pre-loop creates implementation plan for Player (happy path)
    - Pre-loop fails appropriately when plan is not generated
    - Player fails appropriately when plan is missing

Architecture:
    - Uses mock fixtures and temporary directories
    - Mocks TaskWorkInterface to avoid actual task-work execution
    - Tests PreLoopQualityGates and its integration with Player

Run with:
    pytest tests/integration/test_autobuild_preloop.py -v
    pytest tests/integration/test_autobuild_preloop.py -v --cov=guardkit/orchestrator

Coverage Target: >=85%
Test Count: 3 tests
"""

import json
import pytest
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.quality_gates.pre_loop import (
    PreLoopQualityGates,
    PreLoopResult,
)
from guardkit.orchestrator.quality_gates.task_work_interface import (
    TaskWorkInterface,
    DesignPhaseResult,
)
from guardkit.orchestrator.quality_gates.exceptions import (
    QualityGateBlocked,
)
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
)
from guardkit.orchestrator.exceptions import (
    PlanNotFoundError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_with_task(tmp_path):
    """
    Create a mock worktree structure with task file and directories.

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create task directories
    design_approved_dir = worktree / "tasks" / "design_approved"
    design_approved_dir.mkdir(parents=True)

    in_progress_dir = worktree / "tasks" / "in_progress"
    in_progress_dir.mkdir(parents=True)

    backlog_dir = worktree / "tasks" / "backlog"
    backlog_dir.mkdir(parents=True)

    # Create task file in backlog state (pre-loop will run design phase)
    task_file = backlog_dir / "TASK-PRELOOP-001-test-preloop.md"
    task_file.write_text("""---
id: TASK-PRELOOP-001
title: Test Pre-loop Task
status: backlog
created: 2025-12-31T10:00:00Z
priority: medium
complexity: 5
---

# Test Pre-loop Task

## Description

Implement feature X for testing pre-loop quality gates.

## Requirements

- Implement feature X
- Add comprehensive tests
- Ensure code quality

## Acceptance Criteria

- [ ] Feature X works correctly
- [ ] All tests pass
- [ ] Coverage >= 80%
""", encoding='utf-8')

    # Create .claude directory for plans
    claude_dir = worktree / ".claude" / "task-plans"
    claude_dir.mkdir(parents=True)

    # Create .guardkit/autobuild directory for reports
    autobuild_dir = worktree / ".guardkit" / "autobuild" / "TASK-PRELOOP-001"
    autobuild_dir.mkdir(parents=True)

    return worktree


@pytest.fixture
def mock_worktree_with_plan(mock_worktree_with_task):
    """
    Create a mock worktree with an implementation plan already present.

    Returns:
        Path: Path to worktree root
    """
    # Create implementation plan
    plan_dir = mock_worktree_with_task / ".claude" / "task-plans"
    plan_file = plan_dir / "TASK-PRELOOP-001-implementation-plan.md"
    plan_file.write_text("""# Implementation Plan: TASK-PRELOOP-001

## Overview

This plan covers the implementation of feature X.

## Steps

1. Create feature module
2. Implement core logic
3. Add unit tests
4. Add integration tests
5. Update documentation

## Files to Create

- src/feature.py
- tests/test_feature.py

## Estimated Complexity: 5/10
""", encoding='utf-8')

    return mock_worktree_with_task


@pytest.fixture
def mock_design_phase_result(mock_worktree_with_plan) -> DesignPhaseResult:
    """
    Create a mock DesignPhaseResult with valid plan.

    Returns:
        DesignPhaseResult: Mock result from task-work --design-only
    """
    plan_path = mock_worktree_with_plan / ".claude" / "task-plans" / "TASK-PRELOOP-001-implementation-plan.md"

    return DesignPhaseResult(
        implementation_plan={
            "overview": "Implement feature X",
            "steps": [
                "Create feature module",
                "Implement core logic",
                "Add unit tests",
            ],
            "files_to_create": ["src/feature.py", "tests/test_feature.py"],
        },
        plan_path=str(plan_path),
        complexity={"score": 5, "rationale": "Medium complexity task"},
        checkpoint_result="approved",
        architectural_review={
            "score": 85,
            "solid_score": 80,
            "dry_score": 90,
            "yagni_score": 85,
            "recommendations": [],
        },
        clarifications={
            "scope": "standard",
            "testing_approach": "integration",
        },
    )


@pytest.fixture
def mock_design_phase_result_no_plan() -> DesignPhaseResult:
    """
    Create a mock DesignPhaseResult with no plan path.

    Returns:
        DesignPhaseResult: Mock result with missing plan
    """
    return DesignPhaseResult(
        implementation_plan={},
        plan_path=None,  # No plan path returned
        complexity={"score": 5},
        checkpoint_result="approved",
        architectural_review={},
        clarifications={},
    )


# ============================================================================
# TestPreLoopCreatesPlansForPlayer - Happy Path Tests
# ============================================================================


@pytest.mark.integration
class TestPreLoopCreatesPlansForPlayer:
    """Test that pre-loop creates implementation plan for Player agent."""

    @pytest.mark.asyncio
    async def test_preloop_creates_plan_for_player(
        self,
        mock_worktree_with_plan,
        mock_design_phase_result,
    ):
        """
        Verify pre-loop calls design phase and returns plan for Player.

        Test Flow:
        1. Create PreLoopQualityGates with mocked interface
        2. Execute pre-loop quality gates
        3. Verify DesignPhaseResult contains implementation_plan
        4. Verify Player can receive plan context
        """
        # Create mock TaskWorkInterface
        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.execute_design_phase = AsyncMock(
            return_value=mock_design_phase_result
        )

        # Create PreLoopQualityGates with mocked interface
        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree_with_plan),
            interface=mock_interface,
        )

        # Execute pre-loop quality gates
        result = await gates.execute(
            task_id="TASK-PRELOOP-001",
            options={"no_questions": True},
        )

        # Verify design phase was called
        mock_interface.execute_design_phase.assert_called_once_with(
            "TASK-PRELOOP-001",
            {"no_questions": True},
        )

        # Verify result contains implementation plan
        assert result is not None
        assert isinstance(result, PreLoopResult)
        assert result.plan is not None
        assert "overview" in result.plan
        assert result.plan["overview"] == "Implement feature X"

        # Verify plan_path is valid and file exists
        assert result.plan_path is not None
        assert Path(result.plan_path).exists()

        # Verify complexity and max_turns were extracted
        assert result.complexity == 5
        assert result.max_turns == 5  # Complexity 4-6 maps to 5 turns

        # Verify checkpoint passed
        assert result.checkpoint_passed is True

        # Verify architectural score was extracted
        assert result.architectural_score == 85

    @pytest.mark.asyncio
    async def test_preloop_plan_can_be_passed_to_player(
        self,
        mock_worktree_with_plan,
        mock_design_phase_result,
    ):
        """
        Verify the plan from pre-loop can be formatted and passed to Player.

        This test ensures the plan context is usable by the Player agent.
        """
        # Setup mock interface
        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.execute_design_phase = AsyncMock(
            return_value=mock_design_phase_result
        )

        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree_with_plan),
            interface=mock_interface,
        )

        # Execute pre-loop
        result = await gates.execute(
            task_id="TASK-PRELOOP-001",
            options={},
        )

        # Format plan context for Player (similar to how AutoBuild would do it)
        plan_context = f"""
## Implementation Plan

**Overview**: {result.plan.get('overview', 'N/A')}

**Steps**:
{chr(10).join(f"- {step}" for step in result.plan.get('steps', []))}

**Files to Create**:
{chr(10).join(f"- {file}" for file in result.plan.get('files_to_create', []))}

**Complexity**: {result.complexity}/10
**Max Turns**: {result.max_turns}
"""

        # Verify plan context is well-formed
        assert "Implementation Plan" in plan_context
        assert "Implement feature X" in plan_context
        assert "Create feature module" in plan_context
        assert "src/feature.py" in plan_context
        assert "5/10" in plan_context  # Complexity value present

        # Verify the plan context could be used in a Player prompt
        player_prompt = f"""
You are implementing TASK-PRELOOP-001.

{plan_context}

Begin implementation according to the plan.
"""
        assert len(player_prompt) > 100  # Non-trivial prompt


# ============================================================================
# TestPreLoopFailsWithoutPlan - Pre-loop Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestPreLoopFailsWithoutPlan:
    """Test that pre-loop fails appropriately when plan is not generated."""

    @pytest.mark.asyncio
    async def test_preloop_fails_without_plan_path(
        self,
        mock_worktree_with_task,
        mock_design_phase_result_no_plan,
    ):
        """
        Verify pre-loop raises QualityGateBlocked when design phase returns no plan path.
        """
        # Create mock interface that returns result with no plan
        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.execute_design_phase = AsyncMock(
            return_value=mock_design_phase_result_no_plan
        )

        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree_with_task),
            interface=mock_interface,
        )

        # Execute should raise QualityGateBlocked
        with pytest.raises(QualityGateBlocked) as exc_info:
            await gates.execute(
                task_id="TASK-PRELOOP-001",
                options={},
            )

        # Verify error message contains task ID and helpful context
        error_msg = str(exc_info.value)
        assert "TASK-PRELOOP-001" in error_msg or exc_info.value.details.get("task_id") == "TASK-PRELOOP-001"
        assert exc_info.value.gate_name == "plan_generation"

    @pytest.mark.asyncio
    async def test_preloop_fails_when_plan_file_missing(
        self,
        mock_worktree_with_task,
    ):
        """
        Verify pre-loop raises QualityGateBlocked when plan path points to non-existent file.
        """
        # Create result with plan_path that doesn't exist
        non_existent_plan_path = mock_worktree_with_task / ".claude" / "task-plans" / "TASK-MISSING-001-implementation-plan.md"

        mock_result = DesignPhaseResult(
            implementation_plan={"overview": "Test"},
            plan_path=str(non_existent_plan_path),  # Path exists in result but file doesn't
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={},
            clarifications={},
        )

        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.execute_design_phase = AsyncMock(return_value=mock_result)

        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree_with_task),
            interface=mock_interface,
        )

        # Execute should raise QualityGateBlocked
        with pytest.raises(QualityGateBlocked) as exc_info:
            await gates.execute(
                task_id="TASK-MISSING-001",
                options={},
            )

        # Verify error indicates plan validation failure
        assert exc_info.value.gate_name == "plan_validation"
        assert "not found" in str(exc_info.value).lower() or "not found" in exc_info.value.reason.lower()


# ============================================================================
# TestPlayerFailsWithoutPlan - Player Error Propagation Tests
# ============================================================================


@pytest.mark.integration
class TestPlayerFailsWithoutPlan:
    """Test that Player fails appropriately when plan is missing."""

    @pytest.mark.asyncio
    async def test_player_fails_without_plan(
        self,
        mock_worktree_with_task,
    ):
        """
        Verify Player raises appropriate error when implementation plan is missing.

        This test verifies that the Player agent (via AgentInvoker) properly
        handles the case where no implementation plan exists, which would occur
        if pre-loop was skipped or failed.
        """
        # Create invoker pointing to worktree without plan
        invoker = AgentInvoker(
            worktree_path=mock_worktree_with_task,
            development_mode="tdd",
            use_task_work_delegation=True,
        )

        # Move task to design_approved state (normally done by pre-loop)
        task_file = mock_worktree_with_task / "tasks" / "backlog" / "TASK-PRELOOP-001-test-preloop.md"
        design_approved_dir = mock_worktree_with_task / "tasks" / "design_approved"
        new_task_file = design_approved_dir / "TASK-PRELOOP-001-test-preloop.md"

        # Update status in frontmatter
        content = task_file.read_text()
        content = content.replace("status: backlog", "status: design_approved")
        task_file.write_text(content)

        # Move file
        import shutil
        shutil.move(str(task_file), str(new_task_file))

        # Create player report file that task-work would have created
        report_dir = mock_worktree_with_task / ".guardkit" / "autobuild" / "TASK-PRELOOP-001"
        report_file = report_dir / "player_turn_1.json"
        report_file.write_text(json.dumps({
            "task_id": "TASK-PRELOOP-001",
            "turn": 1,
            "files_modified": [],
            "files_created": [],
            "tests_written": [],
            "tests_run": False,
            "tests_passed": False,
            "implementation_notes": "Failed - no plan available",
            "concerns": ["No implementation plan found"],
            "requirements_addressed": [],
            "requirements_remaining": ["All requirements"],
        }), encoding='utf-8')

        # Mock subprocess to simulate task-work failure due to missing plan
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1  # Non-zero exit code
            mock_proc.communicate = AsyncMock(return_value=(
                b'',
                b'Error: Implementation plan not found for TASK-PRELOOP-001'
            ))
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-PRELOOP-001",
                turn=1,
                requirements="Implement feature X",
            )

            # Verify Player failed
            assert result.success is False
            assert "plan" in result.error.lower() or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_player_receives_plan_context_from_preloop(
        self,
        mock_worktree_with_plan,
        mock_design_phase_result,
    ):
        """
        Verify the complete flow: pre-loop creates plan, Player receives it.

        This is an end-to-end integration test verifying the handoff between
        pre-loop quality gates and Player invocation.
        """
        # Step 1: Run pre-loop to get plan
        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.execute_design_phase = AsyncMock(
            return_value=mock_design_phase_result
        )

        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree_with_plan),
            interface=mock_interface,
        )

        preloop_result = await gates.execute(
            task_id="TASK-PRELOOP-001",
            options={},
        )

        # Verify pre-loop succeeded with plan
        assert preloop_result.plan is not None
        assert preloop_result.plan_path is not None

        # Step 2: Verify plan file exists (Player would read this)
        plan_path = Path(preloop_result.plan_path)
        assert plan_path.exists()
        plan_content = plan_path.read_text()
        assert "Implementation Plan" in plan_content
        assert "TASK-PRELOOP-001" in plan_content

        # Step 3: Simulate Player receiving plan context
        # In real AutoBuild, this would be passed in requirements or read from file
        player_context = {
            "task_id": "TASK-PRELOOP-001",
            "plan": preloop_result.plan,
            "plan_path": preloop_result.plan_path,
            "complexity": preloop_result.complexity,
            "max_turns": preloop_result.max_turns,
        }

        # Verify Player context is complete
        assert player_context["plan"]["overview"] == "Implement feature X"
        assert player_context["complexity"] == 5
        assert player_context["max_turns"] == 5

        # Verify Player would have all information needed to implement
        assert len(player_context["plan"]["steps"]) == 3
        assert len(player_context["plan"]["files_to_create"]) == 2


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
