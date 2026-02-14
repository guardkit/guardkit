---
id: TASK-FIX-STUB-A
title: Wire acceptance_criteria through _execute_turn() to Coach
status: completed
created: 2026-02-13T12:00:00Z
completed: 2026-02-14T00:00:00Z
priority: critical
tags: [autobuild, quality-gates, bug-fix, acceptance-criteria, wiring]
parent_review: TASK-REV-STUB
feature_id: FEAT-STUB-QG
implementation_mode: task-work
wave: 1
complexity: 3
task_type: bug-fix
previous_state: backlog
state_transition_reason: "Completed via /task-work + /task-complete"
---

# Task: Wire acceptance_criteria through _execute_turn() to Coach

## Description

**CRITICAL BUG**: `_execute_turn()` in `guardkit/orchestrator/autobuild.py` does not accept or pass the `acceptance_criteria` parameter to `_invoke_coach_safely()`. This means the Coach has **never verified acceptance criteria for any task** across all AutoBuild runs. Every `coach_turn_*.json` shows `criteria_total: 0` (vacuous truth).

The `acceptance_criteria` list is correctly loaded by `TaskLoader.load_task()` and passed through `orchestrate()` → `_loop_phase()`, but `_loop_phase()` only passes it to `_capture_turn_state()` and `_display_criteria_progress()` — never to `_execute_turn()`.

This is a 3-line fix that restores the entire acceptance criteria verification pipeline, including the previously-inert TASK-FIX-ACA7b completion_promises matching logic.

## Root Cause

```
orchestrate() → _loop_phase(acceptance_criteria=[15 items])
    ├→ _capture_turn_state(acceptance_criteria)      ← HAS criteria
    ├→ _display_criteria_progress(acceptance_criteria) ← HAS criteria
    └→ _execute_turn(turn, task_id, ...)             ← MISSING criteria
        └→ _invoke_coach_safely(..., acceptance_criteria=None)
            └→ CoachValidator.validate(task={"acceptance_criteria": []})
                └→ validate_requirements() → criteria_total: 0
```

## Changes Made

1. `guardkit/orchestrator/autobuild.py:1635` — Added `acceptance_criteria: Optional[List[str]] = None` parameter to `_execute_turn()` signature
2. `guardkit/orchestrator/autobuild.py:1509` — Added `acceptance_criteria=acceptance_criteria` in `_loop_phase()`'s call to `_execute_turn()`
3. `guardkit/orchestrator/autobuild.py:1820` — Added `acceptance_criteria=acceptance_criteria` in `_execute_turn()`'s call to `_invoke_coach_safely()`

## Acceptance Criteria

- [x] AC-001: `_execute_turn()` accepts `acceptance_criteria: Optional[List[str]] = None` parameter
- [x] AC-002: `_loop_phase()` passes `acceptance_criteria` to `_execute_turn()` at the call site
- [x] AC-003: `_execute_turn()` passes `acceptance_criteria` to `_invoke_coach_safely()` at the call site
- [x] AC-004: Unit test: When `acceptance_criteria=["AC-001: Feature works"]` is passed to `_execute_turn()`, the Coach receives it in `task["acceptance_criteria"]`
- [x] AC-005: Unit test: When `acceptance_criteria=None` (default), Coach receives `None` (backward compatible)
- [x] AC-006: Unit test: Integration test — `_loop_phase()` with acceptance_criteria flows through to `_execute_turn()` with non-empty list
- [x] AC-007: All existing orchestrator tests pass without modification (backward compatible due to default=None)
- [ ] AC-008: After fix, running a task with acceptance criteria produces `criteria_total > 0` in coach_turn JSON (requires live AutoBuild run)

## Tests

3 new tests in `TestAcceptanceCriteriaWiring` class (`tests/unit/test_autobuild_orchestrator.py`):
- `test_execute_turn_passes_acceptance_criteria_to_coach` (AC-004)
- `test_execute_turn_default_acceptance_criteria_is_none` (AC-005)
- `test_loop_phase_passes_acceptance_criteria_to_execute_turn` (AC-006)

All 7 existing `_execute_turn` tests pass without modification (AC-007).

## References

- Review report: `.claude/reviews/TASK-REV-STUB-review-report.md` (RC-1)
- Related fix: TASK-FIX-ACA7b (completion_promises matching — now activated)
- Related fix: TASK-AQG-001 (structured criteria verification — now activated)
