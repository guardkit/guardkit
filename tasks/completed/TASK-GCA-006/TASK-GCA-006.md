---
id: TASK-GCA-006
title: Fix /arch-refine and /design-refine Graphiti availability and seeding
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T12:00:00Z'
completed: '2026-03-18T12:00:00Z'
priority: medium
complexity: 5
tags: [graphiti, arch-refine, design-refine, command-specs]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 2
depends_on:
  - TASK-GCA-001
completed_location: tasks/completed/TASK-GCA-006/
---

# Fix /arch-refine and /design-refine Graphiti availability and seeding

## Description

Replace Python pseudocode Graphiti patterns in the two refinement commands. These have 3 availability blocks each plus seeding operations.

## Acceptance Criteria

### /arch-refine (3 availability + 1 seeding)
- [x] Lines ~45-48: Availability check replaced with preamble reference
- [x] Lines ~74-76: Context loading replaced with Read-based pattern
- [x] Lines ~760-762: Execution section replaced with preamble reference
- [x] Seeding operations replaced with `guardkit graphiti add-context` CLI commands
- [x] `sanitise_for_graphiti()` usage documented

### /design-refine (3 availability + 1 seeding)
- [x] Lines ~49-52: Availability check replaced with preamble reference
- [x] Lines ~86-89: Context loading replaced with Read-based pattern
- [x] Lines ~1027-1029: Execution section replaced with preamble reference
- [x] Seeding operations replaced with `guardkit graphiti add-context` CLI commands
- [x] `SystemDesignGraphiti` / `SystemPlanGraphiti` pseudocode replaced

### Both
- [x] All `from guardkit.knowledge.graphiti_client import get_graphiti` removed
- [x] Graceful degradation messaging updated

## Files Modified

- `installer/core/commands/arch-refine.md`
- `installer/core/commands/design-refine.md`

## Implementation Notes

Replaced all Python pseudocode Graphiti patterns with tool-native LLM instructions following the patterns established in `lib/graphiti-preamble.md`:

- **3 availability blocks each** → Tier 1 Read-based checks (`.guardkit/graphiti.yaml`)
- **Seeding operations** → `guardkit graphiti add-context --group architecture_decisions` CLI commands
- **Graceful degradation** → Standard preamble warning template
- **`sanitise_for_graphiti()`** → Documented as handled automatically by CLI
- **Disambiguation** (arch-refine Phase 1) → Also updated from Python pseudocode to tool-native instructions
