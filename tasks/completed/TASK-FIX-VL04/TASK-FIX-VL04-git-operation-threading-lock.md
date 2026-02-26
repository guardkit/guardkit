---
id: TASK-FIX-VL04
title: Add threading lock for git operations in parallel wave execution
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T15:00:00Z
completed: 2026-02-26T15:00:00Z
priority: medium
tags: [autobuild, vllm, bug-fix, parallel, race-condition, git]
complexity: 3
task_type: bug-fix
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-FIX-VL04/
---

# Task: Add threading lock for git operations in parallel wave execution

## Description

When Wave 2+ tasks run in parallel sharing a single worktree, `_detect_git_changes()` runs `git diff HEAD` and `git ls-files --others` without any synchronisation. This causes non-deterministic file attribution: files created by task B may be detected by task A's git operation.

**Root Cause**: No `threading.Lock()` or equivalent for git operations. All parallel tasks see the cumulative git state.

## Requirements

Add a class-level `threading.RLock()` to protect git operations in `_detect_git_changes()` and any other git-touching methods in AgentInvoker.

## Acceptance Criteria

- [x] `_detect_git_changes()` acquires a lock before running git commands
- [x] Lock is released after git commands complete (use context manager)
- [x] Lock is shared across all AgentInvoker instances (class-level or passed via constructor)
- [x] No deadlock risk (use RLock not Lock)
- [x] Parallel wave execution still works (tasks run concurrently, just git operations are serialised)
- [x] Unit test verifies lock prevents interleaved git operations

## Files Modified

- `guardkit/orchestrator/agent_invoker.py` - Added class-level `_git_lock = threading.RLock()` and wrapped `_detect_git_changes()` with lock context manager
- `tests/unit/test_agent_invoker.py` - Added `TestGitOperationThreadingLock` (3 tests)

## Completion Summary

- All 6 acceptance criteria met
- 3 new unit tests pass (412 total, 0 failures)
- No deadlock risk: RLock used (reentrant)
- Lock is class-level, shared across all AgentInvoker instances
- Git operations serialised; non-git work remains concurrent
