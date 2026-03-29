---
id: TASK-GMR-008
title: "Add /task-review knowledge capture write path"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
priority: medium
tags: [graphiti, mcp, task-review, write-path, knowledge-capture]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 3
conductor_workspace: graphiti-mcp-restoration-wave3-2
complexity: 3
depends_on:
  - TASK-GMR-001
  - TASK-GMR-003
---

# Add /task-review Knowledge Capture Write Path

## Description

When a review is accepted ([A]ccept at decision checkpoint), key findings and architectural decisions should be automatically captured to the knowledge graph. This preserves review insights for future reviews and implementations.

Note: `/task-review` already has a `--capture-knowledge` flag in the spec (Phase 4.5) but it's not connected to Graphiti. This task wires it up.

## What to Capture

On `/task-review` [A]ccept:

| Data | Group ID | Format |
|------|----------|--------|
| Review findings | `project_decisions` | Key architectural findings and their rationale |
| Score and recommendations | `task_outcomes` | Review score, recommendation summary |

## Acceptance Criteria

- [ ] AC-1: [A]ccept at decision checkpoint triggers Graphiti write
- [ ] AC-2: Uses MCP `mcp__graphiti__add_memory` when available
- [ ] AC-3: Falls back to CLI when MCP not available
- [ ] AC-4: Captures review mode, score, key findings, and recommendations
- [ ] AC-5: Uses correct group_ids: `project_decisions` for findings, `task_outcomes` for score
- [ ] AC-6: Non-blocking — review acceptance succeeds even if write fails
- [ ] AC-7: Integrates with existing `--capture-knowledge` flag (Phase 4.5 in task-review spec)

## Implementation Notes

- The `--capture-knowledge` flag already exists in the task-review spec but is not wired to Graphiti
- Review report is generated at `.claude/reviews/TASK-XXX-review-report.md` — extract key findings from there
- `guardkit/knowledge/review_knowledge_capture.py` already exists — evaluate if it can be used
