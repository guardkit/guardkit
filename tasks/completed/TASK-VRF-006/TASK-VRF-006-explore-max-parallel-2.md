---
id: TASK-VRF-006
title: Explore max_parallel=2 with GPU memory safeguards for vLLM
status: completed
priority: low
complexity: 5
tags: [autobuild, vllm, max-parallel, performance]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 5
implementation_mode: task-work
dependencies: [TASK-VRF-003]
created: 2026-03-09
updated: 2026-03-09
completed: 2026-03-09
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-VRF-006/
organized_files:
  - TASK-VRF-006-explore-max-parallel-2.md
---

# Task: Explore max_parallel=2 with GPU Memory Safeguards

## Description

Investigate whether `max_parallel=2` is feasible for vLLM backends with appropriate GPU memory guardrails. The current `max_parallel=1` (from TASK-VPT-001) prevents KV cache contention but causes budget starvation in multi-task waves.

## Context

From TASK-REV-5E1F review: With `max_parallel=2`, FBP-007 would have had 3.4x more budget (9600s vs 2820s). The trade-off is GPU memory contention vs budget starvation.

## Investigation Areas

1. Test `max_parallel=2` on current vLLM setup:
   - Monitor GPU memory usage during concurrent requests
   - Measure KV cache hit rates and eviction frequency
   - Compare per-task completion time (sequential vs parallel)

2. Consider alternatives:
   - Per-wave max_parallel override (allow parallel for final wave only)
   - Dynamic max_parallel based on GPU memory availability
   - Staggered start (delay second task by N minutes)

3. If max_parallel=2 causes contention:
   - Document the specific failure mode
   - Propose GPU memory threshold for auto-scaling

## Acceptance Criteria

- [x] Test results for max_parallel=2 on vLLM documented
- [x] GPU memory impact measured and reported
- [x] Recommendation: keep max_parallel=1, change to 2, or implement dynamic scaling

## Implementation Summary

### Recommendation
Keep `max_parallel=1` as default. Add `--max-parallel-strategy=dynamic` as opt-in for GPU-aware scaling. See `docs/reviews/vllm-profiling/max_parallel_recommendation.md`.

### Deliverables
- `guardkit/orchestrator/gpu_monitor.py` - GPU memory monitoring protocol
- `guardkit/orchestrator/parallel_strategy.py` - Strategy resolver (STATIC/DYNAMIC/PER_WAVE)
- `guardkit/cli/autobuild.py` - `--max-parallel-strategy` CLI option + help text fix
- `guardkit/orchestrator/feature_orchestrator.py` - Strategy-aware wave execution
- `tests/unit/test_parallel_strategy.py` - 27 tests, 100% coverage
- `docs/reviews/vllm-profiling/max_parallel_recommendation.md` - Full analysis

### Quality Gates
- Tests: 37/37 passed (100%)
- Coverage: 100% on new modules (gpu_monitor.py, parallel_strategy.py)
- Backward compatibility: All 10 existing max_parallel tests still pass
