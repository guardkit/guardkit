---
id: TASK-FBSDK-004
title: Add implementation plan stub for feature tasks
status: completed
created: 2026-01-18T12:15:00Z
updated: 2026-01-19T09:26:06Z
priority: medium
tags: [feature-build, implementation-plan, state-bridge]
complexity: 3
parent_review: TASK-REV-F6CB
feature_id: FEAT-FBSDK
implementation_mode: task-work
wave: 2
conductor_workspace: feature-build-sdk-wave2-2
depends_on:
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
  - TASK-FBSDK-001
  - TASK-FBSDK-002
completed: 2026-01-19T09:26:06Z
completed_location: tasks/completed/TASK-FBSDK-004/
organized_files:
  - TASK-FBSDK-004.md
  - code-review-report.md
  - test-execution-report.md
  - task-work-results.json
---

# Task: Add implementation plan stub for feature tasks

## Description

Feature tasks created by `/feature-plan` don't have implementation plans because they're designed to run with `--no-pre-loop` (skipping Phases 2-2.8). However, `TaskStateBridge.verify_implementation_plan_exists()` requires a plan file, causing validation to fail.

## Current Behavior

When transitioning a feature task to `design_approved` state:
1. `TaskStateBridge.ensure_design_approved_state()` is called
2. After state transition, `verify_implementation_plan_exists()` runs
3. No plan file exists (pre-loop was skipped)
4. `PlanNotFoundError` is raised

## Proposed Solution

For feature tasks with `--no-pre-loop`, create a minimal stub plan:

```python
def _ensure_implementation_plan(self, task_id: str, worktree: Path) -> None:
    """Create stub implementation plan if missing.

    For feature tasks with pre-loop disabled, we create a minimal stub
    that satisfies the state bridge validation.

    Args:
        task_id: Task identifier
        worktree: Worktree path
    """
    plan_path = TaskArtifactPaths.preferred_plan_path(task_id, worktree)

    if plan_path.exists():
        return  # Plan already exists

    plan_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract task title for context
    task_loader = TaskLoader(worktree)
    task_data = task_loader.load(task_id)
    title = task_data.get("title", task_id)

    stub_content = f"""# Implementation Plan: {task_id}

## Task
{title}

## Plan Status
**Auto-generated stub** - Pre-loop was skipped for this feature task.

## Implementation
Follow acceptance criteria in task file.

## Notes
This plan was auto-generated because the task was created via /feature-plan
with pre-loop disabled. The detailed specifications are in the task markdown.
"""
    plan_path.write_text(stub_content)
    logger.info(f"Created stub implementation plan at {plan_path}")
```

## Alternative: Relax Validation

Instead of creating a stub, modify `verify_implementation_plan_exists()` to skip validation when a marker indicates feature task:

```python
def verify_implementation_plan_exists(self) -> Optional[Path]:
    """Verify implementation plan exists or is intentionally skipped."""
    # Check for feature task marker
    if self._is_feature_task_with_no_preloop():
        logger.info(f"Skipping plan verification for feature task {self.task_id}")
        return None

    # ... existing validation ...
```

## Recommended Approach

Create stub plan (first option) because:
- Maintains consistent state machine behavior
- Plan file can be populated if pre-loop is run later
- No special case logic needed in validation

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` - Add `_ensure_implementation_plan()`
- `guardkit/tasks/state_bridge.py` - Call stub creation before validation

## Acceptance Criteria

- [ ] Feature tasks with no pre-loop have stub implementation plan
- [ ] TaskStateBridge validation passes for feature tasks
- [ ] Existing tasks with real plans are unaffected
- [ ] Stub plan clearly indicates it's auto-generated
- [ ] Unit tests verify stub creation

## Testing Strategy

1. **Unit Test**: Mock task loader, verify stub content
2. **Integration Test**: Run feature-build, verify state transition completes

## Notes

This is a P2 robustness improvement. It prevents edge case failures when pre-loop is disabled.
