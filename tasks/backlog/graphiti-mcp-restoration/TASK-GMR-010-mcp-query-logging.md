---
id: TASK-GMR-010
title: "Add MCP query result logging for data quality tracking"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
priority: low
tags: [graphiti, mcp, observability, data-quality]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 4
conductor_workspace: graphiti-mcp-restoration-wave4-2
complexity: 2
depends_on:
  - TASK-GMR-004
---

# Add MCP Query Result Logging

## Description

Track what MCP queries return (empty vs populated, result count, relevance) to validate data quality over time. Without this, there's no way to know if the seeded knowledge graph data is useful for the queries commands are making.

## Acceptance Criteria

- [ ] AC-1: MCP query results logged to `.guardkit/graphiti-query-log.jsonl` (append-only)
- [ ] AC-2: Each log entry includes: timestamp, command, query text, group_ids, result count, first result preview (50 chars)
- [ ] AC-3: Log rotation or max file size (e.g., 1MB) to prevent unbounded growth
- [ ] AC-4: Log file is gitignored

## Implementation Notes

- This can be a simple JSONL append in the command spec after each MCP tool call
- Alternatively, could be a post-command hook if hooks support it
- Primary purpose is debugging data quality — not production telemetry
- Keep it lightweight — one line per query, not full result dumps
