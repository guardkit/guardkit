---
id: TASK-FIX-6141
title: Fix extract_acceptance_criteria() search path divergence
status: completed
task_type: implementation
priority: critical
tags: [autobuild, vllm, bugfix, agent-invoker, p0]
complexity: 2
parent_review: TASK-REV-5610
feature_id: FEAT-FF93
wave: 1
implementation_mode: task-work
dependencies: []
completed: 2026-02-27T00:00:00Z
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-27T00:00:00Z
  tests_passed: 9
  tests_failed: 0
---

# Task: Fix extract_acceptance_criteria() Search Path Divergence

## Description

Fix the `extract_acceptance_criteria()` method in `agent_invoker.py` to align with `_find_task_file()`, which already correctly searches all task directories using glob patterns.

Currently, `extract_acceptance_criteria()` (line 4108-4133) has two bugs:
1. **Missing directory**: Only searches `in_progress/`, `backlog/`, `in_review/` — missing `design_approved/`, `completed/`, `blocked/`
2. **Wrong filename pattern**: Uses exact match `f"{task_id}.md"` but actual files use the format `TASK-DB-005-create-initial-migration.md`

The existing `_find_task_file()` method (line 2226-2252) already does this correctly using `rglob(f"{task_id}*.md")` across all 6 directories.

## Root Cause

This is the root cause of TASK-DB-005 Turn 1 scoring 0/6 in the vLLM autobuild run 2. When the task file can't be found, no acceptance criteria are injected into the Player prompt. Without AC context, Qwen3 produces generic `requirements_met` that can't match specific AC text even with semantic matching active (50% Jaccard threshold).

## Implementation

Refactor `extract_acceptance_criteria()` to use `_find_task_file()` internally:

```python
# BEFORE (agent_invoker.py:4108-4129):
task_file = None
possible_paths = [
    self.worktree_path / "tasks" / "in_progress" / f"{task_id}.md",
    self.worktree_path / "tasks" / "backlog" / f"{task_id}.md",
    self.worktree_path / "tasks" / "in_review" / f"{task_id}.md",
]
for status_dir in ["in_progress", "backlog", "in_review"]:
    # ... subdirectory search with exact filename ...
for path in possible_paths:
    if path.exists():
        task_file = path
        break

# AFTER:
task_file = self._find_task_file(task_id)
```

This is a single-line replacement that eliminates the divergence entirely.

## Acceptance Criteria

- [x] `extract_acceptance_criteria()` uses `_find_task_file()` for file location
- [x] Tasks in `design_approved/` directory are found correctly
- [x] Tasks with slug-suffixed filenames (e.g., `TASK-DB-005-create-initial-migration.md`) are found
- [x] Existing tests pass (no regression)
- [x] New unit test confirms `extract_acceptance_criteria()` finds files in `design_approved/`

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py:4108-4129` | Replace file search with `_find_task_file()` call |

## Risk Assessment

**Risk**: Very Low
- `_find_task_file()` has been working correctly throughout all autobuild runs
- The change removes code (simpler), doesn't add complexity
- No architectural changes, no new dependencies
