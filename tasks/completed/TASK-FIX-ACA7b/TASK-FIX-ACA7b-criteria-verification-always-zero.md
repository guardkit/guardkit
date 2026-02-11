---
id: TASK-FIX-ACA7b
title: Investigate and fix criteria verification always showing 0%
status: completed
created: 2026-02-11T00:00:00Z
updated: 2026-02-11T12:00:00Z
completed: 2026-02-11T13:00:00Z
completed_location: tasks/completed/TASK-FIX-ACA7b/
priority: low
tags: [bugfix, quality-gates, criteria-verification, autobuild]
task_type: bugfix
complexity: 5
parent_review: TASK-REV-ACA7
previous_state: in_progress
state_transition_reason: "Task completed - all acceptance criteria met"
organized_files:
  - TASK-FIX-ACA7b-criteria-verification-always-zero.md
---

# Task: Investigate and Fix Criteria Verification Always Showing 0%

## Description

BUG-2 from TASK-REV-ACA7: Criteria verification (TASK-AQG-001) shows 0% across all tasks in FEAT-CEE8 Run 3. Every task logged `0/N verified (0%)` with all criteria in "pending" state.

### Evidence

```
TASK-DOC-001: Criteria Progress (Turn 1): 0/6 verified (0%)
TASK-DOC-002: Criteria Progress (Turn 1): 0/6 verified (0%)
TASK-DOC-003: Criteria Progress (Turn 1): 0/6 verified (0%)
TASK-DOC-003: Criteria Progress (Turn 2): 0/6 verified (0%)
TASK-DOC-004: Criteria Progress (Turn 1): 0/7 verified (0%)
TASK-DOC-005: Criteria Progress (Turn 1): 0/10 verified (0%)
```

### Root Cause (Confirmed)

TWO data pipeline gaps identified:

1. **GAP 1**: `requirements_met` key is NEVER written to `task_work_results.json` — `validate_requirements()` reads it but neither writer path (`_write_task_work_results()` nor `_write_direct_mode_results()`) ever produces it.

2. **GAP 2**: Even if `requirements_met` were populated, exact text matching would fail because Player uses free-form summaries that don't match task acceptance criteria text verbatim.

### Fix Applied

Switched from legacy text-matching (`requirements_met`) to ID-based matching via `completion_promises` from Player reports. Player already emits structured promises with `criterion_id` (AC-001, AC-002) and `status` (complete/incomplete).

### Impact

LOW — Criteria verification is informational only and does not affect approval decisions. The Coach approves based on quality gates (tests, coverage, audit), not criteria verification. However, the feature now provides accurate data in the AutoBuild flow.

## Acceptance Criteria

- [x] AC-001: Determine the exact data gap — what does `validate_requirements()` expect vs what `task_work_results.json` provides
- [x] AC-002: Fix the data pipeline so criteria verification can match Player results to acceptance criteria
- [x] AC-003: At least one criterion shows as "verified" when the Player's work satisfies it
- [x] AC-004: Criteria that are NOT met show as "pending" or "rejected" (not false positive "verified")
- [x] AC-005: No regressions in existing AQG-001 tests

## Implementation Summary

### Files Modified

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`** — Main fix
   - Refactored `validate_requirements()` into dispatcher with two matching strategies
   - Added `_load_completion_promises()` — reads from `task_work_results` or `player_turn_N.json`
   - Added `_match_by_promises()` — ID-based matching (AC-001 → promise lookup)
   - Added `_match_by_text()` — preserved legacy exact-text fallback
   - Updated call site to pass `turn` parameter

2. **`guardkit/orchestrator/agent_invoker.py`** — Writer fixes
   - `_write_direct_mode_results()` now includes `completion_promises` from Player report
   - `_write_player_report_for_direct_mode()` now includes `completion_promises`

3. **`tests/unit/test_coach_validator.py`** — 13 new tests
   - `TestCompletionPromisesMatching` class covering: all match, partial match, missing criterion, evidence preserved, promises precedence, fallback to text, player file loading, 10-criterion IDs, unknown status handling, empty criteria

### Test Results

- 13 new tests: ALL PASSING
- 17 existing AQG-001 tests: ALL PASSING (zero regressions)
- 179 total tests passing (7 pre-existing GraphitiThresholdIntegration failures deselected)

## Implementation Notes

### Investigation Steps

1. Check `task_work_results.json` structure — does it contain `requirements_met` or equivalent?
2. Check `validate_requirements()` input expectations — what key/format does it look for?
3. Check whether the stream parser (`TaskWorkStreamParser`) captures any criteria-related output
4. Determine if the fix belongs in the stream parser, the results writer, or the criteria matcher

### Affected Code

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `validate_requirements()` (~line 1040)
- `guardkit/orchestrator/agent_invoker.py` — `_write_task_work_results()` / `TaskWorkStreamParser`
- `guardkit/orchestrator/autobuild.py` — criteria progress logging
