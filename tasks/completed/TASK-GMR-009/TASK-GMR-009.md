---
id: TASK-GMR-009
title: "Add context influence observability markers"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
completed_location: tasks/completed/TASK-GMR-009/
priority: medium
tags: [graphiti, observability, commands]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 4
conductor_workspace: graphiti-mcp-restoration-wave4-1
complexity: 2
depends_on:
  - TASK-GMR-004
  - TASK-GMR-005
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
organized_files:
  - TASK-GMR-009.md
---

# Add Context Influence Observability Markers

## Description

Currently there is no way to distinguish "Graphiti loaded useful context" from "Graphiti silently failed" from "Graphiti returned nothing relevant." All three produce identical user-visible outcomes. Add observability markers so users can see whether knowledge graph context is being loaded and whether it influences decisions.

## Acceptance Criteria

- [x] AC-1: Phase 1.7 output shows count of items loaded and source (MCP vs CLI)
- [x] AC-2: Phase 2 plan output includes a "Context Used" section showing which Graphiti results influenced the plan
- [x] AC-3: If no context was loaded, Phase 2 output says "No knowledge graph context available — planning from task description only"
- [x] AC-4: Review output (task-review) similarly shows whether historical context was used

## Implementation Notes

- This is primarily a command spec change (markdown)
- The goal is visibility, not metrics — users should be able to see at a glance whether Graphiti is contributing
- Keep markers concise — one line per command output, not verbose logging

## Completion Summary

### Files Modified
1. `installer/core/commands/task-work.md` — Phase 1.7 stores `graphiti_access_method`; Phase 2 prompt adds "Context Used" instruction and "No knowledge graph context" else clause; Phase 2 completion message shows context source
2. `installer/core/commands/task-review.md` — Phase 1.5 display shows source (MCP/CLI); Phase 2 prompt adds "Context Used" instruction and "No knowledge graph context" else clause
3. `installer/core/commands/lib/graphiti_context_loader.py` — Log messages updated to match observability format
