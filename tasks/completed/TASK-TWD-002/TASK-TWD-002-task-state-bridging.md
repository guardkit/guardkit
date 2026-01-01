---
id: TASK-TWD-002
title: Implement task state bridging for design_approved state
status: completed
task_type: implementation
created: 2025-12-31T14:00:00Z
completed: 2026-01-01T22:20:00Z
priority: high
tags: [autobuild, task-work-delegation, state-management, core-change]
complexity: 5
parent_feature: autobuild-task-work-delegation
wave: 1
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave1-2
source_review: TASK-REV-RW01
completed_location: tasks/completed/TASK-TWD-002/
quality_gates:
  tests_passed: true
  code_review: approved
  plan_audit: passed
files_created:
  - guardkit/tasks/state_bridge.py
  - tests/unit/test_state_bridge.py
files_modified:
  - guardkit/orchestrator/exceptions.py
  - guardkit/orchestrator/agent_invoker.py
  - guardkit/tasks/task_loader.py
  - tests/unit/test_agent_invoker.py
---

# Task: Implement task state bridging for design_approved state

## Description

Ensure that when AutoBuild delegates to `task-work --implement-only`, the task is in the correct state (`design_approved`). This requires bridging the AutoBuild orchestration state with the task-work state requirements.

## Problem

`task-work --implement-only` requires the task to be in `design_approved` state with an approved implementation plan. AutoBuild currently manages its own state independently, so we need to:

1. Create/update the implementation plan before Player invocation
2. Set the task state to `design_approved` in the task frontmatter
3. Handle cases where the task may not have gone through the design phases

## Current State Flow

```
AutoBuild:
  BACKLOG → IN_PROGRESS (AutoBuild-managed)
       ↓
  Player loops with Coach feedback
       ↓
  APPROVED/FAILED

task-work:
  BACKLOG → DESIGN_APPROVED (after --design-only)
       ↓
  IN_PROGRESS (during --implement-only)
       ↓
  IN_REVIEW → COMPLETED
```

## Target State Flow

```
AutoBuild with task-work delegation:
  BACKLOG
       ↓
  PreLoop: task-work --design-only → DESIGN_APPROVED
       ↓
  Loop: task-work --implement-only (each turn)
       ↓
  APPROVED → IN_REVIEW (ready for human merge)
```

## Implementation

### Option A: Ensure PreLoop Creates design_approved State

The `PreLoopQualityGates` already calls `task-work --design-only`, which should set the state. Verify this flow works.

```python
# guardkit/orchestrator/quality_gates/pre_loop.py

class PreLoopQualityGates:
    async def execute(self, task_id: str, ...) -> PreLoopResult:
        """Execute pre-loop quality gates."""
        # This should already set task to design_approved
        design_result = await self.task_work_interface.execute_design_phase(
            task_id=task_id,
            options={...},
        )

        # Verify state was set
        task_state = await self._read_task_state(task_id)
        if task_state != "design_approved":
            raise StateError(f"Expected design_approved, got {task_state}")

        return PreLoopResult(
            success=True,
            implementation_plan=design_result.implementation_plan,
            ...
        )
```

### Option B: State Bridge Before Each Player Invocation

If state needs to be set before each turn (in case task-work resets it):

```python
# guardkit/orchestrator/agent_invoker.py

async def _ensure_design_approved_state(self, task_id: str) -> None:
    """Ensure task is in design_approved state before invoke."""
    from guardkit.tasks.task_loader import TaskLoader

    task_file = TaskLoader.find_task_file(task_id, self.repo_root)
    frontmatter = TaskLoader.read_frontmatter(task_file)

    if frontmatter.get("status") != "design_approved":
        # Update frontmatter to set state
        TaskLoader.update_frontmatter(
            task_file,
            {"status": "design_approved"}
        )
```

## Acceptance Criteria

1. Task is in `design_approved` state before `task-work --implement-only` is called
2. Implementation plan exists in the expected location
3. State transitions are logged for debugging
4. Error handling for missing plan or incorrect state
5. Works with both fresh tasks and resumed tasks

## Files to Modify

- `guardkit/orchestrator/quality_gates/pre_loop.py` - Verify state setting
- `guardkit/orchestrator/agent_invoker.py` - Add state validation
- `guardkit/tasks/task_loader.py` - Add `update_frontmatter()` if not present

## Testing

1. Unit test: State is set correctly after PreLoop
2. Unit test: State validation before invoke_player
3. Unit test: Error handling for incorrect state
4. Integration test: Full flow from BACKLOG → DESIGN_APPROVED → implementation

## Dependencies

- Depends on: TASK-TWD-001 (invoke_player changes)
- Required by: TASK-TWD-005 (integration tests)

## Notes

- Consider adding a state machine diagram to documentation
- Log state transitions for debugging turn-by-turn flow
- Handle edge case: task manually moved out of design_approved during orchestration
