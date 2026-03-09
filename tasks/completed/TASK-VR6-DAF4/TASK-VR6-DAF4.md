---
id: TASK-VR6-DAF4
title: Add task-type-aware wave separation to detect_parallel_groups()
status: completed
task_type: implementation
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T12:00:00Z
completed: 2026-03-09T12:00:00Z
completed_location: tasks/completed/TASK-VR6-DAF4/
priority: high
complexity: 4
wave: 1
implementation_mode: task-work
parent_review: TASK-REV-35DC
feature_id: FEAT-81DD
tags: [autobuild, feature-plan, wave-assignment, parallel-analyzer]
dependencies: []
organized_files:
  - TASK-VR6-DAF4.md
---

# Task: Add task-type-aware wave separation to detect_parallel_groups()

## Description

Update `detect_parallel_groups()` in `installer/core/lib/parallel_analyzer.py` to prevent budget starvation when `max_parallel=1`. Currently, the algorithm assigns waves based solely on file conflicts and dependencies, with no awareness of serialization risk.

When `max_parallel=1`, tasks within a wave are serialized by a semaphore. If a high-complexity task consumes most of the wave budget, subsequent tasks face budget starvation. This caused FBP-007 to be cancelled in Runs 4-6.

## Context

The wave assignment algorithm at `parallel_analyzer.py:178-296` performs:
1. Build file map (which tasks touch which files)
2. Build conflict graph (tasks that share files cannot be parallel)
3. Greedy wave assignment respecting dependency order

It has NO awareness of:
- `max_parallel` setting (doesn't know tasks are serialized)
- Task complexity or estimated runtime
- Budget starvation risk

## Proposed Solution

Add a post-processing rule after wave assignment:

```
When max_parallel=1:
    For each wave with >1 task:
        Enforce single-task-per-wave
        (redistribute extra tasks to subsequent waves, preserving dependency order)
```

This is the simplest correct solution because with `max_parallel=1`, multiple tasks in a wave are serialized anyway — wave count doesn't affect parallelism. Each task gets a fresh budget.

### Alternative (more nuanced)

Only separate when wave contains tasks with combined estimated runtime > 60% of task_timeout. This requires complexity-based runtime estimation but allows co-location of quick tasks.

## Expected Interface

The `detect_parallel_groups()` function should accept an optional `max_parallel` parameter:

```python
def detect_parallel_groups(
    subtasks: List[Dict],
    max_parallel: int = 0,  # 0 = auto-detect / unlimited
) -> List[Dict]:
```

When `max_parallel=1`, apply the single-task-per-wave rule.

## Acceptance Criteria

- [x] `detect_parallel_groups()` accepts optional `max_parallel` parameter
- [x] When `max_parallel=1`, each wave contains at most 1 task
- [x] Dependency ordering is preserved (tasks only move to later waves, never earlier)
- [x] When `max_parallel > 1` or 0 (default), existing behavior is unchanged
- [x] Tests cover: max_parallel=1 with 2 tasks in same wave → separated
- [x] Tests cover: max_parallel=1 with dependency chain → waves preserved
- [x] Tests cover: max_parallel=0 (default) → no change to existing behavior
- [x] Existing parallel_analyzer tests continue to pass

## Files Modified

- `installer/core/lib/parallel_analyzer.py` — Added `max_parallel` parameter and `_enforce_single_task_waves()` helper
- `tests/test_parallel_analyzer.py` — Added `TestMaxParallelOne` class with 8 test cases

## Completion Summary

- **Tests**: 50/50 passed (42 existing + 8 new)
- **Coverage**: 97% for parallel_analyzer.py
- **Approach**: Post-processing after greedy wave assignment splits multi-task waves into single-task waves when `max_parallel=1`

## Compatibility with Commit 821dfda5

This file (`parallel_analyzer.py`) was NOT modified in commit 821dfda5. No conflicts expected. The commit's changes (session resume, local turn state, command verification) are orthogonal to wave assignment.
