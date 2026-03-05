---
id: TASK-SPR-9d9b
title: Add seed summary statistics at end of seed run
status: completed
completed: 2026-03-05T14:00:00Z
task_type: implementation
created: 2026-03-05T12:00:00Z
priority: medium
complexity: 2
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, seeding, ux, logging]
wave: 2
implementation_mode: direct
dependencies: [TASK-SPR-2cf7]
---

# Task: Add seed summary statistics at end of seed run

## Problem

After seeding, there is no aggregate summary showing overall success rate. Users must mentally add up per-category results to understand the outcome.

## Solution

Add a summary line at the end of the seed output:

```
Seed Summary:
  Categories: 14/17 fully seeded, 3 partial/failed
  Episodes: 101/193 created (52.3%)
  Skipped: 92 episodes
  Duration: 45m 23s
```

## Files to Modify

- `guardkit/cli/graphiti.py` — Add summary display after category list
- `guardkit/knowledge/seeding.py` — Return aggregate results from `seed_all_system_context()`

## Acceptance Criteria

- [x] Summary shows total categories succeeded/failed
- [x] Summary shows total episodes created/skipped with percentage
- [x] Summary shows total duration
- [x] Summary appears after the per-category list
