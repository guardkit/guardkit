---
id: TASK-FIX-DF01
title: Add configurable wave parallelism for local backends
status: backlog
task_type: implementation
priority: low
tags: [autobuild, vllm, config, feature-orchestrator, p2]
complexity: 4
parent_review: TASK-REV-5610
feature_id: FEAT-FF93
wave: 3
implementation_mode: task-work
dependencies: [TASK-FIX-6141, TASK-FIX-7718]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add Configurable Wave Parallelism for Local Backends

## Description

Add a `GUARDKIT_MAX_PARALLEL_TASKS` environment variable to limit the number of concurrent tasks per wave when running on local backends. Default to 2 for local backends (detected via `timeout_multiplier > 1.0`), unlimited for Anthropic.

**Note**: This task is P2 (deferred). R1 (AC search fix) and R2 (SDK turn budget) may resolve the underlying timing issues that make reduced parallelism necessary. Re-evaluate after run 3 with R1+R2 applied.

## Root Cause

Wave 3 runs 3 tasks in parallel, all making concurrent requests to a single GPU via vLLM. This caused a transient SDK streaming error on DB-006. Limiting to 2 concurrent tasks would reduce GPU memory/compute pressure.

However, the streaming error was transient (Turn 2 succeeded) and the primary impact was indirect (cascading through state recovery → re-implementation → timeout). With R1 and R2 fixing the direct causes, parallel contention may no longer be the bottleneck.

## Implementation

In `feature_orchestrator.py`:

```python
# At init or in _execute_wave_parallel():
max_parallel = int(os.environ.get("GUARDKIT_MAX_PARALLEL_TASKS", 0))
if max_parallel == 0:
    # Auto-detect: 2 for local, unlimited for Anthropic
    max_parallel = 2 if self.timeout_multiplier > 1.0 else len(task_ids)

# Batch tasks into groups of max_parallel
for batch_start in range(0, len(tasks_to_execute), max_parallel):
    batch = tasks_to_execute[batch_start:batch_start + max_parallel]
    batch_results = await asyncio.gather(*batch, return_exceptions=True)
    all_results.extend(batch_results)
```

## Acceptance Criteria

- [ ] `GUARDKIT_MAX_PARALLEL_TASKS` env var controls max concurrent tasks per wave
- [ ] Default: auto-detect (2 for local, unlimited for Anthropic)
- [ ] Env var override: `GUARDKIT_MAX_PARALLEL_TASKS=3` overrides auto-detection
- [ ] Batching logic correctly handles waves with more tasks than max_parallel
- [ ] Anthropic API behaviour unchanged (no parallelism reduction)
- [ ] Existing tests pass

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/feature_orchestrator.py` | Add parallelism batching in `_execute_wave_parallel()` |

## Risk Assessment

**Risk**: Medium
- Changes parallel execution logic that affects all backends
- Needs careful testing to avoid breaking Anthropic parallel execution
- Batching introduces sequential waiting within a wave
- Deferred: re-evaluate after R1+R2 are applied and run 3 results are available
