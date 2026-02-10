---
id: TASK-FIX-FP02
title: Add directory check to FeatureLoader.validate_feature() for file_path
status: completed
created: 2026-02-10T12:00:00Z
updated: 2026-02-10T14:00:00Z
completed: 2026-02-10T14:05:00Z
completed_location: tasks/completed/TASK-FIX-FP02/
priority: high
tags: [bug-fix, validation, defensive]
task_type: feature
parent_review: TASK-REV-1BE3
feature_id: FEAT-FP-FIX
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
---

# Task: Add directory check to FeatureLoader.validate_feature() for file_path

## Description

`FeatureLoader.validate_feature()` at `feature_loader.py:644-648` checks `(repo_root / task.file_path).exists()` but does not check whether the path is a file vs a directory. When `file_path: .`, `Path(".").exists()` returns `True` (it's the current directory), so validation passes as a false positive.

## Changes Required

**File**: `guardkit/orchestrator/feature_loader.py:644-648`

Add checks:
1. Reject `file_path` that resolves to a directory (`is_dir()`)
2. Reject `file_path` that doesn't end with `.md`
3. Reject `file_path` that doesn't contain "tasks" in its path components

## Acceptance Criteria

- [x] `validate_feature()` rejects `file_path: .` with clear error message
- [x] `validate_feature()` rejects `file_path` pointing to directories
- [x] `validate_feature()` rejects `file_path` not ending in `.md`
- [x] Existing valid file_path values still pass validation
- [x] Tests cover all three new rejection cases

## Evidence

- `FeatureLoader.validate_feature()`: `guardkit/orchestrator/feature_loader.py:617-666`
- FEAT-CEE8 passed validation with `file_path: .` (false positive)

## Implementation Summary

**Files modified**: 2
- `guardkit/orchestrator/feature_loader.py` — Added 3 validation checks before the `exists()` check
- `tests/unit/test_feature_loader.py` — Added 5 new tests

**Tests**: 5 new, 106 total passing, 0 regressions
