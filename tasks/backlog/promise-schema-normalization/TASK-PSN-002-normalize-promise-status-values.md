---
id: TASK-PSN-002
title: Normalize completion promise status values ("done" -> "complete")
task_type: bugfix
parent_review: TASK-REV-D1AE
feature_id: FEAT-PSN
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: critical
status: backlog
tags: [autobuild, coach-validator, schema-normalization, P0]
---

# Task: Normalize completion promise status values ("done" -> "complete")

## Description

The Coach validator rejects completion promises when the Player SDK emits `status: "done"` instead of `status: "complete"`. This was the secondary root cause of the FEAT-M2P run 1 failure — even if the field name mismatch (TASK-PSN-001) were fixed, the status comparison `promise.get("status") == "complete"` would still reject `"done"`.

The fix adds a status alias map in two locations so that common synonyms (`"done"`, `"finished"`, `"completed"`) are normalized to the canonical `"complete"` value.

## Root Cause Reference

- Review: `specialist-agent/docs/reviews/TASK-REV-D1AE-review-report.md` (Finding 2)
- Evidence: 14x `WARNING:guardkit.orchestrator.schemas:Unknown CriterionStatus value 'done', defaulting to INCOMPLETE` in FEAT-M2P run 1 log
- Enum at `schemas.py:47-58` only accepts `"complete"`, `"partial"`, `"incomplete"`

## Changes Required

### 1. Update: `guardkit/orchestrator/schemas.py`

In `CompletionPromise.from_dict()` at line ~148, add alias normalization before enum construction:

```python
_STATUS_ALIASES: Dict[str, str] = {
    "done": "complete",
    "finished": "complete",
    "completed": "complete",
}

@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "CompletionPromise":
    raw_status = data.get("status", "incomplete")
    # Normalize common synonyms before enum construction
    raw_status = _STATUS_ALIASES.get(raw_status, raw_status)
    try:
        status = CriterionStatus(raw_status)
    except ValueError:
        logger.warning(
            "Unknown CriterionStatus value %r, defaulting to INCOMPLETE", raw_status
        )
        status = CriterionStatus.INCOMPLETE
    ...
```

### 2. Update: `guardkit/orchestrator/quality_gates/coach_validator.py`

In `_match_by_promises()` at line ~2284, normalize the raw status before comparison:

```python
# Before:
if promise and promise.get("status") == "complete":

# After:
raw_status = promise.get("status", "") if promise else ""
normalized_status = _STATUS_ALIASES.get(raw_status, raw_status)
if promise and normalized_status == "complete":
```

Import or define the same `_STATUS_ALIASES` map used in schemas.py. Prefer importing from schemas to maintain a single source of truth.

## Acceptance Criteria

- [ ] `CompletionPromise.from_dict()` maps `"done"` to `CriterionStatus.COMPLETE` (no warning logged)
- [ ] `CompletionPromise.from_dict()` maps `"finished"` to `CriterionStatus.COMPLETE`
- [ ] `CompletionPromise.from_dict()` maps `"completed"` to `CriterionStatus.COMPLETE`
- [ ] `coach_validator._match_by_promises()` verifies promises with `status: "done"` as complete
- [ ] Existing promises with `status: "complete"` continue to work unchanged (zero regressions)
- [ ] Unknown values not in alias map still fall back to INCOMPLETE with warning
- [ ] Unit test: `from_dict()` with `status: "done"` produces `CriterionStatus.COMPLETE`
- [ ] Unit test: promise with `status: "done"` is verified in `_match_by_promises()`
- [ ] All existing tests pass

## Implementation Notes

- Define `STATUS_ALIASES` as a module-level constant in `schemas.py` and import in `coach_validator.py`
- The alias map should be case-sensitive (LLM output is lowercase)
- `"partial"` and `"incomplete"` do NOT need aliases — they're unambiguous
