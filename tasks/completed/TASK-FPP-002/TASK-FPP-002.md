---
id: TASK-FPP-002
title: Unify slug generation into shared utility
status: completed
created: 2026-02-07T20:00:00Z
updated: 2026-02-07T21:20:00Z
completed: 2026-02-07T21:20:00Z
priority: high
tags: [fix-feature-plan-paths, refactor]
complexity: 4
task_type: refactor
implementation_mode: task-work
parallel_group: 1
parent_review: TASK-REV-FP01
feature_id: FEAT-FPP
dependencies: []
previous_state: in_review
state_transition_reason: "All quality gates passed - 72 tests passing, 100% slug_utils coverage"
completed_location: tasks/completed/TASK-FPP-002/
---

# Unify slug generation into shared utility

## Description

There are two different slug generation functions that produce different output for the same input, causing filename mismatches between YAML records and files on disk:

1. `slugify_task_name()` in `installer/core/commands/lib/generate_feature_yaml.py:119-144`
2. `_slugify()` in `installer/core/lib/implement_orchestrator.py:568-584`

Key differences:
- `_slugify()` has a 50-character limit; `slugify_task_name()` does not
- Character handling differs (regex vs manual filtering)
- Both produce different results for identical inputs

## Acceptance Criteria

- [x] Single shared slug function exists in a common location
- [x] `generate_feature_yaml.py` imports and uses the shared function
- [x] `implement_orchestrator.py` imports and uses the shared function
- [x] Both previous slug functions are replaced (not duplicated)
- [x] Shared function includes consistent length limiting behavior
- [x] Unit tests cover the shared function with edge cases
- [x] Existing tests in `test_generate_feature_yaml.py` still pass

## Implementation Summary

### Changes Made

| File | Action | Details |
|------|--------|---------|
| `installer/core/lib/slug_utils.py` | **NEW** | Shared `slugify_task_name()` with `max_length` param (default 50) |
| `installer/core/commands/lib/generate_feature_yaml.py` | **MODIFIED** | Replaced 26-line local function with 1-line import + re-export |
| `installer/core/lib/implement_orchestrator.py` | **MODIFIED** | Removed 17-line `_slugify()` method, updated 2 call sites |
| `tests/unit/test_slug_utils.py` | **NEW** | 30 tests covering edge cases, length limiting, real-world names |
| `tests/unit/test_generate_feature_yaml.py` | **MODIFIED** | Updated import comment |

### Key Decisions
- **Location:** `installer/core/lib/slug_utils.py` — accessible to both consumers
- **Regex approach:** Cleaner and more robust than manual character filtering
- **Default 50-char limit:** Matches previous `implement_orchestrator` behavior; configurable via `max_length`
- **Backward compatibility:** `slugify_task_name` re-exported from `generate_feature_yaml`

### Test Results
- 72/72 tests passing
- `slug_utils.py`: 100% line + branch coverage

## Notes

Auto-generated from TASK-REV-FP01 recommendations (R1: Unify Slug Generation).
