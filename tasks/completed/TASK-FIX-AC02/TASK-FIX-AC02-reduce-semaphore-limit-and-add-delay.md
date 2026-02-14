---
id: TASK-FIX-AC02
title: Reduce SEMAPHORE_LIMIT and add inter-episode delay to prevent FalkorDB query saturation
status: completed
created: 2026-02-13T00:00:00Z
updated: 2026-02-14T00:00:00Z
completed: 2026-02-14T00:00:00Z
priority: high
tags: [fix, graphiti, add-context, falkordb, rate-limiting]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
test_results:
  status: passed
  total_tests: 10
  passed: 10
  failed: 0
  last_run: 2026-02-14T00:00:00Z
---

# Task: Reduce SEMAPHORE_LIMIT and add inter-episode delay

## Description

graphiti-core fires up to 20 parallel queries per `add_episode()` via `semaphore_gather()`. Combined with FalkorDB index creation at startup, this exceeds FalkorDB's pending query limit. Add two mitigations:

1. Set `SEMAPHORE_LIMIT=5` in `add-context` command before Graphiti init (env var read by graphiti-core at import)
2. Add configurable inter-episode delay (default 0.5s) to let FalkorDB drain between episodes

## Review Reference

TASK-REV-1294 recommendations R1 (P0) + R2 (P2). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-002.

## Acceptance Criteria

- [x] AC-001: `SEMAPHORE_LIMIT` env var set to 5 before graphiti-core import in add-context command
- [x] AC-002: `--delay` CLI option controls inter-episode sleep (default 0.5s, 0 to disable)
- [x] AC-003: No "Max pending queries exceeded" errors when processing 9+ ADRs sequentially
- [x] AC-004: `SEMAPHORE_LIMIT` override only affects add-context command, not global graphiti-core usage
- [x] AC-005: Tests verify delay is applied between episodes

## Implementation Notes

Key files:
- `guardkit/cli/graphiti.py` — set `os.environ["SEMAPHORE_LIMIT"] = "5"` early in `_cmd_add_context()`, add `--delay` Click option
- Episode loop at line 663: add `await asyncio.sleep(delay)` after each successful episode

Important: `SEMAPHORE_LIMIT` must be set BEFORE `import graphiti_core` since it reads the env var at module load time.

## Test Execution Log
[Automatically populated by /task-work]
