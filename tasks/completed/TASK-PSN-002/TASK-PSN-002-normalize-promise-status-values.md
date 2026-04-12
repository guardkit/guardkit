---
id: TASK-PSN-002
title: Normalize completion promise status values ("done" -> "complete")
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
previous_state: backlog
tags: [autobuild, coach-validator, schema-normalization, P0]
---

# Task: Normalize completion promise status values ("done" -> "complete")

## Description

The Coach validator rejects completion promises when the Player SDK emits `status: "done"` instead of `status: "complete"`. This was the secondary root cause of the FEAT-M2P run 1 failure -- even if the field name mismatch (TASK-PSN-001) were fixed, the status comparison `promise.get("status") == "complete"` would still reject `"done"`.

The fix adds a status alias map in two locations so that common synonyms (`"done"`, `"finished"`, `"completed"`) are normalized to the canonical `"complete"` value.

## Root Cause Reference

- Review: `specialist-agent/docs/reviews/TASK-REV-D1AE-review-report.md` (Finding 2)
- Evidence: 14x `WARNING:guardkit.orchestrator.schemas:Unknown CriterionStatus value 'done', defaulting to INCOMPLETE` in FEAT-M2P run 1 log
- Enum at `schemas.py:47-58` only accepts `"complete"`, `"partial"`, `"incomplete"`

## Changes Made

### 1. Updated: `guardkit/orchestrator/schemas.py`

- Added `STATUS_ALIASES` module-level constant mapping `"done"`, `"finished"`, `"completed"` to `"complete"`
- Applied normalization in `CompletionPromise.from_dict()` before enum construction
- Exported `STATUS_ALIASES` in `__all__` for single source of truth

### 2. Updated: `guardkit/orchestrator/quality_gates/coach_validator.py`

- Imported `STATUS_ALIASES` from schemas module
- Updated `_match_by_promises()` to normalize raw status before comparison

### 3. Tests added

- `tests/unit/test_schemas.py`: 4 new tests (parametrized alias mapping, canonical value regression, unknown fallback, constant validation)
- `tests/unit/test_coach_validator.py`: 3 new tests (done/finished/completed normalization in promise matching)

## Acceptance Criteria

- [x] `CompletionPromise.from_dict()` maps `"done"` to `CriterionStatus.COMPLETE` (no warning logged)
- [x] `CompletionPromise.from_dict()` maps `"finished"` to `CriterionStatus.COMPLETE`
- [x] `CompletionPromise.from_dict()` maps `"completed"` to `CriterionStatus.COMPLETE`
- [x] `coach_validator._match_by_promises()` verifies promises with `status: "done"` as complete
- [x] Existing promises with `status: "complete"` continue to work unchanged (zero regressions)
- [x] Unknown values not in alias map still fall back to INCOMPLETE with warning
- [x] Unit test: `from_dict()` with `status: "done"` produces `CriterionStatus.COMPLETE`
- [x] Unit test: promise with `status: "done"` is verified in `_match_by_promises()`
- [x] All existing tests pass (325/325)

## Implementation Notes

- `STATUS_ALIASES` defined as module-level constant in `schemas.py` and imported in `coach_validator.py`
- The alias map is case-sensitive (LLM output is lowercase)
- `"partial"` and `"incomplete"` do NOT need aliases -- they're unambiguous
