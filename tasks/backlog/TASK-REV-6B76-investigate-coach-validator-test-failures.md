---
id: TASK-REV-6B76
title: Investigate pre-existing coach_validator test failures
status: completed
created: 2026-02-15T00:00:00Z
updated: 2026-02-15T00:00:00Z
priority: medium
tags: [test-failures, coach-validator, graphiti, investigation]
task_type: review
complexity: 0
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T00:00:00Z
review_results:
  mode: investigation
  depth: standard
  findings_count: 15
  recommendations_count: 1
  decision: remove
  report_path: .claude/reviews/TASK-REV-6B76-review-report.md
---

# Task: Investigate Pre-existing Coach Validator Test Failures

## Description

15 test failures exist in `tests/unit/test_coach_validator.py` that are pre-existing and unrelated to current work. These tests exercise functions that do not yet exist:

- `get_quality_gate_config`
- `get_graphiti_thresholds`
- `validate_with_graphiti_thresholds`

All 15 failures are in the `TestGraphitiThresholdIntegration` test class and relate to unimplemented Graphiti threshold features.

## Investigation Scope

1. Confirm the 15 failing tests and catalogue them
2. Determine whether the tested functions are planned for a specific feature/task
3. Assess options: skip/mark as xfail, implement the missing functions, or remove the tests
4. Recommend a resolution path

## Acceptance Criteria

- [x] All 15 failing tests are identified and catalogued
- [x] Root cause confirmed (missing `get_quality_gate_config`, `get_graphiti_thresholds`, `validate_with_graphiti_thresholds`)
- [x] Relationship to Graphiti feature roadmap assessed
- [x] Recommendation provided: skip, implement, or remove
- [x] No regressions in passing tests

## Key Files

- `tests/unit/test_coach_validator.py` (lines ~2026-3650)
- `guardkit/orchestrator/quality_gates/coach_validator.py`

## Implementation Notes

These failures are pre-existing and do not block current development. They appear to be tests written ahead of implementation for planned Graphiti quality gate features.

## Resolution

**Decision: Remove all 15 orphaned tests**

### Root Cause

The tests were NOT written ahead of implementation - they were written alongside implementations in TASK-GE-005 and TASK-SC-009. However, TASK-REV-GROI subsequently proved the tested code was dead/disconnected, and TASK-GWR-001 removed the source code but did not clean up the corresponding tests.

### Tests Removed (3 classes, 15 tests)

1. **TestGraphitiThresholdIntegration** (7 tests) - tested `get_graphiti_thresholds`, `get_quality_gate_config`, `GRAPHITI_AVAILABLE`
2. **TestQualityGateConfigIntegration** (3 tests) - tested `get_quality_gate_config` via `get_graphiti_thresholds`
3. **TestCoachContextIntegration** (5 tests) - tested `validate_with_graphiti_thresholds`

### Verification

- 184 tests passing, 0 failures after cleanup
- No regressions in any existing tests
- Review report: `.claude/reviews/TASK-REV-6B76-review-report.md`
