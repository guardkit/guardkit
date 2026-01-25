---
id: TASK-FB-FIX-004
title: "Add integration test for pre-loop + Player flow"
status: completed
created: 2026-01-10T11:45:00Z
updated: 2026-01-11T10:00:00Z
completed: 2026-01-11T10:00:00Z
priority: medium
implementation_mode: task-work
wave: 2
conductor_workspace: fb-fix-wave2-2
complexity: 4
parent_task: TASK-REV-FB04
depends_on:
  - TASK-FB-FIX-001
  - TASK-FB-FIX-002
tags:
  - feature-build
  - testing
  - integration-test
---

# TASK-FB-FIX-004: Add Integration Test for Pre-Loop + Player Flow

## Summary

Create an integration test that verifies the complete pre-loop to Player handoff, ensuring the implementation plan is created and readable by the Player agent.

## Problem

The bug was undetected because there was no integration test verifying that:
1. Pre-loop creates an implementation plan file
2. Player can read and use that plan

## New File

`tests/integration/test_preloop_player_flow.py`

## Requirements

1. Test that pre-loop creates implementation plan file
2. Test that Player can read the plan
3. Test error case when plan is missing
4. Use test fixtures (not real SDK) for speed
5. Test both markdown and JSON plan formats

## Acceptance Criteria

- [x] Integration test `test_preloop_creates_plan_for_player()` passes
- [x] Integration test `test_player_fails_without_plan()` passes
- [x] Test uses appropriate fixtures/mocks for CI speed
- [x] Test runs in under 30 seconds (actual: 1.26s)
- [x] Test added to CI pipeline (pytest.ini includes `integration` marker)

## Implementation Notes

### Test Structure

```python
# tests/integration/test_preloop_player_flow.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.exceptions import QualityGateBlocked


@pytest.fixture
def test_worktree(tmp_path: Path) -> Path:
    """Create a test worktree structure."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create tasks directory
    tasks = worktree / "tasks" / "backlog"
    tasks.mkdir(parents=True)

    # Create test task
    task_file = tasks / "TASK-TEST-001-test-task.md"
    task_file.write_text("""---
id: TASK-TEST-001
title: Test Task
status: backlog
---
# Test Task

## Description
A test task for integration testing.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
""")

    return worktree


@pytest.fixture
def mock_sdk_design_result():
    """Mock SDK result for design phase."""
    return {
        "plan_path": ".claude/task-plans/TASK-TEST-001-implementation-plan.md",
        "complexity": {"score": 5},
        "architectural_review": {"score": 80},
        "checkpoint_result": "approved",
    }


class TestPreLoopPlayerFlow:
    """Integration tests for pre-loop to Player handoff."""

    @pytest.mark.asyncio
    async def test_preloop_creates_plan_for_player(
        self,
        test_worktree: Path,
        mock_sdk_design_result: dict,
    ):
        """Verify pre-loop creates plan that Player can read."""
        # Given: A task in backlog
        task_id = "TASK-TEST-001"

        # Mock SDK to return design result
        with patch(
            "guardkit.orchestrator.quality_gates.task_work_interface.TaskWorkInterface.execute_design_phase"
        ) as mock_design:
            # Simulate SDK creating the plan file
            plan_path = test_worktree / ".claude" / "task-plans"
            plan_path.mkdir(parents=True)
            plan_file = plan_path / f"{task_id}-implementation-plan.md"
            plan_file.write_text("""# Implementation Plan

## Overview
Test implementation plan.

## Steps
1. Step one
2. Step two
""")

            mock_design.return_value = mock_sdk_design_result

            # When: Pre-loop executes
            gates = PreLoopQualityGates(str(test_worktree))
            result = gates.execute(task_id, {"no_questions": True})

            # Then: Plan file exists
            assert result.plan_path is not None
            assert Path(result.plan_path).exists()

            # And: Player can read it
            invoker = AgentInvoker(test_worktree)
            plan_content = invoker._load_implementation_plan(task_id)
            assert plan_content is not None
            assert "Implementation Plan" in plan_content

    @pytest.mark.asyncio
    async def test_preloop_fails_without_plan(
        self,
        test_worktree: Path,
    ):
        """Verify pre-loop raises error if plan not created."""
        task_id = "TASK-TEST-001"

        with patch(
            "guardkit.orchestrator.quality_gates.task_work_interface.TaskWorkInterface.execute_design_phase"
        ) as mock_design:
            # Simulate SDK returning success but NOT creating plan file
            mock_design.return_value = {
                "plan_path": None,  # No plan created
                "complexity": {"score": 5},
                "architectural_review": {"score": 80},
                "checkpoint_result": "approved",
            }

            # When/Then: Pre-loop raises QualityGateBlocked
            gates = PreLoopQualityGates(str(test_worktree))
            with pytest.raises(QualityGateBlocked) as exc_info:
                gates.execute(task_id, {"no_questions": True})

            assert "Implementation plan not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_player_fails_without_plan(
        self,
        test_worktree: Path,
    ):
        """Verify Player raises clear error if plan missing."""
        task_id = "TASK-TEST-001"

        # Given: No plan file exists
        invoker = AgentInvoker(test_worktree)

        # When/Then: Player raises PlanNotFoundError
        from guardkit.orchestrator.exceptions import PlanNotFoundError

        with pytest.raises(PlanNotFoundError) as exc_info:
            invoker._ensure_design_approved_state(task_id)

        assert task_id in str(exc_info.value)
        assert "task-work --design-only" in str(exc_info.value)
```

### CI Configuration

Add to `pytest.ini` or CI config:

```ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
```

### Running Tests

```bash
# Run all tests
pytest tests/integration/test_preloop_player_flow.py -v

# Run only integration tests
pytest -m integration -v

# Run with coverage
pytest tests/integration/ --cov=guardkit.orchestrator -v
```

## Test Strategy

1. **Happy path**: Pre-loop creates plan, Player reads it
2. **Error path**: Pre-loop fails without plan
3. **Error path**: Player fails without plan
4. **Format variants**: Test both .md and .json plan formats

## Dependencies

- TASK-FB-FIX-001 (the fix being tested)
- TASK-FB-FIX-002 (the validation being tested)
- pytest, pytest-asyncio

## Estimated Effort

2 hours
