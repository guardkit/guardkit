---
id: TASK-FBSDK-003
title: Centralize TaskArtifactPaths for SDK coordination
status: completed
created: 2026-01-18T12:15:00Z
updated: 2026-01-19T07:50:33Z
priority: high
tags: [feature-build, paths, coordination, refactoring]
complexity: 4
parent_review: TASK-REV-F6CB
feature_id: FEAT-FBSDK
implementation_mode: task-work
wave: 2
conductor_workspace: feature-build-sdk-wave2-1
depends_on:
  - TASK-FBSDK-001
  - TASK-FBSDK-002
completed: 2026-01-19T07:50:33Z
completed_location: tasks/completed/TASK-FBSDK-003/
organized_files:
  - TASK-FBSDK-003.md
  - completion-summary.md
---

# Task: Centralize TaskArtifactPaths for SDK coordination

## Description

Both `AgentInvoker` and `CoachValidator` construct paths to `task_work_results.json` independently, risking path inconsistency. The `TaskArtifactPaths` class in `guardkit/orchestrator/paths.py` should be the single source of truth for all artifact paths.

## Current State

```python
# In AgentInvoker (after TASK-FBSDK-002)
results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"

# In CoachValidator
results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

While currently identical, this duplicated path construction is error-prone.

## Implementation

### 1. Add method to TaskArtifactPaths

```python
# guardkit/orchestrator/paths.py

class TaskArtifactPaths:
    @staticmethod
    def task_work_results_path(task_id: str, worktree_path: Path) -> Path:
        """Get path for task-work quality gate results.

        Args:
            task_id: Task identifier
            worktree_path: Path to worktree root

        Returns:
            Path to task_work_results.json
        """
        return worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

### 2. Update AgentInvoker

```python
# guardkit/orchestrator/agent_invoker.py

def _get_task_work_results_path(self, task_id: str) -> Path:
    """Get path for task-work results JSON."""
    return TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
```

### 3. Update CoachValidator

```python
# guardkit/orchestrator/quality_gates/coach_validator.py

def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
    results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
    # ... rest of method unchanged
```

## Files to Modify

- `guardkit/orchestrator/paths.py` - Add `task_work_results_path()` method
- `guardkit/orchestrator/agent_invoker.py` - Use centralized path
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Use centralized path

## Acceptance Criteria

- [x] `TaskArtifactPaths.task_work_results_path()` exists and is documented
- [x] `AgentInvoker` uses centralized path method
- [x] `CoachValidator` uses centralized path method
- [x] No hardcoded paths remain in SDK coordination code
- [x] Unit tests verify path consistency

## Testing Strategy

1. **Unit Test**: Verify `task_work_results_path()` returns expected path
2. **Integration Test**: Verify AgentInvoker and CoachValidator use same path

## Related Work

- TASK-FBSDK-002 introduces `_get_task_work_results_path()` which this task consolidates
- `TaskArtifactPaths` already has `implementation_plan_paths()`, `complexity_score_path()`, etc.

## Notes

This is a P1 coordination improvement. It prevents future path drift and makes the codebase more maintainable.
