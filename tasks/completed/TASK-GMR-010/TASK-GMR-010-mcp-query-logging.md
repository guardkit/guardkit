---
id: TASK-GMR-010
title: "Add MCP query result logging for data quality tracking"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
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
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
completed_location: tasks/completed/TASK-GMR-010/
organized_files:
  - TASK-GMR-010-mcp-query-logging.md
---

# Add MCP Query Result Logging

## Description

Track what MCP queries return (empty vs populated, result count, relevance) to validate data quality over time. Without this, there's no way to know if the seeded knowledge graph data is useful for the queries commands are making.

## Acceptance Criteria

- [x] AC-1: MCP query results logged to `.guardkit/graphiti-query-log.jsonl` (append-only)
- [x] AC-2: Each log entry includes: timestamp, command, query text, group_ids, result count, first result preview (50 chars)
- [x] AC-3: Log rotation or max file size (e.g., 1MB) to prevent unbounded growth
- [x] AC-4: Log file is gitignored

## Implementation Summary

### Files Created
- `guardkit/knowledge/query_logger.py` — JSONL logger with thread-safe append, 1MB rotation, preview extraction
- `tests/knowledge/test_query_logger.py` — 26 tests (path resolution, entry building, rotation, logging, preview extraction, thread safety)

### Files Modified
- `guardkit/knowledge/graphiti_client.py` — Integrated `log_query()` into `search()` and `add_episode()` methods
- `.gitignore` — Added `.guardkit/graphiti-query-log.jsonl` and `.jsonl.1` patterns

### Design Decisions
- Logging integrated at `GraphitiClient` level (covers all Python-side queries)
- Single-backup rotation (`.jsonl.1`) — simple, sufficient for debugging tool
- Thread-safe via module-level lock — matches `GraphitiClient`'s threading model
- Never raises — all errors caught at DEBUG level for graceful degradation
- Lazy import in `graphiti_client.py` to avoid circular dependencies

## Implementation Notes

- This can be a simple JSONL append in the command spec after each MCP tool call
- Alternatively, could be a post-command hook if hooks support it
- Primary purpose is debugging data quality — not production telemetry
- Keep it lightweight — one line per query, not full result dumps
