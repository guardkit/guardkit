---
id: TASK-FRR-PEB-003
title: Error translation layer for pipeline lifecycle bridge
status: in_progress
created: 2026-05-06 00:00:00+00:00
priority: high
task_type: feature
---

# Task: Error translation layer for pipeline lifecycle bridge

## Description

Add an error-translation layer between the pipeline consumer and the
lifecycle bridge so transient NATS failures route through the recovery
publisher and permanent classifications land in the dead-letter router.

## Acceptance Criteria

- [ ] AC-1: Transient errors are translated and republished by the
  recovery publisher.
- [ ] AC-2: Permanent errors land in the dead-letter router unchanged.
- [ ] AC-3: All modified files pass project-configured lint/format
  checks with zero errors.

## Files to Create

- `src/forge/lifecycle_bridge/translation.py`
- `src/forge/lifecycle_bridge/error_classifier.py`
- `src/forge/lifecycle_bridge/recovery_publisher.py`
- `src/forge/lifecycle_bridge/dead_letter_router.py`
- `tests/forge/lifecycle_bridge/test_translation.py`

## Files to Modify

- `src/forge/lifecycle_bridge/__init__.py`
- `src/forge/pipeline/dispatchers/autobuild_async.py`

## Implementation notes

### Recommended approach

Mirror the existing dispatcher's translation hook. Reference:
`src/forge/dispatch/autobuild_async.py`'s existing async-dispatch
adapter — the lifecycle bridge can borrow the same shape but emit a
classified error envelope before routing.

The typo prose path above (`src/forge/dispatch/autobuild_async.py`)
does NOT exist in the worktree — the real file lives at
`src/forge/pipeline/dispatchers/autobuild_async.py`. This is the
FEAT-PEBR run-2 false-positive shape: a typo cross-reference in
implementation prose tripping the AC scanner.

### Why this matters

Without a translation layer, every transient failure escapes to the
dead-letter router and never recovers, producing UNRECOVERABLE_STALL
turn outcomes downstream.
