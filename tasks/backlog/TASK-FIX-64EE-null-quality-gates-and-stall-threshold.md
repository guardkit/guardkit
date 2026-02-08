---
id: TASK-FIX-64EE
title: Fix null quality gate handling, stall threshold, and incomplete session feedback
status: in_review
created: 2026-02-08T12:00:00Z
updated: 2026-02-08T12:00:00Z
priority: high
task_type: bugfix
parent_review: TASK-REV-312E
feature: FEAT-D4CE
complexity: 4
dependencies: []
related_tasks:
  - TASK-REV-312E  # Review that identified these issues
  - TASK-FIX-CKPT  # Prior fix (different bug, must not regress)
  - TASK-AB-SD01   # Stall detection implementation (must preserve architecture)
tags: [autobuild, quality-gates, stall-detection, null-handling]
---

# Fix Null Quality Gate Handling, Stall Threshold, and Incomplete Session Feedback

## Description

TASK-REV-312E identified that when a Player's task-work session exhausts SDK turns without completing quality gates, the system writes `all_passed: null` to `task_work_results.json`. The Coach and checkpoint system treat this `null` identically to `false` (explicit failure), causing premature UNRECOVERABLE_STALL after just 2 turns.

This is NOT the same bug as TASK-FIX-CKPT. That fix addressed misreading data that was present. This fix addresses the system having no resilience when data is absent.

### Four changes needed:

1. **`verify_quality_gates()`**: Handle `all_passed: null` by falling through to `tests_failed` check
2. **`_extract_tests_passed()`**: Return `False` (not `None`) when value is null
3. **`should_rollback()` threshold**: Increase default from 2 to 3 consecutive failures
4. **Coach feedback**: Provide actionable feedback for incomplete Player sessions instead of misleading "Tests did not pass"

## Requirements

### Fix 1: Handle null in `verify_quality_gates()` (coach_validator.py:726-727)

```python
# Current (buggy):
elif "all_passed" in quality_gates:
    tests_passed = quality_gates["all_passed"]

# Fixed:
elif "all_passed" in quality_gates:
    all_passed_value = quality_gates["all_passed"]
    if all_passed_value is None:
        # Player session didn't reach quality gate evaluation
        # Fall through to tests_failed check for partial data
        if "tests_failed" in quality_gates:
            tests_failed_count = quality_gates["tests_failed"]
            tests_passed = tests_failed_count == 0
        else:
            tests_passed = False
    else:
        tests_passed = all_passed_value
```

### Fix 2: Handle null in `_extract_tests_passed()` (autobuild.py:2843-2844)

```python
# Current (buggy):
if "tests_passed" in quality_gates:
    return quality_gates.get("tests_passed", False)

# Fixed:
if "tests_passed" in quality_gates:
    value = quality_gates.get("tests_passed")
    if value is None:
        return False
    return bool(value)
```

### Fix 3: Increase stall threshold (worktree_checkpoints.py:475)

```python
# Current:
def should_rollback(self, consecutive_failures: int = 2) -> bool:

# Fixed:
def should_rollback(self, consecutive_failures: int = 3) -> bool:
```

### Fix 4: Better feedback for incomplete sessions (coach_validator.py `_build_gate_failure_feedback`)

When `all_passed` is null and `tests_passed=0, tests_failed=0`, the feedback should say:

```
"Quality gate evaluation was not completed — the Player session may have exhausted SDK turns
before reaching Phase 4.5. Focus on completing implementation within fewer SDK turns."
```

Instead of the current misleading: `"Tests did not pass during task-work execution"`

## Acceptance Criteria

- [ ] `verify_quality_gates()` handles `all_passed: null` by falling through to `tests_failed` check
- [ ] `_extract_tests_passed()` returns `False` (not `None`) when coach report has `tests_passed: null`
- [ ] `should_rollback()` default threshold is 3 consecutive failures (not 2)
- [ ] Coach feedback for incomplete sessions is actionable (mentions exhausted turns, not "tests failed")
- [ ] TASK-FIX-CKPT fixes NOT regressed: approval-before-stall ordering preserved
- [ ] TASK-AB-SD01 architecture preserved: both stall mechanisms still active
- [ ] Unit tests for null quality gate scenarios

## Constraints

- Do NOT modify the `TaskWorkStreamParser` or `_write_task_work_results()` — the writer correctly represents `null` as "not evaluated"
- Do NOT change the TASK-FIX-CKPT approval-before-stall ordering in `_loop_phase()`
- Do NOT remove either stall detection mechanism (no-passing-checkpoint or repeated-feedback)
- The 3 consecutive failures threshold should be a default, not hardcoded (allow callers to override)

## Technical Notes

- See `.claude/reviews/TASK-REV-312E-review-report.md` for full analysis
- Data flow: `TaskWorkStreamParser → _write_task_work_results() → task_work_results.json → CoachValidator.verify_quality_gates()`
- `null` means "Player never reached Phase 4.5" — semantically different from `false` ("gates evaluated, failed")
- All 120+ prior successful tasks had `all_passed: true` — DM-008 was the first `null` case
