---
id: TASK-ACR-005
title: "Store event loop reference with thread loaders"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T12:00:00Z
completed: 2026-02-15T12:05:00Z
completed_location: tasks/completed/TASK-ACR-005/
priority: high
task_type: scaffolding
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
tags: [autobuild, asyncio, thread-safety, f3-fix]
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T12:00:00Z
  tests_passed: 14
  tests_failed: 0
organized_files:
  - TASK-ACR-005.md
  - completion-report.md
---

# Task: Store event loop reference with thread loaders

## Description

Modify `_thread_loaders` storage in `autobuild.py` to include the event loop alongside each loader. This is the foundation for fixing `_cleanup_thread_loaders()` and `_capture_turn_state()`.

## Files to Modify

- `guardkit/orchestrator/autobuild.py` — `_get_thread_local_loader()` and `_thread_loaders` declaration

## Acceptance Criteria

- [x] AC-001: `_thread_loaders` type changed from `Dict[int, Optional[AutoBuildContextLoader]]` to `Dict[int, Tuple[Optional[AutoBuildContextLoader], asyncio.AbstractEventLoop]]`
- [x] AC-002: `_get_thread_local_loader()` stores the current thread's event loop alongside the loader
- [x] AC-003: All existing reads of `_thread_loaders` updated to unpack the tuple
- [x] AC-004: Thread lock protection maintained for concurrent access
- [x] AC-005: Unit test verifies loop reference stored and retrievable per thread

## Implementation Notes

```python
# Current pattern:
_thread_loaders: Dict[int, Optional[AutoBuildContextLoader]] = {}

# New pattern:
_thread_loaders: Dict[int, Tuple[Optional[AutoBuildContextLoader], asyncio.AbstractEventLoop]] = {}

# In _get_thread_local_loader():
loop = asyncio.get_event_loop()
_thread_loaders[thread_id] = (loader, loop)
```

Update all callsites that read from `_thread_loaders` to unpack: `loader, loop = _thread_loaders[tid]`
