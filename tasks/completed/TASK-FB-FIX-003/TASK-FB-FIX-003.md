---
id: TASK-FB-FIX-003
title: "Centralize path logic in TaskArtifactPaths"
status: completed
created: 2026-01-10T11:45:00Z
updated: 2026-01-10T14:30:00Z
completed: 2026-01-10T14:30:00Z
priority: medium
implementation_mode: task-work
wave: 2
conductor_workspace: fb-fix-wave2-1
complexity: 4
parent_task: TASK-REV-FB04
depends_on:
  - TASK-FB-FIX-001
  - TASK-FB-FIX-002
tags:
  - feature-build
  - refactoring
  - dry
---

# TASK-FB-FIX-003: Centralize Path Logic in TaskArtifactPaths

## Summary

Create a `TaskArtifactPaths` utility class to centralize all task artifact path logic, eliminating duplication across `agent_invoker.py`, `pre_loop.py`, and `task_work_interface.py`.

## Problem

Implementation plan paths are currently hardcoded in multiple locations:
- `agent_invoker.py:_ensure_design_approved_state()`
- `pre_loop.py:_extract_pre_loop_results()`
- Likely other locations

This violates DRY and makes maintenance difficult.

## New File

`guardkit/orchestrator/paths.py`

## Requirements

1. Create `TaskArtifactPaths` class with static methods for:
   - Implementation plan paths
   - Player report paths
   - Coach decision paths
   - Task state directory
2. Update all consumers to use centralized paths
3. Add path resolution helpers (find first existing file)
4. Add path creation helpers (ensure directory exists)

## Acceptance Criteria

- [x] `TaskArtifactPaths` class created with all path methods
- [x] `agent_invoker.py` updated to use `TaskArtifactPaths`
- [x] `pre_loop.py` updated to use `TaskArtifactPaths` (verified no direct paths - delegates to TaskWorkInterface)
- [x] `task_work_interface.py` updated to use `TaskArtifactPaths`
- [x] No hardcoded paths remain in orchestrator modules
- [x] Unit tests for path generation and resolution (33 tests)

## Implementation Notes

### Class Design

```python
from pathlib import Path
from typing import List, Optional

class TaskArtifactPaths:
    """Centralized path resolution for task artifacts.

    All task-related file paths should be resolved through this class
    to ensure consistency and maintainability.
    """

    # Implementation plan locations (in priority order)
    PLAN_LOCATIONS = [
        ".claude/task-plans/{task_id}-implementation-plan.md",
        ".claude/task-plans/{task_id}-implementation-plan.json",
        "docs/state/{task_id}/implementation_plan.md",
        "docs/state/{task_id}/implementation_plan.json",
    ]

    # Player report location
    PLAYER_REPORT = ".guardkit/autobuild/{task_id}/player_turn_{turn}.json"

    # Coach decision location
    COACH_DECISION = ".guardkit/autobuild/{task_id}/coach_turn_{turn}.json"

    # Task state directory
    TASK_STATE_DIR = "docs/state/{task_id}"

    @classmethod
    def implementation_plan_paths(cls, task_id: str, worktree: Path) -> List[Path]:
        """Get all possible implementation plan paths."""
        return [
            worktree / loc.format(task_id=task_id)
            for loc in cls.PLAN_LOCATIONS
        ]

    @classmethod
    def find_implementation_plan(cls, task_id: str, worktree: Path) -> Optional[Path]:
        """Find first existing implementation plan file."""
        for path in cls.implementation_plan_paths(task_id, worktree):
            if path.exists():
                return path
        return None

    @classmethod
    def player_report_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for Player report."""
        return worktree / cls.PLAYER_REPORT.format(task_id=task_id, turn=turn)

    @classmethod
    def coach_decision_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for Coach decision."""
        return worktree / cls.COACH_DECISION.format(task_id=task_id, turn=turn)

    @classmethod
    def ensure_task_dirs(cls, task_id: str, worktree: Path) -> None:
        """Ensure all task directories exist."""
        dirs = [
            worktree / ".guardkit" / "autobuild" / task_id,
            worktree / ".claude" / "task-plans",
            worktree / "docs" / "state" / task_id,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
```

### Migration Steps

1. Create `guardkit/orchestrator/paths.py`
2. Update `agent_invoker.py`:
   ```python
   from guardkit.orchestrator.paths import TaskArtifactPaths

   # Replace hardcoded paths:
   # OLD: paths = ['.claude/task-plans/...', ...]
   # NEW:
   plan_path = TaskArtifactPaths.find_implementation_plan(task_id, self.worktree_path)
   ```
3. Update `pre_loop.py` similarly
4. Update `task_work_interface.py` similarly
5. Run tests to verify no regressions

## Test Strategy

1. **Path generation tests**: Verify paths are correctly formatted
2. **Path resolution tests**: Mock file system, verify first existing file found
3. **Directory creation tests**: Verify directories created correctly

## Dependencies

- TASK-FB-FIX-001 (uses paths to create plan)
- TASK-FB-FIX-002 (uses paths to validate plan)

## Estimated Effort

2 hours
