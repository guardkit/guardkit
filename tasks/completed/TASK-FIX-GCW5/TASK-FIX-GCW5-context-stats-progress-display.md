---
id: TASK-FIX-GCW5
title: Add context retrieval stats to progress display
status: completed
task_type: implementation
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T17:15:00Z
completed: 2026-02-08T17:15:00Z
priority: low
parent_review: TASK-REV-8BD8
tags: [autobuild, progress-display, observability]
complexity: 3
wave: 3
dependencies: [TASK-FIX-GCW3]
completed_location: tasks/completed/TASK-FIX-GCW5/
---

# Add Context Retrieval Stats to Progress Display

## Description

After context retrieval is wired up (GCW3/GCW4), operators should be able to see context retrieval status in the turn summary displayed by `ProgressDisplay`.

From review TASK-REV-8BD8, Recommendation R4.

## Changes Required

In the turn summary section of the progress display, add a line showing context retrieval status:

**When context retrieved:**
```
  Context: retrieved (6 categories, 2500/4000 tokens)
```

**When context skipped (no loader):**
```
  Context: skipped (no context_loader)
```

**When context disabled:**
```
  Context: disabled
```

**When context retrieval failed:**
```
  Context: failed (connection error)
```

This requires:
1. Passing context retrieval result from `_invoke_player()` / `_invoke_coach()` back to the caller
2. Adding context status to `TurnRecord` or a new field
3. Rendering in `ProgressDisplay.render_turn_summary()`

## Acceptance Criteria

- [x] Turn summary shows context retrieval status
- [x] Shows category count and token usage when retrieved
- [x] Shows reason when skipped/disabled/failed
- [x] Existing progress display tests still pass
- [x] New tests for context status rendering

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (return context status from invoke methods)
- `guardkit/orchestrator/progress.py` (render context status)
