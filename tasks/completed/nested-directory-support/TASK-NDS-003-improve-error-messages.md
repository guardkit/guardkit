---
id: TASK-NDS-003
title: Improve error messages to indicate subdirectory search
status: completed
created: 2025-12-31T12:00:00Z
updated: 2025-12-31T14:00:00Z
completed: 2025-12-31T14:00:00Z
priority: low
tags: [nested-directory-support, error-handling, task-loader]
complexity: 2
implementation_mode: direct
parallel_group: 2
conductor_workspace: nested-dir-wave2-2
parent_review: TASK-REV-C675
dependencies: [TASK-NDS-001]
---

# Improve Error Messages to Indicate Subdirectory Search

## Description

Update the `TaskNotFoundError` message in `TaskLoader.load_task()` to indicate that subdirectories were also searched. This helps users understand that the recursive search was performed and provides better debugging guidance.

## Requirements

1. Update error message format to indicate recursive search
2. Include hint about common causes
3. Maintain existing error message structure

## Acceptance Criteria

- [x] Error message indicates subdirectories were searched
- [x] Error message includes helpful hints for common issues
- [x] Error message format is consistent with existing style
- [x] No functional changes to error handling behavior

## Files to Modify

- `guardkit/tasks/task_loader.py` - `load_task()` method error handling (lines 115-123)

## Implementation Details

Implement directly with Claude Code. Changes are straightforward with clear acceptance criteria.

### Proposed Change

```python
raise TaskNotFoundError(
    f"Task {task_id} not found.\n\n"
    f"Searched locations (including subdirectories):\n"
    + "\n".join(f"  - {repo_root / 'tasks' / dir_name}/**/" for dir_name in TaskLoader.SEARCH_PATHS)
    + "\n\n"
    f"Hints:\n"
    f"  - Check task ID format (e.g., TASK-XXX-001)\n"
    f"  - Verify task file exists with .md extension\n"
    f"  - For feature tasks, check tasks/backlog/<feature-slug>/\n"
)
```

## Dependencies

- TASK-NDS-001 (error message should reflect the new recursive search behavior)

## Notes

Auto-generated from TASK-REV-C675 recommendations.
Low priority improvement for better user experience.
