---
id: TASK-GCA-005
title: Fix /system-overview, /impact-analysis, /context-switch Graphiti availability
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T00:00:00Z'
completed: '2026-03-18T00:00:00Z'
priority: medium
complexity: 4
tags: [graphiti, system-overview, impact-analysis, context-switch, command-specs]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 2
depends_on:
  - TASK-GCA-001
completed_location: tasks/completed/TASK-GCA-005/
---

# Fix /system-overview, /impact-analysis, /context-switch Graphiti availability

## Description

Replace Python pseudocode Graphiti patterns in three simpler commands that have fewer Graphiti touchpoints. These are grouped into one task because each has only 1-2 blocks to replace.

## Acceptance Criteria

### /system-overview (2 blocks)
- [x] Lines ~39-43: Availability check replaced with preamble reference
- [x] Lines ~284-287: Context loading replaced with Read-based pattern

### /impact-analysis (2 blocks)
- [x] Lines ~89-92: Availability check replaced with preamble reference
- [x] Lines ~430-433: Context loading replaced with Read-based pattern

### /context-switch (1 block)
- [x] Lines ~447-449: Availability check replaced with preamble reference

### All three
- [x] All `from guardkit.knowledge.graphiti_client import get_graphiti` removed
- [x] Graceful degradation messaging updated

## Files Modified

- `installer/core/commands/system-overview.md`
- `installer/core/commands/impact-analysis.md`
- `installer/core/commands/context-switch.md`
