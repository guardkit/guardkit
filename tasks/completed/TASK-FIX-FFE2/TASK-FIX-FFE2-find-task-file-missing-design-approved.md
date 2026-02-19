---
id: TASK-FIX-FFE2
title: Add design_approved to _find_task_file search dirs
status: completed
created: 2026-02-18T22:45:00Z
updated: 2026-02-19T00:00:00Z
completed: 2026-02-19T00:00:00Z
priority: high
tags: [autobuild, agent-invoker, fix, completion-promises]
complexity: 1
parent_review: TASK-REV-9745
related_tasks:
  - TASK-REV-9745   # Review that identified this bug
  - TASK-FIX-AE7E   # Cross-turn memory fix (safe, not regressed)
---

# Fix: Add `design_approved` to `_find_task_file` Search Dirs

## Problem

`_find_task_file()` in `guardkit/orchestrator/agent_invoker.py` (line ~1833) searches these directories for a task file by ID:

```python
task_dirs = [
    self.worktree_path / "tasks" / "backlog",
    self.worktree_path / "tasks" / "in_progress",
    self.worktree_path / "tasks" / "in_review",
    self.worktree_path / "tasks" / "completed",
    self.worktree_path / "tasks" / "blocked",
]
```

In the autobuild workflow, tasks are moved to `tasks/design_approved/` before the Player agent is invoked (via `state_bridge.py`). The `design_approved` directory is absent from the search list, so `_find_task_file()` always returns `None` for any in-flight autobuild task.

This silently breaks Fix 5 (`_generate_file_existence_promises`), which depends on `_find_task_file()` returning the task file in order to read acceptance criteria and synthesise `completion_promises`. Fix 5 has therefore never worked correctly for any autobuild task — it produces no promises and logs nothing to indicate the failure.

This was identified as the primary structural gap in TASK-REV-9745: when the Player agent non-deterministically omits `completion_promises`, Fix 5 is supposed to be the safety net but is silently broken.

## Fix

Add `design_approved` to the `task_dirs` list in `_find_task_file()`:

```python
task_dirs = [
    self.worktree_path / "tasks" / "backlog",
    self.worktree_path / "tasks" / "design_approved",  # ADD THIS
    self.worktree_path / "tasks" / "in_progress",
    self.worktree_path / "tasks" / "in_review",
    self.worktree_path / "tasks" / "completed",
    self.worktree_path / "tasks" / "blocked",
]
```

## Acceptance Criteria

- [ ] `_find_task_file()` includes `design_approved` in its search list
- [ ] A task file located in `tasks/design_approved/` is found and returned correctly
- [ ] Fix 5 (`_generate_file_existence_promises`) generates promises when task is in `design_approved` and agent omits `completion_promises`
- [ ] Existing behaviour for tasks in other states is unchanged
- [ ] Test added: `test__find_task_file__finds_task_in_design_approved`

## Implementation Notes

- **File**: `guardkit/orchestrator/agent_invoker.py` — `_find_task_file()` method
- **Change**: Single line addition to `task_dirs` list
- **Regression risk**: Zero — adding a directory to search cannot break existing behaviour
- **Also check**: Whether `_find_task_file()` is used elsewhere and whether those call sites also benefit from this change

## Test Plan

Add a unit test to the existing `agent_invoker` test suite:

```python
def test__find_task_file__finds_task_in_design_approved(tmp_path):
    """_find_task_file should find task files in design_approved directory."""
    task_dir = tmp_path / "tasks" / "design_approved"
    task_dir.mkdir(parents=True)
    task_file = task_dir / "TASK-DB-001-setup-database-infrastructure.md"
    task_file.write_text("---\nid: TASK-DB-001\n---\n")

    invoker = AgentInvoker(worktree_path=tmp_path, ...)
    result = invoker._find_task_file("TASK-DB-001")

    assert result == task_file
```
