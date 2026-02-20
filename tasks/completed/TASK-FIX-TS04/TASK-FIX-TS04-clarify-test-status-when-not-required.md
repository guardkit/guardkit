---
id: TASK-FIX-TS04
title: Clarify test status display when tests_required=False
status: completed
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
completed: 2026-02-20T00:00:00Z
priority: medium
tags: [autobuild, ui-clarity, test-status, coach-validator]
task_type: feature
complexity: 3
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 1
implementation_mode: task-work
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-20
completed_location: tasks/completed/TASK-FIX-TS04/
---

# Task: Clarify test status display when tests_required=False

## Description

When a task type has `tests_required=False` (documentation, scaffolding, testing), the Player summary can show `0 tests (failing)` while the Coach still approves the task. This is logically correct but cosmetically confusing — it appears as if the Coach rubber-stamped a failing task.

The fix is to display `0 tests (not required)` or similar when the quality gate profile doesn't require tests.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 9)
- Evidence: TASK-RK01-011 shows `0 tests (failing)` yet Coach approved

## Files Modified

- `guardkit/orchestrator/autobuild.py` — `_build_player_summary` + `_resolve_tests_required` + import
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Coach approval log message + `test_output_summary`
- `tests/unit/test_autobuild_orchestrator.py` — 17 new tests

## Acceptance Criteria

- [x] Player summary shows `tests not required` instead of `0 tests (failing)` when `tests_required=False`
- [x] Coach approval log includes task type name when tests are skipped
- [x] Tasks with `tests_required=True` and 0 tests still show `0 tests (failing)` correctly
- [x] Tasks with passing tests still show `N tests (passing)` correctly
- [x] Unit test covers all display variants

## Implementation Notes

The bug was in `_build_player_summary` in `autobuild.py` (not `_generate_summary` in `agent_invoker.py` as originally listed). Added:
- `_resolve_tests_required(task_type)` helper that handles task type aliases
- `tests_required` parameter to `_build_player_summary`
- Updated both callers in `_execute_turn` (normal + state recovery paths)

732 tests passed, 0 failures.
