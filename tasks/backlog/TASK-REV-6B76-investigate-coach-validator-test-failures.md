---
id: TASK-REV-6B76
title: Investigate pre-existing coach_validator test failures
status: backlog
created: 2026-02-15T00:00:00Z
updated: 2026-02-15T00:00:00Z
priority: medium
tags: [test-failures, coach-validator, graphiti, investigation]
task_type: review
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
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

- [ ] All 15 failing tests are identified and catalogued
- [ ] Root cause confirmed (missing `get_quality_gate_config`, `get_graphiti_thresholds`, `validate_with_graphiti_thresholds`)
- [ ] Relationship to Graphiti feature roadmap assessed
- [ ] Recommendation provided: skip, implement, or remove
- [ ] No regressions in passing tests

## Key Files

- `tests/unit/test_coach_validator.py` (lines ~2026-3650)
- `guardkit/orchestrator/quality_gates/coach_validator.py`

## Implementation Notes

These failures are pre-existing and do not block current development. They appear to be tests written ahead of implementation for planned Graphiti quality gate features.
