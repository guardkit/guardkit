---
id: TASK-NDS-001
title: Update TaskLoader to use rglob for recursive search
status: backlog
created: 2025-12-31T12:00:00Z
updated: 2025-12-31T12:00:00Z
priority: high
tags: [nested-directory-support, autobuild, task-loader]
complexity: 3
implementation_mode: task-work
parallel_group: 1
conductor_workspace: nested-dir-wave1-1
parent_review: TASK-REV-C675
dependencies: []
---

# Update TaskLoader to use rglob for Recursive Search

## Description

Modify `TaskLoader._find_task_file()` in `guardkit/tasks/task_loader.py` to use `rglob` pattern matching instead of exact path matching. This enables discovery of tasks in feature subfolders created by `/feature-plan` and `/task-review [I]mplement`.

## Requirements

1. Replace exact path matching with `rglob` pattern
2. Support pattern `{task_id}*.md` to match both:
   - `TASK-XXX.md` (exact match)
   - `TASK-XXX-descriptive-name.md` (extended filename)
3. Maintain search order priority (backlog → in_progress → in_review → blocked)
4. Log discovered path at DEBUG level for troubleshooting

## Acceptance Criteria

- [ ] `TaskLoader.load_task("TASK-XXX")` finds tasks in `tasks/backlog/feature-slug/TASK-XXX.md`
- [ ] Extended filenames like `TASK-XXX-create-auth-service.md` are matched
- [ ] Search still prefers backlog over in_progress when task exists in both
- [ ] Backward compatible: flat structure tasks still found
- [ ] Performance acceptable (rglob should be fast for typical task directories)

## Files to Modify

- `guardkit/tasks/task_loader.py` - `_find_task_file()` method (lines 127-150)

## Implementation Details

Execute with `/task-work TASK-NDS-001` for full quality gates (architecture review, tests, code review).

### Proposed Change

```python
@staticmethod
def _find_task_file(task_id: str, repo_root: Path) -> Path:
    """
    Find task file in search paths using recursive glob.

    Searches for files matching {task_id}*.md pattern, allowing for
    both exact matches (TASK-XXX.md) and extended filenames
    (TASK-XXX-descriptive-name.md) in nested directories.
    """
    for dir_name in TaskLoader.SEARCH_PATHS:
        search_dir = repo_root / "tasks" / dir_name
        if not search_dir.exists():
            continue

        # Use rglob for recursive search with pattern matching
        for task_path in search_dir.rglob(f"{task_id}*.md"):
            logger.debug(f"Found task {task_id} at {task_path}")
            return task_path

    return None
```

## Dependencies

No dependencies.

## Notes

Auto-generated from TASK-REV-C675 recommendations.
This is the core fix that enables nested directory support.
