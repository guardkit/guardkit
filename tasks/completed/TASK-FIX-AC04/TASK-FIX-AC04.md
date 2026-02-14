---
id: TASK-FIX-AC04
title: Suppress index-already-exists log noise in add-context
status: completed
created: 2026-02-13T00:00:00Z
updated: 2026-02-14T00:00:00Z
completed: 2026-02-14T00:00:00Z
completed_location: tasks/completed/TASK-FIX-AC04/
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
  status: passed
  coverage: null
  last_run: 2026-02-14T00:00:00Z
organized_files:
  - TASK-FIX-AC04.md
---

# Task: Suppress index-already-exists log noise

## Description

~30 lines of `INFO:graphiti_core.driver.falkordb_driver:Index already exists` appear at startup. These are harmless but create significant visual noise. Set the FalkorDB driver logger to WARNING level in the add-context command.

## Review Reference

TASK-REV-1294 recommendation R9a (P1). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-005.

## Acceptance Criteria

- [x] AC-001: No "Index already exists" messages in add-context output
- [x] AC-002: FalkorDB ERROR-level messages still displayed
- [x] AC-003: Log level override scoped to add-context command, not global
- [x] AC-004: Also suppress httpx INFO-level request logging (lines 55-98 in output)

## Implementation Notes

Add to `_cmd_add_context()` in `guardkit/cli/graphiti.py` before Graphiti connection:

```python
import logging
logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

## Test Execution Log

- **54 tests passing** (39 existing + 10 AC03 + 5 new in `TestLogNoiseSuppression`)
- **0 regressions**
- Tests cover all 4 acceptance criteria:
  - `test_falkordb_driver_logger_set_to_warning` → AC-001
  - `test_falkordb_error_messages_still_displayed` → AC-002
  - `test_log_suppression_scoped_to_add_context` → AC-003
  - `test_httpx_logger_set_to_warning` → AC-004
  - `test_info_messages_blocked_warning_messages_pass` → verifies INFO blocked, WARNING/ERROR pass
