---
id: TASK-AQG-001
title: Add structured acceptance criteria verification to Coach validator
status: completed
created: 2026-02-10T20:30:00Z
updated: 2026-02-10T21:00:00Z
completed: 2026-02-10T21:00:00Z
priority: high
task_type: feature
tags: [autobuild, coach, quality-gates, acceptance-criteria]
parent_review: TASK-REV-7972
feature_id: FEAT-AQG
complexity: 6
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add Structured Acceptance Criteria Verification to Coach Validator

## Description

The Coach validator currently evaluates quality gates (compilation, tests, coverage) but does NOT verify acceptance criteria. Every AutoBuild task shows `Criteria: 0 verified, 0 rejected, N pending`. This has been confirmed across FEAT-SC-001 (TASK-REV-6F11), FEAT-6EDD (TASK-REV-422A), and FEAT-FP-002 (TASK-REV-7972).

The Coach's `validate_requirements()` method (coach_validator.py:955-1005) does string comparison between task acceptance criteria and Player's `requirements_met` array, but the orchestrator expects structured output in `criteria_verification` and `acceptance_criteria_verification.criteria_results` fields that the Coach never populates.

## Root Cause

1. `CoachValidationResult.to_dict()` (coach_validator.py:213-249) does NOT include `criteria_verification` or `acceptance_criteria_verification` fields
2. `_display_criteria_progress()` (autobuild.py:2518-2568) looks for `criteria_verification` in Coach report — always empty
3. `_count_criteria_passed()` (autobuild.py:2237-2261) looks for `acceptance_criteria_verification.criteria_results` — always empty

## Implementation Plan

### Changes Required

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`**:
   - Extend `validate_requirements()` to produce structured per-criterion verification results
   - Each criterion should have: `criterion_text`, `result` (verified/rejected/pending), `evidence` (summary of what was checked)
   - Add `criteria_verification` list to `CoachValidationResult`
   - Update `to_dict()` to serialize the new field

2. **Data model alignment**:
   - Ensure the serialized format matches what `_display_criteria_progress()` expects: `[{"criterion": "...", "result": "verified|rejected|pending", "evidence": "..."}]`
   - Ensure `_count_criteria_passed()` can read the new format via `acceptance_criteria_verification.criteria_results`

### What NOT to change

- Do NOT modify `_display_criteria_progress()` or `_count_criteria_passed()` — they already expect the right format
- Do NOT change the approval/rejection logic — criteria verification is informational, not blocking (for now)
- Do NOT add LLM-based verification — use string matching + structured output

## Acceptance Criteria

- [x] AC1: `CoachValidationResult` includes `criteria_verification` list with per-criterion results
- [x] AC2: `to_dict()` serializes criteria verification data in format expected by orchestrator
- [x] AC3: `_display_criteria_progress()` shows non-zero verified counts when Player reports matching requirements
- [x] AC4: `_count_criteria_passed()` returns non-zero when criteria are verified
- [x] AC5: Existing quality gate evaluation is unchanged (no regressions)
- [x] AC6: Unit tests cover: criteria match, partial match, no match, empty criteria list

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (main changes)
- `guardkit/orchestrator/autobuild.py` (consumers — verify compatibility, don't modify)
- `tests/unit/test_coach_validator.py` (new tests)
