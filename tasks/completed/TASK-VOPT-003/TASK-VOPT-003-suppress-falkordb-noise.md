---
id: TASK-VOPT-003
title: Suppress FalkorDB index noise in logs
status: completed
task_type: implementation
priority: low
tags: [vllm, logging, falkordb, noise]
complexity: 1
parent_review: TASK-REV-CB30
feature_id: FEAT-VOPT
wave: 1
implementation_mode: direct
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T12:00:00Z
completed: 2026-03-08T12:00:00Z
completed_location: tasks/completed/TASK-VOPT-003/
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-08T12:00:00Z
---

# Task: Suppress FalkorDB Index Noise in Logs

## Problem

Run 3 logs show ~50 lines of "Index already exists: Attribute 'uuid' is already indexed" messages from `graphiti_core.driver.falkordb_driver`. This noise obscures actual operational logs.

## Implementation

Add a log filter or set the FalkorDB driver logger to WARNING level during Graphiti initialization.

### File: `guardkit/knowledge/graphiti_client.py`

In the initialization path (around `_try_lazy_init()` or where the client connects):

```python
import logging

# Suppress FalkorDB index-exists noise
logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
```

## Acceptance Criteria

- [x] AC-001: FalkorDB "Index already exists" messages suppressed from default log output
- [x] AC-002: FalkorDB WARNING and ERROR messages still visible
- [x] AC-003: Connection success message still logged

## References

- Run 3 log: lines 122-200 (repetitive index messages)
