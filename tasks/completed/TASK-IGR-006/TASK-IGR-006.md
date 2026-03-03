---
id: TASK-IGR-006
title: Unify constants.py with graphiti_client.py group definitions
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T12:30:00Z
completed: 2026-03-03T12:30:00Z
completed_location: tasks/completed/TASK-IGR-006/
priority: low
complexity: 3
tags: [graphiti, constants, refactoring]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: Unify constants.py with graphiti_client.py group definitions

## Description

`constants.py` defines `PROJECT_GROUPS` (6 entries) and `SYSTEM_GROUPS` (3 entries), but `graphiti_client.py` has `PROJECT_GROUP_NAMES` (7 entries) and `SYSTEM_GROUP_IDS` (19 entries). The files are not linked — `constants.py` is purely informational and has drifted.

## Implementation

Make `graphiti_client.py` import group definitions from `constants.py` as the single source of truth, and update `constants.py` to include all groups.

## Acceptance Criteria

- [x] Single source of truth for group definitions
- [x] `graphiti_client.py` imports from `constants.py`
- [x] All 7 PROJECT_GROUP_NAMES and 20 SYSTEM_GROUP_IDS represented
- [x] Existing tests pass

## Files to Modify

- `guardkit/integrations/graphiti/constants.py`
- `guardkit/knowledge/graphiti_client.py`

## Files Created

- `guardkit/_group_defs.py` (neutral shared module to avoid circular imports)

## Effort Estimate

~1 hour

## Implementation Notes

A circular import prevented direct import from `constants.py` into `graphiti_client.py`:
`graphiti_client.py` → `integrations.graphiti.__init__` → `project.py` → `graphiti_client.py`

Resolution: Created `guardkit/_group_defs.py` as a neutral shared module at the package root.
Both `constants.py` (re-exports for public API) and `graphiti_client.py` (class attributes)
import from this module. All three modules reference the same Python objects.
