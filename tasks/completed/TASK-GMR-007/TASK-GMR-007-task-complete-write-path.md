---
id: TASK-GMR-007
title: "Add /task-complete knowledge capture write path"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
completed_location: tasks/completed/TASK-GMR-007/
previous_state: in_review
state_transition_reason: "All 7 acceptance criteria met - Graphiti write path added to task-complete.md"
priority: high
tags: [graphiti, mcp, task-complete, write-path, knowledge-capture]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 3
conductor_workspace: graphiti-mcp-restoration-wave3-1
complexity: 3
depends_on:
  - TASK-GMR-001
  - TASK-GMR-003
organized_files: [
  "TASK-GMR-007-task-complete-write-path.md"
]
---

# Add /task-complete Knowledge Capture Write Path

## Description

Currently zero task lifecycle events automatically capture knowledge to Graphiti. The knowledge graph becomes stale because only manual seeding adds data. This task adds automatic capture when a task is completed, starting the learning flywheel that makes all read paths (task-work, task-review, feature-plan) valuable over time.

## What to Capture

On `/task-complete TASK-XXX`:

| Data | Group ID | Format |
|------|----------|--------|
| Task outcome | `task_outcomes` | `"{task_id}: {title}. Approach: {approach}. Result: {outcome}. Lessons: {lessons}."` |
| Key decisions made | `project_decisions` | Any architectural decisions noted in the task |

## Acceptance Criteria

- [x] AC-1: `/task-complete` command spec (installer/core/commands/task-complete.md) includes Graphiti write step
- [x] AC-2: Uses MCP `mcp__graphiti__add_memory` when available
- [x] AC-3: Falls back to `guardkit graphiti add-context` CLI when MCP not available
- [x] AC-4: Captures: task ID, title, approach taken, outcome, and lessons learned
- [x] AC-5: Uses correct group_id: `task_outcomes` (project-prefixed automatically by client)
- [x] AC-6: Write path is non-blocking — task completion succeeds even if Graphiti write fails
- [x] AC-7: Display: "[Graphiti] Task outcome captured to knowledge graph"

## Implementation Notes

- The knowledge graph interface (`mcp__graphiti__add_memory`) expects a text episode — format the task outcome as a narrative string
- Task metadata available from task file frontmatter (id, title, status, complexity, etc.)
- Approach and lessons may need to be extracted from task notes section or commit history
- This is the **most important write path** — it enables cross-task learning for all future read queries
