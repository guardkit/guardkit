---
id: TASK-REV-CEE8
title: Analyse FEAT-CEE8 run 2 failure - zero-test anomaly false positive blocking TASK-DOC-002
status: review_complete
created: 2026-02-10T13:00:00Z
updated: 2026-02-10T13:00:00Z
priority: high
tags: [autobuild, coach-validator, zero-test-anomaly, bug-analysis, review]
task_type: review
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: root-cause-analysis
  depth: comprehensive
  findings_count: 6
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-CEE8-review-report.md
  completed_at: 2026-02-10T14:30:00Z
---

# Task: Analyse FEAT-CEE8 run 2 failure - zero-test anomaly false positive blocking TASK-DOC-002

## Description

After fixing the file_path bug (TASK-REV-1BE3), FEAT-CEE8 run 2 progressed further — TASK-DOC-001 was approved on turn 1 (26 files created). However, TASK-DOC-002 failed with `UNRECOVERABLE_STALL` after 3 turns due to the **zero-test anomaly** check rejecting every turn despite the Player producing real passing tests.

**Key contradiction**: The Coach's independent test verification PASSES (`Independent tests passed in 0.6s`), but the zero-test anomaly check rejects because `tests_passed=0` and `coverage=null` in the task_work_results.json. The Player IS writing tests (2 test files detected), and they DO pass independently, but the results JSON doesn't reflect this.

**Hypothesis**: The `direct` implementation mode (used for complexity <= 3 tasks) writes `task_work_results.json` differently than the `task-work` delegation mode. The direct mode may not populate `tests_passed` or `coverage` fields, triggering the zero-test anomaly check added in TASK-AQG-002.

## Failure Evidence

- **Feature**: FEAT-CEE8 (Comprehensive API Documentation), run 2
- **Target repo**: `guardkit-examples/fastapi`
- **Passed**: TASK-DOC-001 (task-work mode, complexity 4) — approved turn 1
- **Failed**: TASK-DOC-002 (direct mode, complexity 3) — UNRECOVERABLE_STALL after 3 turns
- **Error**: `Zero-test anomaly: all_passed=true but tests_passed=0 and coverage=null`
- **Independent test result**: PASSED (0.6s) on all 3 turns
- **Log**: `docs/reviews/fastapi_test/api_docs_2.md`

## Key Log Lines

| Line | Event |
|------|-------|
| 24-29 | Task files successfully copied to worktree (file_path fix working) |
| 107 | TASK-DOC-001: 26 files created, 0 tests, approved (scaffolding profile) |
| 178 | TASK-DOC-002 routed to **direct** Player path (implementation_mode=direct) |
| 191 | Player: 2 files created, 4 modified, 2 tests (passing) |
| 199 | Coach using **feature** profile (not scaffolding) |
| 200 | Quality gates: tests=True, coverage=True, arch=True, audit=True, ALL_PASSED=True |
| 201 | Task-specific tests detected: 2 file(s) |
| 203 | Independent tests PASSED in 0.6s |
| 204 | **Zero-test anomaly: all_passed=true but tests_passed=0 and coverage=null** |
| 205 | Coach REJECTED: zero-test anomaly (blocking) |
| 294 | Feedback stall: identical feedback for 3 turns → UNRECOVERABLE_STALL |

## Review Scope

1. **Direct mode task_work_results.json**: What does the direct mode writer produce? Why is `tests_passed=0` when Player reports 2 tests passing?
2. **Zero-test anomaly check**: Does it correctly handle direct mode results? Is it checking the right fields?
3. **Quality gate profile**: TASK-DOC-002 uses `feature` profile (has `zero_test_blocking=True`). Should `direct` mode tasks use a different profile?
4. **task_type classification**: TASK-DOC-002 is "Configure main.py with full OpenAPI metadata" — should this be `scaffolding` (not `feature`) to avoid the zero-test anomaly check?
5. **Interaction between all_passed and tests_passed**: The quality gates show `ALL_PASSED=True` but then zero-test anomaly fires — is this a contradictory check?

## Acceptance Criteria

- [ ] AC-001: Root cause of zero-test anomaly false positive identified with evidence
- [ ] AC-002: Direct mode vs task-work mode results JSON differences documented
- [ ] AC-003: Determine if this is a CoachValidator bug or a task_type classification issue
- [ ] AC-004: Fix recommendations with specific file/line references
- [ ] AC-005: Verify the file_path fix from TASK-REV-1BE3 is working correctly (lines 24-29 confirm)

## Evidence Location

- AutoBuild log: `docs/reviews/fastapi_test/api_docs_2.md`
- Feature YAML: `guardkit-examples/fastapi/.guardkit/features/FEAT-CEE8.yaml`
- Previous review: `.claude/reviews/TASK-REV-1BE3-review-report.md`
- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Agent invoker (direct mode writer): `guardkit/orchestrator/agent_invoker.py`

## Implementation Tasks

Created from [I]mplement decision:

1. **TASK-FIX-CEE8a** (P0): Fix direct mode test count propagation in `_write_direct_mode_results`
   - File: `guardkit/orchestrator/agent_invoker.py:2236-2257`
   - Task: `tasks/backlog/TASK-FIX-CEE8a-direct-mode-test-count-propagation.md`

2. **TASK-FIX-CEE8b** (P1): Fix zero-test anomaly to respect independent test verification
   - File: `guardkit/orchestrator/quality_gates/coach_validator.py:1352-1398`
   - Task: `tasks/backlog/TASK-FIX-CEE8b-zero-test-anomaly-independent-test-override.md`

## Implementation Notes

Review completed. Use `/task-work TASK-FIX-CEE8a` then `/task-work TASK-FIX-CEE8b` to implement fixes.
