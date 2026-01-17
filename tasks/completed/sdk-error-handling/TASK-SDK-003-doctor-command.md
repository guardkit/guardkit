---
id: TASK-SDK-003
title: Add guardkit doctor diagnostic command
status: completed
created: 2026-01-06T15:35:00Z
updated: 2026-01-06T17:35:00Z
completed: 2026-01-06T17:35:00Z
priority: medium
tags: [cli, diagnostics, developer-experience]
complexity: 5
parent_task: TASK-REV-SDK1
implementation_mode: task-work
wave: 2
conductor_workspace: sdk-error-wave2-1
depends_on:
  - TASK-SDK-001
  - TASK-SDK-002
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/sdk-error-handling/
---

# Task: Add guardkit doctor diagnostic command

## Description

Create a `guardkit doctor` command that validates the GuardKit environment and reports on all dependencies, similar to `flutter doctor` or `brew doctor`.

## Implementation Summary

**Files Created:**
- `guardkit/cli/doctor.py` (480 lines) - Comprehensive diagnostic module
- `tests/unit/test_doctor.py` (742 lines) - Unit test suite

**Files Modified:**
- `guardkit/cli/main.py` - Updated doctor command to delegate to new module

**Architecture:**
- Strategy Pattern for extensible checks
- CheckStatus enum (PASS, FAIL, WARNING)
- CheckResult dataclass with icon/color properties
- Abstract Check base class with subclasses:
  - PythonVersionCheck
  - PackageCheck
  - CLIToolCheck
  - FileExistsCheck
- DoctorRunner orchestration
- DoctorReport formatting with Rich output

## Acceptance Criteria

- [x] `guardkit doctor` runs without error
- [x] Reports Python version and path
- [x] Reports guardkit-py version
- [x] Reports claude-agent-sdk version (or "Not installed")
- [x] Reports Claude CLI version and path (or "Not found")
- [x] Reports git version
- [x] Checks for CLAUDE.md in current directory
- [x] Checks for tasks/ directory
- [x] Exit code 0 if all required checks pass
- [x] Exit code 1 if any required check fails
- [x] Rich formatting with colors and checkmarks

## Quality Gates

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ Pass |
| Tests Pass | 100% | ✅ 52/52 (100%) |
| Line Coverage | ≥80% | ✅ 99.49% |
| Branch Coverage | ≥75% | ✅ 100% |
| Architectural Review | ≥60/100 | ✅ 82/100 |
| Code Review | Approved | ✅ Approved |

## Testing

```bash
# Run doctor tests
pytest tests/unit/test_doctor.py -v
# Result: 52 passed

# Run existing CLI tests (no regressions)
pytest tests/unit/test_cli_autobuild.py -v
# Result: 33 passed
```

## Notes

- Inspired by `flutter doctor` and `brew doctor`
- SDK is optional - doctor should warn but not fail if missing
- Claude CLI is checked via `shutil.which()` and `subprocess` with 5s timeout
- Part of SDK Error Handling feature (TASK-REV-SDK1 recommendations)
