---
id: TASK-IGR-001
title: Suppress noisy loggers during guardkit init
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
completed: 2026-03-03T00:00:00Z
completed_location: tasks/completed/TASK-IGR-001/
priority: high
complexity: 2
tags: [cli, logging, developer-experience, init]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  total: 89
  passed: 89
  failed: 0
  last_run: 2026-03-03T00:00:00Z
---

# Task: Suppress noisy loggers during guardkit init

## Description

Add log level suppression for `httpx`, `httpcore`, and `graphiti_core.driver.falkordb_driver` loggers at the start of `_cmd_init()` in `guardkit/cli/init.py`. This reduces init output from ~651 lines to ~50 actionable lines.

## Context

75% of `guardkit init` output is noise:
- 438 lines of `httpx` HTTP Request INFO logs (67%)
- 52 lines of "Index already exists" messages (8%)
- ~100 lines of leaked embedding vectors from error context (15%)

The suppression pattern already exists in `guardkit/cli/graphiti.py:598-599` for the `add-context` command but was never applied to `init`.

## Implementation

Add at the start of `_cmd_init()`, before Step 2 (seeding), respecting the `--verbose` flag:

```python
# Suppress noisy third-party loggers (same pattern as graphiti.py:598-599)
if not verbose:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
```

## Acceptance Criteria

- [x] httpx INFO logs suppressed during `guardkit init` (non-verbose mode)
- [x] httpcore INFO logs suppressed during `guardkit init` (non-verbose mode)
- [x] graphiti_core.driver.falkordb_driver INFO logs suppressed (non-verbose mode)
- [x] `guardkit init --verbose` still shows all DEBUG/INFO logs
- [x] ERROR and WARNING level logs still visible in non-verbose mode
- [x] Existing tests pass

## Files to Modify

- `guardkit/cli/init.py`

## Effort Estimate

~30 minutes

## Implementation Notes

### Changes Made

**guardkit/cli/init.py:**
- Added `verbose: bool = False` parameter to `_cmd_init()`
- Added 3-line logger suppression block at the start of `_cmd_init()`, before Step 2
- Added `--verbose` / `-v` Click option to the `init` command
- Updated `init()` wrapper to pass `verbose` parameter through to `_cmd_init()`

**tests/cli/test_init.py:**
- `TestLoggerSuppression` (6 tests): httpx suppressed, httpcore suppressed, falkordb_driver suppressed, verbose preserves levels, WARNING/ERROR still visible, verbose flag in help

### Test Execution Log

89 tests passed in 2.37s. All tests passing at 100%.
