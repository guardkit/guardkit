---
id: TASK-FIX-F053
title: Increase coach verification timeout for state recovery
status: completed
completed: 2026-03-01T00:00:00Z
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 3
implementation_mode: task-work
complexity: 2
priority: medium
tags: [coach, timeout, state-recovery, p2, bugfix]
depends_on: []
---

# Task: Increase coach verification timeout for state recovery

## Description

Make the coach verification test timeout configurable and increase it from 120s to 300s when called from state recovery contexts. The 120s timeout is too aggressive when running the full test suite under load (3 parallel tasks sharing a worktree).

## Acceptance Criteria

- [x] `_run_tests()` accepts an optional `timeout` parameter (default 120)
- [x] State recovery callers pass `timeout=300`
- [x] Normal coach validation retains the 120s timeout
- [x] All existing tests pass
- [x] Unit test: Verify timeout parameter is passed through to subprocess.run

## Implementation Notes

- File: `guardkit/orchestrator/coach_verification.py`, line 269
- Current: `subprocess.run(cmd, ..., timeout=120)` — hardcoded
- Change to: `subprocess.run(cmd, ..., timeout=timeout)` with `timeout` parameter defaulting to 120
- Also update the fallback path at line 289 (same 120s timeout)
- Callers in `state_detection.py` (line ~363) should pass `timeout=300` when called from state recovery context
