---
id: TASK-FIX-AC06
title: Add retry with exponential backoff for transient FalkorDB errors
status: backlog
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: medium
tags: [fix, graphiti, falkordb, resilience]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: [TASK-FIX-AC02]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add retry with exponential backoff for transient FalkorDB errors

## Description

`_create_episode()` in `graphiti_client.py` currently catches all exceptions and returns `None`. For transient errors like "Max pending queries exceeded", it should retry with exponential backoff before giving up.

## Review Reference

TASK-REV-1294 recommendation R4 (P1). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-002.

## Acceptance Criteria

- [ ] AC-001: `_create_episode()` retries up to 3 times for "Max pending queries" errors
- [ ] AC-002: Backoff schedule: 1s, 2s, 4s (exponential)
- [ ] AC-003: Non-retryable errors (auth, schema, validation) fail immediately
- [ ] AC-004: Retry attempts logged at WARNING level with attempt number
- [ ] AC-005: Final failure after retries still returns None (graceful degradation preserved)
- [ ] AC-006: Tests cover retry success on 2nd attempt, retry exhaustion, and non-retryable errors

## Implementation Notes

Key file: `guardkit/knowledge/graphiti_client.py` — `_create_episode()` method (lines 682-702).

Retryable error patterns:
- "Max pending queries exceeded"
- "Connection reset"
- "Connection refused" (transient)

Non-retryable:
- "Authentication failed"
- "Invalid group_id"
- Any `ValueError`

## Test Execution Log
[Automatically populated by /task-work]
