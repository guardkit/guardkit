---
id: TASK-GMR-005
title: "Add Graphiti context loading to /task-review"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
priority: high
tags: [graphiti, mcp, task-review, command-spec]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 2
conductor_workspace: graphiti-mcp-restoration-wave2-2
complexity: 4
depends_on:
  - TASK-GMR-001
  - TASK-GMR-002
  - TASK-GMR-003
---

# Add Graphiti Context Loading to /task-review

## Description

`/task-review` currently has zero Graphiti integration. Reviews are where architectural context matters most — knowing past review findings, known architectural violations, and ADR rationale directly improves review quality.

Add MCP-based context loading to Phase 1 of the task-review command spec.

## What to Load

| Query | Group IDs | Purpose |
|-------|-----------|---------|
| Architecture decisions related to review scope | `architecture_decisions`, `guardkit__project_decisions` | Know what ADRs apply |
| Past failure patterns | `guardkit__task_outcomes` | Know what went wrong before |
| Similar past reviews | `guardkit__task_outcomes` | Know what previous reviews found |

## Acceptance Criteria

- [ ] AC-1: Phase 1 of `/task-review` (installer/core/commands/task-review.md) includes MCP-based context loading
- [ ] AC-2: Context loaded before Phase 2 (Execute Review Analysis) begins
- [ ] AC-3: Loaded context passed to review agents (architectural-reviewer, code-reviewer, etc.)
- [ ] AC-4: CLI wrapper fallback when MCP not available
- [ ] AC-5: Display message: "[Graphiti] Review context loaded: N items from knowledge graph"
- [ ] AC-6: Context influences review criteria (e.g., "Past reviews found X — check for recurrence")

## Implementation Notes

- Follow the same MCP-first pattern established in TASK-GMR-004 for /task-work
- The task-review command spec is at `installer/core/commands/task-review.md`
- Review agents are invoked via the Agent tool — context can be passed in the agent prompt
