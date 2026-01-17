---
id: TASK-SDK-002
title: Add SDK pre-flight check in AutoBuild CLI
status: completed
created: 2026-01-06T15:35:00Z
updated: 2026-01-06T17:05:00Z
completed: 2026-01-06T17:05:00Z
priority: medium
tags: [sdk, cli, autobuild, validation]
complexity: 3
parent_task: TASK-REV-SDK1
implementation_mode: task-work
wave: 1
conductor_workspace: sdk-error-wave1-2
previous_state: in_progress
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/sdk-error-handling/
---

# Task: Add SDK pre-flight check in AutoBuild CLI

## Description

Currently, SDK availability is only checked when `_invoke_with_role` is called during turn execution. This is late in the workflow - the orchestrator has already created worktrees and started the process.

Add a pre-flight check at CLI startup to fail fast with a clear message before any work begins.

## Implementation Summary

**Files Modified:**
- `guardkit/cli/autobuild.py` (lines 50-94, 218, 430)
- `tests/unit/test_cli_autobuild.py` (added 9 new tests, updated 11 existing tests)

**Changes Made:**
- Added `_check_sdk_available()` - Returns True/False based on SDK importability
- Added `_require_sdk()` - Exits with code 1 and helpful message if SDK missing
- Integrated `_require_sdk()` at start of `task()` and `feature()` commands
- Updated existing tests to mock `_require_sdk` for proper test isolation

## Acceptance Criteria

- [x] `_check_sdk_available()` returns True/False correctly
- [x] `_require_sdk()` prints helpful message and exits with code 1
- [x] `guardkit autobuild task TASK-XXX` fails fast if SDK missing
- [x] `guardkit autobuild feature FEAT-XXX` fails fast if SDK missing
- [x] Exit code is 1 (not 2 or 3) for missing SDK
- [x] Existing tests still pass
- [x] New test added for pre-flight check

## Quality Gates

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ Pass |
| Tests Pass | 100% | ✅ 33/33 (100%) |
| Architectural Review | ≥60/100 | ✅ 88/100 |
| Code Review | Approved | ✅ Approved |

## Testing

```bash
# Run SDK-related tests
pytest tests/unit/test_cli_autobuild.py -v -k "sdk"
# Result: 9 passed

# Run full test suite
pytest tests/unit/test_cli_autobuild.py -v
# Result: 33 passed
```

## Notes

- Pre-flight check prevents wasted time on worktree creation
- Reference to `guardkit doctor` provides path for deeper diagnostics
- Part of SDK Error Handling feature (TASK-REV-SDK1 recommendations)
