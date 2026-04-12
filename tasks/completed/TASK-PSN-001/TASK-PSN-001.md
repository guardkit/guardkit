---
id: TASK-PSN-001
title: Normalize completion promise field names (ac_id -> criterion_id)
task_type: bugfix
parent_review: TASK-REV-D1AE
feature_id: FEAT-PSN
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: critical
status: completed
completed: 2026-04-12T00:00:00Z
completed_location: tasks/completed/TASK-PSN-001/
tags: [autobuild, coach-validator, schema-normalization, P0]
---

# Task: Normalize completion promise field names (ac_id -> criterion_id)

## Description

The Coach validator's promise matching fails when the Player SDK emits `ac_id` instead of `criterion_id` as the acceptance criterion identifier field. This was the primary root cause of the FEAT-M2P run 1 failure (0/14 criteria verified despite all work being correct and 28 tests passing).

The fix adds key fallback logic in two locations so that `ac_id` is accepted as an alias for `criterion_id`, and `description` is accepted as an alias for `criterion_text`.

## Root Cause Reference

- Review: `specialist-agent/docs/reviews/TASK-REV-D1AE-review-report.md` (Finding 1)
- Evidence: `specialist-agent/.guardkit/worktrees/FEAT-M2P/.guardkit/autobuild/TASK-M2P-003/task_work_results.json` — Player emitted `ac_id`, `description` instead of `criterion_id`, `criterion_text`
- Schema drift caused by context attention degradation at SDK turn ceiling (102 turns, first occurrence)

## Changes Required

### 1. Update: `guardkit/orchestrator/quality_gates/coach_validator.py`

In `_match_by_promises()` at line ~2273, add `ac_id` fallback:

```python
# Before:
cid = p.get("criterion_id", "")

# After:
cid = p.get("criterion_id") or p.get("ac_id", "")
```

### 2. Update: `guardkit/orchestrator/schemas.py`

In `CompletionPromise.from_dict()` at line ~156, add field name fallbacks:

```python
# Before:
return cls(
    criterion_id=data.get("criterion_id", ""),
    criterion_text=data.get("criterion_text", ""),
    ...
)

# After:
return cls(
    criterion_id=data.get("criterion_id") or data.get("ac_id", ""),
    criterion_text=data.get("criterion_text") or data.get("description", ""),
    ...
)
```

## Acceptance Criteria

- [x] `coach_validator._match_by_promises()` matches promises with `ac_id` field when `criterion_id` is absent
- [x] `CompletionPromise.from_dict()` populates `criterion_id` from `ac_id` fallback
- [x] `CompletionPromise.from_dict()` populates `criterion_text` from `description` fallback
- [x] Existing promises with `criterion_id` continue to work unchanged (zero regressions)
- [x] Unit test: promise with `ac_id` matches correctly in `_match_by_promises()`
- [x] Unit test: `CompletionPromise.from_dict()` with `ac_id` produces correct `criterion_id`
- [x] All existing tests pass

## Implementation Notes

- Both changes are additive — they add fallback behavior without changing the primary path
- Use `or` chaining (not `if/else`) for conciseness: `data.get("criterion_id") or data.get("ac_id", "")`
- The `or` chaining also handles the case where `criterion_id` is present but empty string

## Completion Summary

- **Files modified**: `guardkit/orchestrator/quality_gates/coach_validator.py`, `guardkit/orchestrator/schemas.py`
- **Tests added**: 5 in `tests/unit/test_schemas.py`, 2 in `tests/unit/test_coach_validator.py`
- **Total tests passing**: 316/316
