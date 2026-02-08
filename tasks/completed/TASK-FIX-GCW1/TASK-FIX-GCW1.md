---
id: TASK-FIX-GCW1
title: Fix init log to include context_loader state
status: completed
task_type: implementation
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T16:30:00Z
completed: 2026-02-08T17:00:00Z
priority: high
parent_review: TASK-REV-8BD8
tags: [observability, autobuild, logging]
complexity: 1
wave: 1
---

# Fix Init Log to Include context_loader State

## Description

The `AutoBuildOrchestrator.__init__()` log at `guardkit/orchestrator/autobuild.py:570-585` reports `enable_context=True` but does not report whether `_context_loader` was actually provided. This creates a false impression that context retrieval is active when it may be dead.

From review TASK-REV-8BD8, Finding 4.

## Changes Required

In `guardkit/orchestrator/autobuild.py`, line ~583, change:
```python
f"enable_context={self.enable_context}, "
f"verbose={self.verbose}"
```
To:
```python
f"enable_context={self.enable_context}, "
f"context_loader={'provided' if self._context_loader else 'None'}, "
f"verbose={self.verbose}"
```

## Acceptance Criteria

- [x] Init log includes `context_loader=provided` or `context_loader=None`
- [x] Existing tests still pass (no regressions)
- [x] Unit test verifying the log output contains context_loader state

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (1 line change)
