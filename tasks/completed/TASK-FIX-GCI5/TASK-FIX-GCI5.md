---
id: TASK-FIX-GCI5
title: Add [Graphiti] structured logging across integration points
status: completed
task_type: implementation
created: 2026-02-08T23:00:00Z
updated: 2026-02-08T23:00:00Z
completed: 2026-02-08T23:30:00Z
priority: low
parent_review: TASK-REV-C7EB
tags: [graphiti, logging, observability]
complexity: 2
wave: 3
dependencies: [TASK-FIX-GCI1, TASK-FIX-GCI2]
---

# Add [Graphiti] Structured Logging

## CRITICAL: No Stubs Policy

**All code written for this task MUST be fully functional.** No placeholder log statements, no commented-out logging, no TODO markers. Every `[Graphiti]` log message must include real context values (category count, token usage, feature ID, etc.).

## Description

The feature-plan spec describes `[Graphiti]` prefixed log output during execution (e.g., `[Graphiti] Found feature spec`, `[Graphiti] Seeded feature spec`). No such logging exists anywhere in the codebase (zero matches for `[Graphiti]` in `guardkit/`).

Add consistent `[Graphiti]` prefixed logging to all Graphiti integration points for observability.

## Changes Required

Add logging at key integration points:

### feature_plan_context.py
```
[Graphiti] Loading context for feature planning...
[Graphiti] Context loaded: 6 categories, 2800/4000 tokens
[Graphiti] Context unavailable, continuing without enrichment
[Graphiti] Seeded feature spec for FEAT-XXX  (after GCI4)
```

### autobuild_context_loader.py
```
[Graphiti] Loading Player context (turn N)...
[Graphiti] Player context: 8 categories, 3200/4000 tokens
[Graphiti] Loading Coach context (turn N)...
[Graphiti] Coach context: 7 categories, 2900/4000 tokens
```

### graphiti_context_loader.py (after GCI1)
```
[Graphiti] Loading task context for Phase {phase}...
[Graphiti] Task context: 4 categories, 2100/4000 tokens
[Graphiti] Task context unavailable, continuing without
```

### interactive_capture.py (after GCI2)
```
[Graphiti] Knowledge capture: 3 insights stored
[Graphiti] Knowledge capture: Graphiti unavailable, insights not persisted
```

## Acceptance Criteria

- [x] All Graphiti integration points have `[Graphiti]` prefixed log messages
- [x] Log level: INFO for status messages, WARNING for degradation, DEBUG for details
- [x] Consistent format across all files
- [x] No logging noise when Graphiti is disabled (only log when integration is attempted)

## Files Modified

- `guardkit/knowledge/feature_plan_context.py`
- `guardkit/knowledge/autobuild_context_loader.py`
- `installer/core/commands/lib/graphiti_context_loader.py`
- `guardkit/knowledge/interactive_capture.py`

## Test File Created

- `tests/unit/test_graphiti_structured_logging.py` (25 tests, all passing)

## Completion Notes

- 4 source files modified, 1 test file created
- 25 new tests, 239 total passing across all affected suites, 0 regressions
- `seed_feature_spec()` already had `[Graphiti]` logging from TASK-FIX-GCI4
- Log levels: INFO for status/summary, WARNING for error degradation in graphiti_context_loader, DEBUG for per-category failure details in interactive_capture
