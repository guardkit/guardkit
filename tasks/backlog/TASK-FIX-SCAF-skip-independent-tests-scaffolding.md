---
id: TASK-FIX-SCAF
title: "Fix: Skip independent test verification for scaffolding tasks"
status: backlog
created: 2026-01-23T16:00:00Z
updated: 2026-01-23T16:00:00Z
priority: high
tags: [bug-fix, feature-build, quality-gates, autobuild, scaffolding]
task_type: bug_fix
complexity: 2
parent_review: TASK-REV-FBVAL
depends_on: []
---

# Fix: Skip independent test verification for scaffolding tasks

## Problem Statement

Scaffolding tasks (task_type: scaffolding) fail independent test verification because:
1. Scaffolding tasks CREATE the test infrastructure
2. Coach runs `pytest tests/ -v` AFTER quality gates pass
3. Tests don't exist yet (or are empty stubs) during scaffolding

**Evidence from logs:**
```
INFO:coach_validator:Using quality gate profile for task type: scaffolding
INFO:coach_validator:Quality gate evaluation complete: tests=True (required=False),
  coverage=True (required=False), arch=True (required=False), audit=True (required=True),
  ALL_PASSED=True
INFO:coach_validator:Running independent tests: pytest tests/ -v
INFO:coach_validator:Independent tests failed in 0.5s
WARNING:coach_validator:Independent test verification failed for TASK-FHA-001
```

Quality gates ALL_PASSED=True, but then independent test verification fails.

## Acceptance Criteria

- [ ] When `profile.tests_required = False`, skip independent test verification
- [ ] Log message when skipping: "Independent test verification skipped for scaffolding task"
- [ ] Scaffolding tasks can complete without test infrastructure existing
- [ ] Tasks with `tests_required = True` still run independent verification
- [ ] Add test case for this behavior

## Proposed Fix

In `coach_validator.py`, before running independent tests:

```python
def validate(self, task_id: str, turn: int) -> CoachDecision:
    # ... existing code ...

    # Independent test verification
    if profile.tests_required is False:
        # Skip independent test verification for scaffolding
        test_result = IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="Independent test verification skipped (tests_required=False)",
            duration_seconds=0.0,
        )
        logger.info(f"Independent test verification skipped for {task_id} (scaffolding)")
    else:
        test_result = self.run_independent_tests()
```

## Files to Modify

- `src/guardkit/orchestrator/quality_gates/coach_validator.py`
  - Add conditional check before `run_independent_tests()`
- `tests/unit/test_coach_validator.py` (or equivalent)
  - Add test case for scaffolding profile skipping independent tests

## Success Metrics

- TASK-FHA-001 (scaffolding) completes successfully in feature-build
- Logs show "skipped" for independent tests on scaffolding tasks
- Feature tasks still run independent test verification

## Notes

This is a simple logic fix. The profile already knows `tests_required=False` for scaffolding - we just need to honor that in the independent test verification path.
