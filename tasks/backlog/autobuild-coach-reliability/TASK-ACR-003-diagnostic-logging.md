---
id: TASK-ACR-003
title: "Add criteria matching diagnostic logging"
status: backlog
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T10:00:00Z
priority: medium
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
tags: [autobuild, coach, diagnostics, f2-fix]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add criteria matching diagnostic logging

## Description

When `validate_requirements()` produces 0/N results, log detailed diagnostic information at WARNING level to enable rapid diagnosis of future matching failures.

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `validate_requirements()` (~line 897)

## Acceptance Criteria

- [ ] AC-001: When criteria verification is 0/N, log acceptance criteria text (first 100 chars each)
- [ ] AC-002: Log `requirements_met` list contents (or "empty")
- [ ] AC-003: Log `completion_promises` list contents (or "empty")
- [ ] AC-004: Log which matching strategy was attempted (promises vs text)
- [ ] AC-005: Log whether synthetic report flag (`_synthetic`) was set
- [ ] AC-006: Logging is at WARNING level (not DEBUG/INFO)
- [ ] AC-007: Unit test verifies diagnostic output on 0/N scenario

## Implementation Notes

Add diagnostic block after the matching result is computed:
```python
if verified_count == 0 and total_count > 0:
    logger.warning("Criteria verification 0/%d - diagnostic dump:", total_count)
    # ... log each field
```
