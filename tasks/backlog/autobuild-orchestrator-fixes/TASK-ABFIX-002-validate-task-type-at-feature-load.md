---
id: TASK-ABFIX-002
title: Validate task_type during feature loading (fail-fast)
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: backlog
priority: critical
tags: [autobuild, orchestrator, validation, fail-fast]
---

# Task: Validate task_type during feature loading (fail-fast)

## Description

Add task_type validation to `feature_loader.validate_feature()` so that invalid task_type values are caught at feature load time (Phase 1) rather than at Coach validation time (after Player has already consumed a full turn).

Currently, `feature_loader.py:643-726` validates task file existence, dependency graphs, and wave structure, but does NOT validate that each task's `task_type` field is a valid `TaskType` enum value or alias.

## Review Reference

From TASK-REV-A17A Finding 2, Recommendation 2b:
> Validate task_type in `feature_loader.validate_feature()`: Read each task's frontmatter and check `task_type` against `TaskType` enum + aliases. Fail fast with actionable error.

## Requirements

1. In `feature_loader.validate_feature()` (around line 643-726), add a validation step that:
   - Reads each task file's frontmatter
   - Extracts the `task_type` field
   - Validates it against `TaskType` enum values and `TASK_TYPE_ALIASES` keys
   - Reports an actionable error listing the invalid value and valid options
2. The validation should fail the feature setup with a clear error message, not silently skip
3. Import the alias table from the canonical location (coach_validator or task_types module)
4. Add tests for both valid and invalid task_type values during feature validation

## Files to Modify

- `guardkit/orchestrator/feature_loader.py` — add task_type validation to `validate_feature()`
- `guardkit/models/task_types.py` — optionally expose a `is_valid_task_type()` helper
- `tests/` — add tests for feature validation with invalid task_type

## Acceptance Criteria

- [ ] Feature validation fails fast with actionable error for invalid task_type
- [ ] Error message lists the invalid value and all valid options (enum + aliases)
- [ ] Valid task_type values (including aliases like `enhancement`) pass validation
- [ ] All existing tests pass
- [ ] New tests cover the validation path
