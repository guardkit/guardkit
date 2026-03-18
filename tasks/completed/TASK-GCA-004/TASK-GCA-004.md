---
id: TASK-GCA-004
title: Fix /system-plan Graphiti availability detection
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T12:00:00Z'
completed: '2026-03-18T12:00:00Z'
completed_location: tasks/completed/TASK-GCA-004/
priority: high
complexity: 4
tags: [graphiti, system-plan, command-specs]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 2
depends_on:
  - TASK-GCA-001
---

# Fix /system-plan Graphiti availability detection

## Description

Replace all Python pseudocode Graphiti patterns in `installer/core/commands/system-plan.md` with tool-native instructions referencing the shared preamble.

This command has 3 availability check blocks. It also uses `graphiti_service` import path (same as system-arch) which should be harmonised.

## Acceptance Criteria

- [x] Mode detection (lines ~43-52): Replaced with Read-based check
- [x] Context loading (lines ~792-796): Replaced with preamble reference
- [x] Execution summary (lines ~1066): Updated references
- [x] All `from guardkit.knowledge.graphiti_service import get_graphiti` replaced
- [x] `SystemPlanGraphiti` pseudocode replaced with CLI equivalents or Read-based context loading

## Files to Modify

- `installer/core/commands/system-plan.md`
