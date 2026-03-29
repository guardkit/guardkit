---
id: TASK-GMR-006
title: "Add pre-planning context to /feature-plan via MCP"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
priority: medium
tags: [graphiti, mcp, feature-plan, command-spec]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 2
conductor_workspace: graphiti-mcp-restoration-wave2-3
complexity: 4
depends_on:
  - TASK-GMR-001
  - TASK-GMR-002
  - TASK-GMR-003
---

# Add Pre-Planning Context to /feature-plan via MCP

## Description

`/feature-plan` currently has post-generation seeding (write-only) but no pre-planning read path. Feature planning should query the knowledge graph for similar past features, architecture constraints, and domain patterns BEFORE generating the plan.

## What to Load

| Query | Group IDs | Purpose |
|-------|-----------|---------|
| Similar features built previously | `guardkit__feature_specs` | Avoid repeating approaches that failed |
| Architecture context | `architecture_decisions`, `guardkit__project_architecture` | Ensure feature fits current architecture |
| Past outcomes from similar work | `guardkit__task_outcomes` | Learn from what worked/didn't |

## Acceptance Criteria

- [ ] AC-1: `/feature-plan` spec (installer/core/commands/feature-plan.md) includes MCP context loading before plan generation
- [ ] AC-2: Loaded context influences feature scope, risk assessment, and architecture decisions
- [ ] AC-3: Existing post-generation seeding preserved (write path still works)
- [ ] AC-4: CLI fallback when MCP not available
- [ ] AC-5: Display: "[Graphiti] Feature context loaded: N items"

## Implementation Notes

- `/feature-plan` already has Graphiti integration points (post-gen seeding) — this adds the pre-gen read path
- Follow MCP-first pattern from TASK-GMR-004
