---
id: TASK-NDS-001
title: Update TaskLoader to use rglob for recursive search
status: completed
created: 2025-12-31T12:00:00Z
updated: 2025-12-31T13:45:00Z
completed: 2025-12-31T13:45:00Z
priority: high
tags: [nested-directory-support, autobuild, task-loader]
complexity: 3
implementation_mode: task-work
parallel_group: 1
conductor_workspace: nested-dir-wave1-1
parent_review: TASK-REV-C675
dependencies: []
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria verified"
completed_location: tasks/completed/TASK-NDS-001/
organized_files:
  - TASK-NDS-001.md
  - completion-report.md
quality_gates:
  compilation: passed
  tests: passed
  coverage: 94%
  architectural_review: 90/100
  code_review: approved_with_recommendations
  plan_audit: approved
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

- [x] `TaskLoader.load_task("TASK-XXX")` finds tasks in `tasks/backlog/feature-slug/TASK-XXX.md`
- [x] Extended filenames like `TASK-XXX-create-auth-service.md` are matched
- [x] Search still prefers backlog over in_progress when task exists in both
- [x] Backward compatible: flat structure tasks still found
- [x] Performance acceptable (rglob should be fast for typical task directories)

## Files Modified

- `guardkit/tasks/task_loader.py` - `_find_task_file()` method (lines 127-158)
- `guardkit/tasks/task_loader.py` - Error message (lines 115-122)
- `tests/unit/test_task_loader.py` - Added 6 new tests

## Implementation Summary

### Changes Made

1. **Updated `_find_task_file()` method** to use `Path.rglob()` for recursive search
2. **Updated error message** to indicate recursive search behavior
3. **Added comprehensive tests** for nested directory support

### Test Results

- 22 tests passing (100%)
- 94% line coverage
- All acceptance criteria verified

## Completion Summary

| Metric | Value |
|--------|-------|
| Duration | ~15 minutes |
| Lines Changed | ~12 |
| Tests Added | 6 |
| Coverage | 94% |
| Architectural Score | 90/100 |

## Dependencies

No dependencies.

## Notes

Auto-generated from TASK-REV-C675 recommendations.
This is the core fix that enables nested directory support.
