---
id: TASK-FPP-003
title: Fix path doubling in build_task_file_path
status: completed
created: 2026-02-07T20:00:00Z
updated: 2026-02-07T21:05:00Z
completed: 2026-02-07T21:05:00Z
priority: high
tags: [fix-feature-plan-paths, bug-fix]
complexity: 3
task_type: feature
implementation_mode: direct
parallel_group: 1
parent_review: TASK-REV-FP01
feature_id: FEAT-FPP
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
---

# Fix path doubling in build_task_file_path

## Description

`build_task_file_path()` in `generate_feature_yaml.py:147-186` blindly concatenates `{base_path}/{feature_slug}/{filename}`. When `base_path` already contains the `feature_slug` (e.g., `tasks/backlog/design-mode-player-coach`), the slug gets doubled:

```
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-001-...md
```

## Acceptance Criteria

- [x] `build_task_file_path()` detects when `base_path` already ends with `feature_slug` and avoids doubling
- [x] Existing unit tests pass
- [x] New unit test covers the double-slug edge case
- [x] Calling with `base_path="tasks/backlog"` + `feature_slug="my-feature"` still works correctly

## Files Modified

- `installer/core/commands/lib/generate_feature_yaml.py` - added guard in `build_task_file_path()` (lines 183-186)
- `tests/unit/test_generate_feature_yaml.py` - added 4 regression tests

## Completion Summary

- Tests: 42/42 passed (38 existing + 4 new)
- All acceptance criteria satisfied
- No regressions introduced

## Notes

Auto-generated from TASK-REV-FP01 recommendations (R2: Fix Path Doubling).
