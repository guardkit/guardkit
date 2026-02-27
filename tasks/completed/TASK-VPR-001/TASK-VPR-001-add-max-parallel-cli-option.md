---
id: TASK-VPR-001
title: Add --max-parallel CLI option for local backends
status: completed
priority: medium
complexity: 4
tags: [autobuild, vllm, parallelism, cli, performance]
parent_review: TASK-REV-C960
feature_id: FEAT-VPR
wave: 1
implementation_mode: task-work
dependencies: []
completed: 2026-02-27T00:00:00Z
updated: 2026-02-27T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, all tests passing"
completed_location: tasks/completed/TASK-VPR-001/
---

# Task: Add --max-parallel CLI Option for Local Backends

## Description

Add a `--max-parallel N` flag to `guardkit autobuild feature` that limits concurrent task execution within waves. Default to 2 when a local backend is detected (timeout_multiplier > 1.0), unlimited otherwise.

## Context

TASK-REV-C960 Finding 5 identified that 3-task parallel waves on GB10 show ~1.7x GPU contention slowdown per task. Reducing to 2 concurrent tasks may improve per-task time enough to offset reduced parallelism, resulting in similar wall-clock time but more predictable execution.

## Acceptance Criteria

- [x] `--max-parallel N` CLI flag accepted by `guardkit autobuild feature`
- [x] Default value: 2 when `detect_timeout_multiplier() > 1.0`, otherwise no limit
- [x] `GUARDKIT_MAX_PARALLEL_TASKS` environment variable override supported
- [x] Feature orchestrator respects the limit when dispatching wave tasks
- [x] CLI help text documents the new flag
- [x] Unit tests cover: default detection, env var override, wave dispatch limiting
- [x] Existing tests continue to pass

## Implementation Summary

### Files Modified
- `guardkit/cli/autobuild.py` — Added `--max-parallel` CLI option, env var resolution, auto-detect logic
- `guardkit/orchestrator/feature_orchestrator.py` — Added `max_parallel` param, `asyncio.Semaphore` in `_execute_wave_parallel()`

### Files Created
- `tests/unit/test_max_parallel.py` — 10 unit tests across 4 test classes

### Priority Resolution Chain
```
GUARDKIT_MAX_PARALLEL_TASKS env var → --max-parallel CLI flag → auto-detect (2 if local, None if remote)
```

### Test Results
- New tests: 10/10 passed
- Existing CLI tests: 53/53 passed
- Existing orchestrator tests: 89/89 passed
- Total: 152 passed, 0 failed
