---
id: TASK-PCTD-9BEB
title: "Classify infrastructure vs code test failures in Coach feedback"
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
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
  status: pending
  coverage: null
  last_run: null
---

# Task: Classify infrastructure vs code test failures in Coach feedback

## Description

When the Coach's independent test verification fails, classify the failure as **infrastructure** (DB connection, missing package, environment) vs **code** (assertion failure, logic error). For infrastructure failures, generate actionable feedback that tells the Player specific remediation options instead of the generic "tests failed" message.

This was identified as R4 in the TASK-REV-D7B2 review. The 18-turn infinite loop in TASK-DB-003 was caused by PostgreSQL connection failures that the Player could never fix by modifying code alone — the Coach feedback never told the Player this was an infrastructure issue.

## Acceptance Criteria

- [ ] `_classify_test_failure()` method added to `CoachValidator` that scans raw test output for infrastructure patterns
- [ ] Infrastructure patterns include: `ConnectionRefusedError`, `OperationalError`, `psycopg2`, `asyncpg`, `ModuleNotFoundError`, `ImportError`, `No module named`, `Connection refused`, and database-specific errors
- [ ] `run_independent_tests()` stores raw stdout+stderr (not just summary) in `IndependentTestResult` via new optional `raw_output` field
- [ ] `IndependentTestResult` dataclass extended with `raw_output: Optional[str] = None` (backward compatible)
- [ ] Feedback for infrastructure failures includes specific remediation options (mock fixtures, SQLite test DB, pytest marks)
- [ ] Feedback for code failures unchanged (no regression)
- [ ] Unit tests for `_classify_test_failure()` with various error types
- [ ] Unit test verifying infrastructure classification produces actionable feedback text
- [ ] Unit test verifying code classification produces standard feedback text

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `run_independent_tests()`, `_classify_test_failure()` (new), `IndependentTestResult` dataclass, feedback construction at lines 545-560

## Implementation Notes

See `.claude/reviews/TASK-REV-D7B2-review-report.md` R4 section for:
- `_INFRA_FAILURE_PATTERNS` list
- `_classify_test_failure()` implementation
- Feedback template for infrastructure failures
- Regression safety analysis

**Risk**: False classification — a test could fail with `ImportError` due to a genuine code bug (e.g., circular import). Mitigated by: the feedback still tells the Player to investigate and provides options, not an automatic skip.

## Test Execution Log
[Automatically populated by /task-work]
