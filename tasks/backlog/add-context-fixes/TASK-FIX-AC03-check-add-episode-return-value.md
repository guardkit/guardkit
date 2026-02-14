---
id: TASK-FIX-AC03
title: Fix false-positive success reporting — check add_episode return value
status: backlog
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: high
tags: [fix, graphiti, add-context, data-integrity]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 1
implementation_mode: task-work
complexity: 2
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix false-positive success reporting in add-context CLI

## Description

The CLI marks files as `✓` and increments `episodes_added` even when `add_episode()` returns `None` (silent failure). The code at `graphiti.py:674-681` only catches exceptions, but `_create_episode()` swallows exceptions internally and returns `None`. The CLI never sees the failure.

## Review Reference

TASK-REV-1294 "Success Reporting Bug" finding. See `.claude/reviews/TASK-REV-1294-review-report.md` AC-001.

## Acceptance Criteria

- [ ] AC-001: `episodes_added` only incremented when `add_episode()` returns a non-None value (episode UUID)
- [ ] AC-002: Failed episodes logged as errors with the file path
- [ ] AC-003: Summary accurately reports successful vs failed episode counts
- [ ] AC-004: `✓` marker only shown for files where ALL episodes succeeded
- [ ] AC-005: Files with partial success show a warning marker (e.g., `⚠`) with count of failed episodes
- [ ] AC-006: Tests cover None return, exception, and success paths

## Implementation Notes

Key change in `guardkit/cli/graphiti.py` at lines 674-681:

```python
# Before (bug):
await client.add_episode(...)
episodes_added += 1

# After (fix):
result = await client.add_episode(...)
if result is not None:
    episodes_added += 1
else:
    errors.append(f"{file_path_str}: Episode creation returned None (possible silent failure)")
```

Also update the file-level success marker to check if all episodes for the file succeeded.

## Test Execution Log
[Automatically populated by /task-work]
