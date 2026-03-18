---
id: TASK-GCA-002
title: Fix /system-design Graphiti availability detection and seeding
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T12:00:00Z'
completed: '2026-03-18T12:00:00Z'
priority: high
complexity: 5
tags: [graphiti, system-design, command-specs]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 2
depends_on:
  - TASK-GCA-001
---

# Fix /system-design Graphiti availability detection and seeding

## Description

Replace all Python pseudocode Graphiti patterns in `installer/core/commands/system-design.md` with tool-native instructions referencing the shared preamble (TASK-GCA-001).

This is the primary command that triggered REV-SD-001 — it has 3 availability check blocks and 1 seeding block to replace.

## Acceptance Criteria

- [x] Prerequisite Gate (lines ~44-74): Replaced with Read-based `.guardkit/graphiti.yaml` check + reference to preamble
- [x] Phase 0: Context Loading (lines ~80-114): Replaced with Read-based check + instructions to read local `docs/architecture/` files
- [x] Step 1: Prerequisite Check (lines ~1134-1168): Replaced with preamble reference
- [x] Step 8: Graphiti Seeding (lines ~1262-1272): Replaced with `guardkit graphiti add-context` CLI commands
- [x] Graceful Degradation section (lines ~786-809): Updated to reference preamble pattern
- [x] GRAPHITI_UNAVAILABLE_MESSAGE (lines ~1305-1317): Updated install instructions (remove `.env` reference, point to `.guardkit/graphiti.yaml`)
- [x] All `from guardkit.knowledge.graphiti_client import get_graphiti` removed
- [x] All `SystemDesignGraphiti` / `SystemPlanGraphiti` instantiation pseudocode removed or replaced with CLI equivalents
- [x] The installed copy at `~/.agentecflow/commands/system-design.md` is updated

## Files to Modify

- `installer/core/commands/system-design.md` (~20 locations with Python Graphiti pseudocode)

## Implementation Notes

The seeding phase should generate concrete `guardkit graphiti add-context` commands for the artefacts produced during the design session:
- API contracts → `--group project_design`
- Data models → `--group project_design`
- Design decisions (DDRs) → `--group architecture_decisions`

The command spec should instruct the LLM to ask the user whether to execute the seeding commands or just display them.
