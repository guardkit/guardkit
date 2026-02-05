---
id: TASK-FIX-AB03
title: Fix _recovery_count attribute name mismatch in AutoBuildOrchestrator
status: completed
created: 2026-02-05T17:00:00Z
updated: 2026-02-05T17:35:00Z
completed: 2026-02-05T17:35:00Z
completed_location: tasks/completed/TASK-FIX-AB03/
priority: medium
tags: [autobuild, bugfix]
parent_review: TASK-REV-5796
task_type: bugfix
complexity: 1
implementation_mode: direct
organized_files: [
  "TASK-FIX-AB03-fix-recovery-count-attribute-name.md"
]
---

# Task: Fix _recovery_count attribute name mismatch

## Problem Statement

`AutoBuildOrchestrator.__init__()` at `guardkit/orchestrator/autobuild.py:465` initialises:

```python
self.recovery_count: int = 0
```

But the turn state capture at line 1640 references:

```python
elif self._recovery_count > 0:
```

This causes `AttributeError: 'AutoBuildOrchestrator' object has no attribute '_recovery_count'`, silently caught by a warning handler. The turn mode is never set to `RECOVERING_STATE`.

## Acceptance Criteria

- [x] Attribute reference at line 1640 changed from `self._recovery_count` to `self.recovery_count`
- [x] No other references to `_recovery_count` exist in the codebase
- [x] Turn mode correctly set to `RECOVERING_STATE` when recovery count > 0

## Implementation Notes

Single-line fix: change `self._recovery_count` to `self.recovery_count` at autobuild.py:1640.

Search the entire codebase for any other references to `_recovery_count` to ensure consistency.

## Changes Made

- `guardkit/orchestrator/autobuild.py:1640`: Changed `self._recovery_count` to `self.recovery_count`
- Verified all other references in the file (lines 269, 465, 614, 646, 687, 1446) correctly use `self.recovery_count`
- All TurnStateCapture unit tests pass, including `test_capture_turn_state_determines_correct_turn_mode`
