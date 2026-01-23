---
id: TASK-FIX-FBMSG
title: "Fix feedback message to include test_output field"
status: completed
created: 2026-01-23T11:30:00Z
updated: 2026-01-23T12:20:00Z
completed: 2026-01-23T12:20:00Z
priority: medium
tags: [fix, autobuild, feedback, ux]
task_type: feature
complexity: 2
parent_review: TASK-REV-FB26
feature_id: FEAT-FB-FIXES
implementation_mode: task-work
wave: 1
depends_on: []
estimated_hours: 0.5
actual_hours: 0.3
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, tests passing"
completed_location: tasks/completed/TASK-FIX-FBMSG/
organized_files:
  - TASK-FIX-FBMSG.md
---

# Fix feedback message to include test_output field

## Problem

When independent tests fail, the feedback message shows:
```
⚠ Feedback: - Independent test verification failed:
```

The message is truncated because `_extract_feedback()` expects issues to have a `suggestion` field, but the test failure issue has a `test_output` field instead:

```python
# What Coach creates (coach_validator.py:438-443):
issues=[{
    "severity": "must_fix",
    "category": "test_verification",
    "description": "Independent test verification failed",
    "test_output": test_result.test_output_summary,  # IGNORED by _extract_feedback
}],
```

```python
# What _extract_feedback reads (autobuild.py:1751-1754):
desc = issue.get("description", "")
suggestion = issue.get("suggestion", "")  # Empty for test failures
feedback_lines.append(f"- {desc}: {suggestion}")  # Results in "failed:"
```

## Solution

Update `_extract_feedback()` to also read the `test_output` field when `suggestion` is empty.

### Implemented Fix

```python
for issue in issues[:3]:  # Limit to top 3 issues
    desc = issue.get("description", "")
    suggestion = issue.get("suggestion", "")
    test_output = issue.get("test_output", "")

    if suggestion:
        feedback_lines.append(f"- {desc}: {suggestion}")
    elif test_output:
        # Use test output as the actionable detail
        feedback_lines.append(f"- {desc}:\n  {test_output}")
    else:
        feedback_lines.append(f"- {desc}")
```

## Expected Result

Before:
```
⚠ Feedback: - Independent test verification failed:
```

After:
```
⚠ Feedback: - Independent test verification failed:
  FAILED tests/test_config.py::test_settings - ImportError: cannot import name 'Settings'
```

## Acceptance Criteria

- [x] `_extract_feedback()` includes `test_output` field when `suggestion` is empty
- [x] Test output is indented for readability
- [x] Existing behavior preserved when `suggestion` is present
- [x] Unit test added for new behavior

## Files Modified

1. `guardkit/orchestrator/autobuild.py`
   - `_extract_feedback()` method (lines 1751-1762)

2. `tests/unit/test_autobuild_orchestrator.py`
   - Added `TestExtractFeedback` class with 6 comprehensive tests

## Testing

```bash
pytest tests/unit/test_autobuild_orchestrator.py -v -k "extract_feedback"
```

**Test Results:**
- 6 tests added and passing
- All acceptance criteria met

## Completion Summary

| Metric | Value |
|--------|-------|
| Complexity | 2/10 (Simple) |
| Estimated Hours | 0.5 |
| Actual Hours | 0.3 |
| Tests Added | 6 |
| Tests Passing | 6/6 (100%) |
| Files Modified | 2 |

## Related

- Parent review: TASK-REV-FB26
- Related fix: TASK-FIX-INDFB (fixes root cause, this improves UX)
