---
id: TASK-FIX-AC04
title: Suppress index-already-exists log noise in add-context
status: backlog
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: medium
tags: [fix, graphiti, add-context, logging]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 1
implementation_mode: direct
complexity: 1
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Suppress index-already-exists log noise

## Description

~30 lines of `INFO:graphiti_core.driver.falkordb_driver:Index already exists` appear at startup. These are harmless but create significant visual noise. Set the FalkorDB driver logger to WARNING level in the add-context command.

## Review Reference

TASK-REV-1294 recommendation R9a (P1). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-005.

## Acceptance Criteria

- [ ] AC-001: No "Index already exists" messages in add-context output
- [ ] AC-002: FalkorDB ERROR-level messages still displayed
- [ ] AC-003: Log level override scoped to add-context command, not global
- [ ] AC-004: Also suppress httpx INFO-level request logging (lines 55-98 in output)

## Implementation Notes

Add to `_cmd_add_context()` in `guardkit/cli/graphiti.py` before Graphiti connection:

```python
import logging
logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

## Test Execution Log
[Automatically populated by /task-work]
