---
id: TASK-ABFIX-005
title: Isolate Coach independent tests from parallel worktree contention
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: [TASK-ABFIX-001]
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: backlog
priority: high
tags: [autobuild, orchestrator, coach, worktree, parallel]
---

# Task: Isolate Coach independent tests from parallel worktree contention

## Description

Coach independent tests currently run against the live (shared) worktree, which may be concurrently modified by other parallel tasks in the same wave. This causes spurious test failures (e.g., `ImportError` from a modified `__init__.py`) that are classified as `code` failures and trigger unnecessary feedback turns.

Implement test isolation for Coach independent tests when running in a parallel wave, and update the conditional approval formula to handle `code` failures in parallel wave context.

## Review Reference

From TASK-REV-A17A Finding 3, Recommendations 3a, 3b, 3c:
> 3a: Run Coach tests against a per-task git snapshot. Before running independent tests, isolate the test environment from concurrent mutations.
> 3b: Grant conditional approval for `code` failures when all gates passed and task is in a parallel wave.
> 3c: Add `parallel_contention` failure classification when running in a parallel wave.

## Requirements

1. Test isolation (choose ONE approach):
   - **Option A (git stash)**: Before running independent tests in `coach_validator.run_independent_tests()` (lines 1264-1455), stash/snapshot the task's changes, run tests, then restore. Needs serialization with parallel checkpoint commits.
   - **Option B (tempdir copy)**: Copy task-specific test files + source files to a temp directory and run tests there. Avoids git contention entirely.
   - **Option C (per-task worktree)**: Create a lightweight per-task git worktree for Coach testing. Most isolated but highest overhead.
2. Parallel wave awareness in conditional approval:
   - In `coach_validator.py:665-774`, when `wave_size > 1` and `gates_status.all_gates_passed`:
     - Grant conditional approval for `code` failures (not just `collection_error`)
   - Requires passing `wave_size` or `is_parallel` flag to Coach validator
3. Add `parallel_contention` failure classification:
   - In `coach_validator._classify_test_failure()` (lines 2713-2812):
     - When `wave_size > 1`, reclassify `code` → `parallel_contention` with `conditional_approval=True`
4. Tests verifying:
   - Coach tests are isolated from parallel mutations
   - Conditional approval works for `code` failures in parallel waves
   - Serial (wave_size=1) tasks are NOT affected by the change

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — test isolation, conditional approval, classification
- `guardkit/orchestrator/autobuild.py` — pass wave context to Coach
- `guardkit/orchestrator/feature_orchestrator.py` — pass wave_size to task execution
- `tests/` — test isolation, conditional approval in parallel context

## Acceptance Criteria

- [ ] Coach independent tests are isolated from parallel task mutations
- [ ] `code` failures in parallel waves get conditional approval when all gates passed
- [ ] `parallel_contention` classification exists and is used appropriately
- [ ] Serial task execution is NOT affected
- [ ] All existing tests pass
- [ ] New tests cover parallel isolation and conditional approval
