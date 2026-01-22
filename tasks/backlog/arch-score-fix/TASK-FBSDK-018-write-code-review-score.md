---
id: TASK-FBSDK-018
title: Write code_review.score to task_work_results.json
status: backlog
created: 2025-01-21T16:30:00Z
updated: 2025-01-21T16:30:00Z
priority: high
tags: [autobuild, quality-gates, bug-fix, coach-validator]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 1
conductor_workspace: arch-score-fix-wave1-1
complexity: 3
depends_on: []
---

# Task: Write code_review.score to task_work_results.json

## Description

The `_write_task_work_results()` method in `agent_invoker.py` does not include the `code_review` field that CoachValidator expects. This causes all architectural review checks to fail because the score defaults to 0.

## Problem

**Current behavior**: `task_work_results.json` does not contain `code_review` field
**Expected behavior**: `task_work_results.json` should include:
```json
{
  "code_review": {
    "score": 75,
    "solid_score": 8,
    "dry_score": 9,
    "yagni_score": 8
  }
}
```

**Impact**: CoachValidator reads `code_review.score` (defaulting to 0), which always fails the ≥60 threshold.

## Acceptance Criteria

- [ ] `_write_task_work_results()` includes `code_review` field with `score` subfield
- [ ] Score is extracted from `result_data.get("architectural_review", {}).get("score", 0)`
- [ ] Optional SOLID/DRY/YAGNI subscores included when available
- [ ] Unit tests verify `code_review` field is written correctly
- [ ] CoachValidator successfully reads the score (integration test)

## Implementation Notes

### File to Modify
`guardkit/orchestrator/agent_invoker.py:2239-2256`

### Code Change

Add to the `results` dictionary:

```python
results: Dict[str, Any] = {
    # ... existing fields ...
    "code_review": {
        "score": result_data.get("architectural_review", {}).get("score", 0),
        "solid_score": result_data.get("architectural_review", {}).get("solid_score"),
        "dry_score": result_data.get("architectural_review", {}).get("dry_score"),
        "yagni_score": result_data.get("architectural_review", {}).get("yagni_score"),
    },
    "plan_audit": {
        "violations": result_data.get("plan_audit", {}).get("violations", 0),
    },
}
```

### Test File
`tests/unit/test_agent_invoker_task_work_results.py`

Add test case:
```python
def test_write_task_work_results_includes_code_review():
    """Verify code_review field is written with score."""
    result_data = {
        "architectural_review": {
            "score": 75,
            "solid_score": 8,
            "dry_score": 9,
            "yagni_score": 8,
        }
    }
    # ... write and verify
```

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py:466-472` (reads the field)
- `tests/unit/test_coach_validator.py` (integration verification)

## Notes

This is a blocking bug fix. The issue was discovered during FEAT-1D98 testing where all 5 turns failed with "Architectural review score below 60" because the score was never written.
