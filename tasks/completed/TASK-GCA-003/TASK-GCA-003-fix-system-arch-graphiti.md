---
id: TASK-GCA-003
title: Fix /system-arch Graphiti availability detection and seeding
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T12:00:00Z'
completed: '2026-03-18T12:00:00Z'
completed_location: tasks/completed/TASK-GCA-003/
priority: high
complexity: 5
tags: [graphiti, system-arch, command-specs]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 2
depends_on:
  - TASK-GCA-001
---

# Fix /system-arch Graphiti availability detection and seeding

## Description

Replace all Python pseudocode Graphiti patterns in `installer/core/commands/system-arch.md` with tool-native instructions referencing the shared preamble.

This command has 3 availability check blocks and 1 seeding block. It also uses a different import path (`guardkit.knowledge.graphiti_service` instead of `graphiti_client`) which should be harmonised.

## Acceptance Criteria

- [x] Mode detection (lines ~36-52): Replaced with Read-based check; mode detection via local file existence (`docs/architecture/`)
- [x] Phase 0: Context Loading (lines ~60-64): Replaced with preamble reference
- [x] Step 2: Initialize Graphiti (lines ~998-1012): Replaced with Read-based check
- [x] Phase 4: Graphiti Seeding (lines ~572-620): Replaced with `guardkit graphiti add-context` CLI commands
- [x] All `from guardkit.knowledge.graphiti_service import get_graphiti` replaced (note: uses `graphiti_service` not `graphiti_client`)
- [x] `sanitise_for_graphiti()` usage documented as CLI flag or pre-processing step
- [x] Seeding groups: `project_architecture`, `project_decisions` documented

## Files to Modify

- `installer/core/commands/system-arch.md`

## Implementation Notes

The seeding phase produces:
- Bounded contexts → `--group project_architecture`
- ADRs → `--group architecture_decisions` (with sanitisation note)
- Technology decisions → `--group project_decisions`
- Cross-cutting concerns → `--group project_architecture`

The `sanitise_for_graphiti()` function strips prompt injection attempts from free-text ADR rationale. The CLI equivalent should note that `guardkit graphiti add-context` handles sanitisation internally, or the LLM should sanitise before passing to the CLI.
