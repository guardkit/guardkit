---
id: TASK-GCI-005
title: Create Claude Code rules file template for Graphiti MCP
status: completed
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T12:00:00Z
completed: 2026-03-18T12:00:00Z
priority: low
tags: [graphiti, template, claude-code, installer]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
completed_location: tasks/completed/TASK-GCI-005/
organized_files:
  - TASK-GCI-005.md
---

# Task: Create Claude Code rules file template for Graphiti MCP

## Description

Create a template for `.claude/rules/graphiti-knowledge-graph.md` that `guardkit init --with-mcp` generates. This file instructs Claude Code how to use the Graphiti MCP tools effectively.

## Reference

The agentic-dataset-factory has a working version at:
`.claude/rules/graphiti-knowledge-graph.md`

## Template Requirements

The template should include placeholders for:
- `{{project_id}}` — project identifier
- `{{group_ids}}` — list of project-prefixed group IDs
- `{{falkordb_host}}` — FalkorDB hostname
- `{{falkordb_port}}` — FalkorDB port

### Template Content

1. **Overview** — project has Graphiti MCP server connected to FalkorDB
2. **Critical rule** — always pass group_ids when searching
3. **Group ID reference table** — what each group contains
4. **Available MCP tools** — `mcp__graphiti__search_nodes`, `mcp__graphiti__search_memory_facts`, etc.
5. **Configuration reference** — pointers to `.mcp.json` and `.guardkit/graphiti.yaml`

## Deliverable

- `installer/core/templates/common/claude-rules-graphiti-mcp.md.template`

## Acceptance Criteria

- [x] Template generates valid `.claude/rules/graphiti-knowledge-graph.md`
- [x] Placeholders are replaced correctly during `guardkit init`
- [x] Generated file matches the format used in agentic-dataset-factory
- [x] Group IDs use project-prefixed format (consistent with TASK-GCI-002)
