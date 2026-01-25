---
id: TASK-FIX-COVNULL
title: "Fix coverage=None handling in coach_validator quality gates"
status: completed
created: 2026-01-24T00:35:00Z
updated: 2026-01-23T17:20:00Z
completed: 2026-01-23T17:20:00Z
priority: high
tags: [fix, coach-validator, quality-gates, coverage, autobuild]
task_type: feature
complexity: 2
parent_review: TASK-REV-FB25
feature_id: FEAT-FB-FIXES
implementation_mode: task-work
wave: 1
estimated_hours: 1-2
actual_hours: 0.25
completed_location: tasks/completed/TASK-FIX-COVNULL/
---

# Fix coverage=None handling in coach_validator quality gates

## Problem

When task-work writes `coverage_met: null` (Python `None`) to `task_work_results.json`, the coach_validator treats this as a gate failure even though coverage data simply wasn't collected.

### Evidence from logs:
```
Quality gate evaluation complete: tests=True (required=True), coverage=None (required=True), arch=True (required=False), audit=True (required=True), ALL_PASSED=False
Quality gates failed for TASK-FHA-003: QualityGateStatus(tests_passed=True, coverage_met=None, ...)
```

### Current behavior:
- `coverage_met=None` in JSON → gate fails
- Should treat `None` as "not measured" → pass (same as coverage not required)

## Root Cause

In `guardkit/orchestrator/quality_gates/coach_validator.py` around line 588:

```python
coverage_met = quality_gates.get("coverage_met", True)  # Default True if not present
```

The problem: This defaults to `True` only if the key is **missing**, but when the key **exists** with value `None`, it returns `None`.

## Solution

### Option A: Fix in coach_validator.py (Recommended)

Change the coverage extraction to handle `None` explicitly:

```python
# OLD:
coverage_met = quality_gates.get("coverage_met", True)

# NEW:
coverage_met_value = quality_gates.get("coverage_met")
# Treat None as "not measured" = pass (same as coverage not required)
coverage_met = coverage_met_value if coverage_met_value is not None else True
```

### Option B: Fix in agent_invoker.py

Ensure `coverage_met` is always boolean when writing results:

```python
results = {
    "quality_gates": {
        "coverage_met": bool(coverage_met) if coverage_met is not None else True,
        ...
    }
}
```

## Acceptance Criteria

- [x] When `coverage_met=null` in task_work_results.json, quality gate passes (treated as "not measured")
- [x] When `coverage_met=true`, quality gate passes
- [x] When `coverage_met=false`, quality gate fails (coverage below threshold)
- [x] Existing behavior preserved for valid boolean values
- [x] Unit test added for None handling

## Implementation Notes

### File to modify:
`guardkit/orchestrator/quality_gates/coach_validator.py`

### Location:
`verify_quality_gates()` method, around line 582-589

### Test file:
`tests/unit/test_coach_validator.py`

## Testing

```bash
# Run existing tests
pytest tests/unit/test_coach_validator.py -v

# Add test case for None coverage
# test_coverage_none_treated_as_pass()
```

## Related

- Parent review: TASK-REV-FB25
- Related fix: TASK-FIX-INDTEST (independent test verification)
- Previous fixes: TASK-FIX-ARIMPL (arch review skip - WORKING)
