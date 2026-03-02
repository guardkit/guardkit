---
id: TASK-FIX-7532
title: Change TASK-INST-012 task_type from enhancement to feature
task_type: documentation
parent_review: TASK-REV-7530
feature_id: FEAT-CF57
wave: 1
implementation_mode: direct
complexity: 1
priority: critical
dependencies: []
status: completed
completed: 2026-03-02T00:00:00Z
tags: [autobuild, task-type, frontmatter, quick-fix]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix TASK-INST-012 task_type

## Context

`tasks/backlog/autobuild-instrumentation/TASK-INST-012-enrich-system-seeding.md` uses `task_type: enhancement` (an alias) instead of the canonical value `feature`. While aliases should work after TASK-FIX-7531, best practice is to use canonical enum values in task frontmatter to avoid alias-resolution dependencies.

## Implementation

Change line 4 of `tasks/backlog/autobuild-instrumentation/TASK-INST-012-enrich-system-seeding.md`:

```diff
- task_type: enhancement
+ task_type: feature
```

Also reset the `status` from `blocked` back to `backlog` (or `pending`) and clear the `autobuild_state` error feedback so a fresh run can proceed cleanly.

## Acceptance Criteria

- [x] TASK-INST-012 task file uses `task_type: feature`
- [x] Task status allows re-execution
