---
id: TASK-GMR-009
title: "Add context influence observability markers"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
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
---

# Add Context Influence Observability Markers

## Description

Currently there is no way to distinguish "Graphiti loaded useful context" from "Graphiti silently failed" from "Graphiti returned nothing relevant." All three produce identical user-visible outcomes. Add observability markers so users can see whether knowledge graph context is being loaded and whether it influences decisions.

## Acceptance Criteria

- [ ] AC-1: Phase 1.7 output shows count of items loaded and source (MCP vs CLI)
- [ ] AC-2: Phase 2 plan output includes a "Context Used" section showing which Graphiti results influenced the plan
- [ ] AC-3: If no context was loaded, Phase 2 output says "No knowledge graph context available — planning from task description only"
- [ ] AC-4: Review output (task-review) similarly shows whether historical context was used

## Implementation Notes

- This is primarily a command spec change (markdown)
- The goal is visibility, not metrics — users should be able to see at a glance whether Graphiti is contributing
- Keep markers concise — one line per command output, not verbose logging
