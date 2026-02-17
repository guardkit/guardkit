---
id: TASK-PCTD-9BEB
title: "Classify infrastructure vs code test failures in Coach feedback"
status: completed
previous_state: in_review
state_transition_reason: "All quality gates passed, code review approved"
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17
priority: high
tags: [autobuild, coach-validator, test-classification, feedback]
task_type: feature
complexity: 5
parent_review: TASK-REV-D7B2
feature_id: FEAT-27F2
wave: 2
implementation_mode: task-work
dependencies: [TASK-PCTD-5208]
test_results:
  status: passed
  tests_total: 282
  tests_passed: 282
  tests_failed: 0
  new_tests: 14
  regression_tests: 268
---

# Task: Classify infrastructure vs code test failures in Coach feedback

## Description

When the Coach's independent test verification fails, classify the failure as **infrastructure** (DB connection, missing package, environment) vs **code** (assertion failure, logic error). For infrastructure failures, generate actionable feedback that tells the Player specific remediation options instead of the generic "tests failed" message.

This was identified as R4 in the TASK-REV-D7B2 review. The 18-turn infinite loop in TASK-DB-003 was caused by PostgreSQL connection failures that the Player could never fix by modifying code alone — the Coach feedback never told the Player this was an infrastructure issue.

## Acceptance Criteria

- [x] `_classify_test_failure()` method added to `CoachValidator` that scans raw test output for infrastructure patterns
- [x] Infrastructure patterns include: `ConnectionRefusedError`, `OperationalError`, `psycopg2`, `asyncpg`, `ModuleNotFoundError`, `ImportError`, `No module named`, `Connection refused`, and database-specific errors
- [x] `run_independent_tests()` stores raw stdout+stderr (not just summary) in `IndependentTestResult` via new optional `raw_output` field
- [x] `IndependentTestResult` dataclass extended with `raw_output: Optional[str] = None` (backward compatible)
- [x] Feedback for infrastructure failures includes specific remediation options (mock fixtures, SQLite test DB, pytest marks)
- [x] Feedback for code failures unchanged (no regression)
- [x] Unit tests for `_classify_test_failure()` with various error types
- [x] Unit test verifying infrastructure classification produces actionable feedback text
- [x] Unit test verifying code classification produces standard feedback text

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `run_independent_tests()`, `_classify_test_failure()` (new), `IndependentTestResult` dataclass, feedback construction
- `tests/unit/test_coach_failure_classification.py` — 14 tests covering classification, backward compatibility, and feedback path integration

## Implementation Summary

### Changes to `coach_validator.py`:
1. **`IndependentTestResult`** — Added `raw_output: Optional[str] = None` field (backward compatible)
2. **`_INFRA_FAILURE_PATTERNS`** — 16-pattern class variable covering connection errors, DB drivers, and missing dependencies
3. **`_classify_test_failure()`** — Case-insensitive pattern matching, returns "infrastructure" or "code"
4. **`run_independent_tests()`** — Now captures raw stdout+stderr in `raw_output` field
5. **Feedback path** — Infrastructure failures produce actionable remediation guidance; code failures unchanged

### Test Coverage:
- 10 unit tests for `_classify_test_failure()` (all pattern categories, edge cases, case sensitivity)
- 2 backward compatibility tests for `raw_output` field
- 2 integration tests for feedback path (infrastructure vs code)
- 268 existing tests pass with zero regressions

## Test Execution Log

- 282/282 tests passed (14 new + 268 existing)
- 0 failures, 0 regressions
- Code review: APPROVED
