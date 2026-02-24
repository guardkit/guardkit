---
id: TASK-FIX-d999
title: Fix CriterionStatus enum crash on 'partial' status from synthetic report
status: completed
task_type: feature
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
completed: 2026-02-23T00:00:00Z
priority: high
tags: [bug, autobuild, schemas, synthetic-report, crash]
complexity: 3
parent_review: TASK-REV-GB10
feature_id: FEAT-GB10-fixes
---

# Task: Fix CriterionStatus enum crash on 'partial' status from synthetic report

## Description

The autobuild orchestrator crashes with `ValueError: 'partial' is not a valid CriterionStatus`
when state recovery generates a synthetic report via git/disk detection. The crash halts the
entire feature build at the Coach validation display step.

**Root cause**: `synthetic_report.py` emits `"partial"` status for disk-found files (lines 230,
252), but `CriterionStatus` enum only defines `COMPLETE = "complete"` and `INCOMPLETE =
"incomplete"`. The `CompletionPromise.from_dict()` method calls `CriterionStatus(raw_value)`
directly which raises `ValueError` for any unrecognised value.

**Crash path**:
```
autobuild.py:3083 _display_criteria_progress()
  → CompletionPromise.from_dict(p)
    → schemas.py:149 CriterionStatus(data.get("status", "incomplete"))
      → ValueError: 'partial' is not a valid CriterionStatus
```

## Acceptance Criteria

- [ ] `CriterionStatus` enum includes a `PARTIAL = "partial"` value
- [ ] `CompletionPromise.from_dict()` does not crash on any status string — unknown values
      fall back to `INCOMPLETE` with a logged warning
- [ ] `_display_criteria_progress` in `autobuild.py` correctly handles `PARTIAL` status
      in its display logic (distinct visual treatment from COMPLETE and INCOMPLETE)
- [ ] `synthetic_report.py` docstring updated to reflect the 3-state output is valid
- [ ] Existing tests pass; new test covers the `from_dict()` round-trip with `"partial"` input

## Implementation Notes

### Change 1: `guardkit/orchestrator/schemas.py`

Add `PARTIAL` to enum:
```python
class CriterionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"      # disk-found but not in git changes
    INCOMPLETE = "incomplete"
```

Add defensive sanitisation in `from_dict()`:
```python
raw_status = data.get("status", "incomplete")
try:
    status = CriterionStatus(raw_status)
except ValueError:
    logger.warning(f"Unknown CriterionStatus value '{raw_status}', defaulting to INCOMPLETE")
    status = CriterionStatus.INCOMPLETE
```

### Change 2: `guardkit/orchestrator/autobuild.py` (~line 3128)

Extend the display logic for `PARTIAL`:
```python
elif promise:
    if promise.status == CriterionStatus.COMPLETE:
        status = "PROMISED"
        icon = "~"
    elif promise.status == CriterionStatus.PARTIAL:
        status = "PARTIAL"
        icon = "?"
    else:
        status = "PENDING"
        icon = " "
```

### Change 3: `guardkit/orchestrator/synthetic_report.py`

Update the Returns docstring to note that `"partial"` is a valid output status, and that
callers must handle all three values.

## Files to Change

- `guardkit/orchestrator/schemas.py` — add `PARTIAL` to enum, defensive `from_dict()`
- `guardkit/orchestrator/autobuild.py` — handle `PARTIAL` in `_display_criteria_progress`
- `guardkit/orchestrator/synthetic_report.py` — docstring only

## Related

- Review: `TASK-REV-GB10`
- Source of bug: `docs/reviews/gb10_local_autobuild/api_feature_1.md` line 341
- Introduced when enum was "simplified from 3 states to 2" without updating synthetic report
