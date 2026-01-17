---
id: TASK-SDK-001
title: Improve SDK error message with diagnostic information
status: completed
created: 2026-01-06T15:35:00Z
updated: 2026-01-06T17:00:00Z
completed: 2026-01-06T17:00:00Z
priority: high
tags: [sdk, error-handling, diagnostics, autobuild]
complexity: 3
parent_task: TASK-REV-SDK1
implementation_mode: task-work
wave: 1
conductor_workspace: sdk-error-wave1-1
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/sdk-error-handling/
---

# Task: Improve SDK error message with diagnostic information

## Description

The current error handling in `agent_invoker.py` catches all `ImportError` exceptions and reports them as "SDK not installed" - even when the SDK IS installed but fails to import for other reasons (dependency issues, path problems, etc.).

Improve the error message to include diagnostic information that helps identify the actual cause.

## Implementation Summary

**Files Modified:**
- `guardkit/orchestrator/agent_invoker.py` (lines 738-750)
- `tests/unit/test_agent_invoker.py` (added/updated 2 tests)

**Changes Made:**
- Enhanced ImportError handler to include diagnostic information
- Added sys.executable path to error message
- Added first 3 sys.path entries to error message
- Added both installation options to error message
- Preserved exception chaining with `from e`

## Acceptance Criteria

- [x] Error message includes the actual ImportError message
- [x] Error message includes Python executable path
- [x] Error message includes first 3 sys.path entries
- [x] Error message includes both installation options
- [x] Existing tests still pass
- [x] New test added for error message format

## Quality Gates

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ Pass |
| Tests Pass | 100% | ✅ 102/102 (100%) |
| Architectural Review | ≥60/100 | ✅ 88/100 |
| Code Review | Approved | ✅ Approved |

## Testing

```bash
# Run specific import_error tests
pytest tests/unit/test_agent_invoker.py -v -k "import_error"
# Result: 2 passed

# Run full test suite
pytest tests/unit/test_agent_invoker.py -v
# Result: 102 passed
```

## Notes

- This is a non-breaking change - just improves error diagnostics
- Part of SDK Error Handling feature (TASK-REV-SDK1 recommendations)
- Lazy import of `sys` module inside except block for performance
