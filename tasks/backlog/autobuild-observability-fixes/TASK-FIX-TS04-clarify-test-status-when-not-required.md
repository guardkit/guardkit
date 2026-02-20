---
id: TASK-FIX-TS04
title: Clarify test status display when tests_required=False
status: backlog
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
priority: medium
tags: [autobuild, ui-clarity, test-status, coach-validator]
task_type: feature
complexity: 3
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 1
implementation_mode: task-work
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Clarify test status display when tests_required=False

## Description

When a task type has `tests_required=False` (documentation, scaffolding, testing), the Player summary can show `0 tests (failing)` while the Coach still approves the task. This is logically correct but cosmetically confusing — it appears as if the Coach rubber-stamped a failing task.

The fix is to display `0 tests (not required)` or similar when the quality gate profile doesn't require tests.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 9)
- Evidence: TASK-RK01-011 shows `0 tests (failing)` yet Coach approved

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — Player summary generation (`_generate_summary`)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Coach approval log message

## Implementation Plan

### Step 1: Update Player summary in `_generate_summary`

The `_generate_summary` method generates the status line (e.g., `"24 files created, 66 modified, 1 tests (passing)"`). When tests_passed is 0 or None and tests are not required, change the display:

```python
def _generate_summary(self, result_data, tests_required=True):
    # ...existing logic...
    tests_passed = result_data.get("tests_passed", 0)
    tests_failed = result_data.get("tests_failed", 0)

    if not tests_required and tests_passed == 0 and tests_failed == 0:
        parts.append("tests not required")
    elif tests_passed is not None or tests_failed is not None:
        total = (tests_passed or 0) + (tests_failed or 0)
        status = "passing" if (tests_failed or 0) == 0 else "failing"
        parts.append(f"{total} tests ({status})")
```

### Step 2: Thread `tests_required` through to `_generate_summary`

The `_write_task_work_results` method calls `_generate_summary` but doesn't currently know the task type. Either:
- Pass `documentation_level` context (already available) and infer, or
- Add a `tests_required` parameter

### Step 3: Enhance Coach approval log message

In `coach_validator.py`, when logging the approval, include the reason when tests are skipped:

```python
if not profile.tests_required:
    logger.info(
        f"Independent test verification skipped for {task_id} "
        f"(tests not required for {task_type_str} tasks)"
    )
```

Currently shows: `tests_required=False` — change to include the task type name for clarity.

## Acceptance Criteria

- [ ] Player summary shows `tests not required` instead of `0 tests (failing)` when `tests_required=False`
- [ ] Coach approval log includes task type name when tests are skipped
- [ ] Tasks with `tests_required=True` and 0 tests still show `0 tests (failing)` correctly
- [ ] Tasks with passing tests still show `N tests (passing)` correctly
- [ ] Unit test covers all display variants
