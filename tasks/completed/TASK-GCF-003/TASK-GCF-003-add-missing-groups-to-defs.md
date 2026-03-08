---
id: TASK-GCF-003
title: Add task_outcomes and turn_states to _group_defs.py
status: completed
task_type: implementation
priority: medium
tags: [graphiti, bugfix, group-definitions]
complexity: 2
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
wave: 1
implementation_mode: direct
dependencies: []
created: 2026-03-08T15:00:00Z
completed: 2026-03-08T16:00:00Z
---

# Task: Add task_outcomes and turn_states to _group_defs.py

## Problem

`task_outcomes` and `turn_states` are queried by `JobContextRetriever` but are NOT defined in `_group_defs.py`. This causes `is_project_group()` to default to `True` (line 341 of `graphiti_client.py`), which auto-prefixes them with `{project_id}__`. While this happens to be correct behaviour (they should be project-scoped), it relies on an undocumented default rather than explicit definition.

## Requirements

1. Add `task_outcomes` to PROJECT_GROUPS in `_group_defs.py` with description "Task completion outcomes and lessons learned"
2. Add `turn_states` to PROJECT_GROUPS in `_group_defs.py` with description "Feature-build turn state history for cross-turn learning"
3. Verify that `outcome_manager.py` and `turn_state_operations.py` use the same group ID strings

## Files to Modify

- `guardkit/_group_defs.py`
- `tests/` (update any tests that assert on group counts)

## Acceptance Criteria

- [x] `task_outcomes` in PROJECT_GROUPS
- [x] `turn_states` in PROJECT_GROUPS
- [x] Group IDs match usage in `outcome_manager.py` and `turn_state_operations.py`
- [x] Existing tests pass
