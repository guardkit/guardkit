---
id: TASK-FIX-54F6
title: Add diagnostic logging for partial criteria matches in Coach validator
status: completed
task_type: implementation
created: 2026-02-26T00:00:00Z
updated: 2026-02-26T00:00:00Z
completed: 2026-02-26T00:00:00Z
completed_location: tasks/completed/TASK-FIX-54F6/
priority: medium
tags: [autobuild, coach-validator, diagnostics, observability]
complexity: 2
parent_review: TASK-REV-BA6F
feature_id: FEAT-TM-FIX
wave: 1
implementation_mode: task-work
dependencies: []
files_touched: [guardkit/orchestrator/quality_gates/coach_validator.py]
---

# Task: Add diagnostic logging for partial criteria matches in Coach validator

## Problem

The Coach validator's diagnostic dump (`coach_validator.py` around line 1530) only fires when criteria verification is **0/N** (zero matches). When criteria > 0 but < 100%, no `requirements_met` data is logged.

This creates a diagnostic blind spot for the most interesting cases — partial matches. During TASK-REV-BA6F analysis, TASK-LOG-001 Turn 2 matched 5/7 in Run 4, but the exact `requirements_met` data was unavailable because the diagnostic dump didn't trigger.

## Solution

Extend the diagnostic dump to log `requirements_met` data at DEBUG level for ALL cases, and at WARNING level when 0/N:

```python
# Always log requirements_met at DEBUG level
logger.debug(
    "Criteria verification %d/%d - requirements_met: %s",
    validation.criteria_met, validation.criteria_total,
    requirements_met
)

# WARNING level only for 0/N (existing behaviour)
if validation.criteria_met == 0 and validation.criteria_total > 0:
    logger.warning(
        "Criteria verification 0/%d - diagnostic dump:",
        validation.criteria_total
    )
    # ... existing dump ...
```

Also log the matching strategy and confidence for each criterion at DEBUG level.

## Acceptance Criteria

1. `requirements_met` data is logged at DEBUG level for every Coach validation
2. `completion_promises` data is logged at DEBUG level when present
3. Per-criterion matching strategy and confidence are logged at DEBUG level
4. Existing WARNING-level diagnostic dump for 0/N cases is preserved (no regression)
5. All existing coach_validator tests pass
6. New test verifies DEBUG-level logging for partial match case

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `validate_requirements()` diagnostic section
