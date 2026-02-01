---
id: TASK-AB-FIX-001
title: Pass AutoBuild context to TaskStateBridge for stub creation
status: completed
created: 2026-01-31T15:30:00Z
updated: 2026-01-31T16:30:00Z
completed: 2026-01-31T16:30:00Z
priority: high
tags: [autobuild, state-bridge, fix, race-condition]
task_type: implementation
parent_review: TASK-GR-REV-001
complexity: 3
depends_on: []
completed_location: tasks/completed/TASK-AB-FIX-001/
---

# Task: Pass AutoBuild Context to TaskStateBridge for Stub Creation

## Description

Fix the race condition where `_create_stub_implementation_plan()` fails because `autobuild_state` hasn't been written yet when the stub creation check runs.

**Root Cause (from TASK-GR-REV-001):**

The stub creation logic checks:
```python
should_create_stub = has_autobuild_config or has_autobuild_state or is_task_work_mode
```

But `autobuild_state` is written AFTER `verify_implementation_plan_exists()` fails, creating a timing issue in parallel task execution.

**Solution:**

Pass an `in_autobuild_context` flag from AgentInvoker to TaskStateBridge, enabling stub creation regardless of other flags when called from AutoBuild.

## Acceptance Criteria

- [x] Add `in_autobuild_context: bool = False` parameter to `TaskStateBridge.__init__()`
- [x] Update `_create_stub_implementation_plan()` to include `self.in_autobuild_context` in stub creation check
- [x] Update `AgentInvoker._ensure_design_approved_state()` to pass `in_autobuild_context=True`
- [x] Add unit tests for stub creation with `in_autobuild_context=True`
- [x] Verify fix with parallel task execution test

## Implementation

### File: guardkit/tasks/state_bridge.py

```python
class TaskStateBridge:
    def __init__(self, task_id: str, repo_root: Path, in_autobuild_context: bool = False):
        self.task_id = task_id
        self.repo_root = Path(repo_root)
        self.in_autobuild_context = in_autobuild_context  # NEW
        self.logger = logging.getLogger(f"{__name__}.{task_id}")

    def _create_stub_implementation_plan(self) -> Optional[Path]:
        # ... existing code ...

        should_create_stub = (
            has_autobuild_config or
            has_autobuild_state or
            is_task_work_mode or
            self.in_autobuild_context  # NEW: Always true when called from AutoBuild
        )
```

### File: guardkit/orchestrator/agent_invoker.py

```python
def _ensure_design_approved_state(self, task_id: str) -> None:
    from guardkit.tasks.state_bridge import TaskStateBridge

    logger.info(f"Ensuring task {task_id} is in design_approved state")

    try:
        bridge = TaskStateBridge(
            task_id,
            self.worktree_path,
            in_autobuild_context=True  # NEW: Signal AutoBuild context
        )
        bridge.ensure_design_approved_state()
        logger.info(f"Task {task_id} state verified: design_approved")
    # ... existing exception handling ...
```

## Test Requirements

- [x] Unit test: `test_stub_creation_with_autobuild_context_flag`
- [x] Unit test: `test_stub_creation_autobuild_context_with_verify`
- [x] Unit test: `test_stub_creation_autobuild_context_backward_compatible`

## Files to Modify

1. `guardkit/tasks/state_bridge.py` - Add `in_autobuild_context` parameter
2. `guardkit/orchestrator/agent_invoker.py` - Pass context flag
3. `tests/tasks/test_state_bridge.py` - Add new tests

## References

- [TASK-GR-REV-001 Review Report](.claude/reviews/TASK-GR-REV-001-review-report.md) - Deep Dive 1: Race Condition Timing
