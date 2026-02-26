---
id: TASK-FIX-VL02
title: Fix 5 - Use TaskLoader for acceptance criteria extraction
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T14:45:00Z
completed: 2026-02-26T14:45:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-FIX-VL02/
priority: high
tags: [autobuild, vllm, bug-fix, synthetic-promises, two-parser-divergence]
complexity: 2
task_type: bug-fix
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Fix 5 - Use TaskLoader for acceptance criteria extraction

## Description

Fix 5 (synthetic file-existence promises) in `agent_invoker.py:1881-1909` uses `_load_task_metadata()` which only reads YAML frontmatter. Feature task acceptance criteria are stored in the markdown body (`## Acceptance Criteria` section), not the frontmatter. This means Fix 5 always gets `acceptance_criteria=[]` and never generates synthetic promises.

**Root Cause**: Two-parser divergence. `TaskLoader._extract_acceptance_criteria()` correctly parses both frontmatter AND markdown body. `AgentInvoker._load_task_metadata()` only reads frontmatter.

## Requirements

Replace the `_load_task_metadata()` call in Fix 5 with `TaskLoader.load_task()` or equivalent to correctly extract acceptance criteria from the markdown body.

## Acceptance Criteria

- Fix 5 uses `TaskLoader` (or equivalent body-parsing logic) to extract acceptance criteria
- Acceptance criteria from `## Acceptance Criteria` markdown section are correctly extracted
- Synthetic file-existence promises are generated when AC references match files_created/files_modified
- Existing Fix 5 behaviour unchanged for tasks with AC in YAML frontmatter
- `_load_task_metadata()` method can optionally be deprecated or updated
- Unit test covers markdown-body AC extraction in Fix 5 context

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (lines 1884-1896, Fix 5 block)

## Implementation Notes

```python
# Current (lines 1886-1895):
task_file = self._find_task_file(task_id)
if task_file:
    task_meta = self._load_task_metadata(task_file)  # YAML frontmatter only!
    acceptance_criteria = task_meta.get("acceptance_criteria", [])

# Proposed:
try:
    from guardkit.tasks.task_loader import TaskLoader
    task_data = TaskLoader.load_task(task_id, repo_root=self.worktree_path)
    acceptance_criteria = task_data.get("acceptance_criteria", [])
except Exception as e:
    logger.debug(f"Fix 5: TaskLoader failed for {task_id}: {e}")
    # Fallback to existing _load_task_metadata
    task_file = self._find_task_file(task_id)
    if task_file:
        task_meta = self._load_task_metadata(task_file)
        acceptance_criteria = task_meta.get("acceptance_criteria", [])
    else:
        acceptance_criteria = []
```

**Important**: Use `self.worktree_path` as `repo_root` for `TaskLoader.load_task()` since the task files are in the worktree, not the original repo root.
