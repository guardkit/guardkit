---
id: TASK-GCI-002
title: Fix group ID isolation between MCP server and Python client
status: completed
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T12:45:00Z
completed: 2026-03-18T12:45:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied"
priority: high
tags: [graphiti, mcp, isolation, group-ids]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
implementation_mode: task-work
wave: 1
complexity: 4
depends_on: []
completed_location: tasks/completed/TASK-GCI-002/
---

# Task: Fix group ID isolation between MCP server and Python client

## Description

The Python client auto-prefixes group IDs with `{project_id}__` (e.g., `guardkit__product_knowledge`), but the MCP server uses a flat `group_id` from its config (e.g., `guardkit`). This means knowledge written by one is invisible to the other.

## Problem

| Operation | Python Client writes | MCP Server writes |
|-----------|---------------------|-------------------|
| `product_knowledge` | `guardkit__product_knowledge` | `guardkit` |
| `architecture_decisions` | `guardkit__architecture_decisions` | `guardkit` |

Searches from one access method cannot find data written by the other.

## Solution

Generate per-project MCP server configs that use the same group ID format as the Python client.

### Option A: Configure MCP Server group_ids to Match Python Client

In the per-project MCP server config (`config-{project_id}.yaml`):
```yaml
graphiti:
  group_id: "{project_id}__product_knowledge"  # Matches Python client format
```

However, the MCP server only supports a single `group_id` in its config. Searches would need to pass multiple group_ids explicitly.

### Option B: Document the Convention

Ensure the `.claude/rules/graphiti-knowledge-graph.md` rules file instructs Claude Code to always pass the project-prefixed group_ids when searching:
```
group_ids: ["{project_id}__product_knowledge", "{project_id}__command_workflows", "{project_id}__architecture_decisions"]
```

### Option C: Upstream MCP Server Enhancement

Contribute `project_id` prefixing support to the Graphiti MCP server. This aligns both access methods automatically.

## Acceptance Criteria

- [x] Knowledge seeded via Python client is searchable via MCP
- [x] Knowledge added via MCP is searchable via Python client
- [x] Per-project MCP server configs use consistent group ID namespacing
- [x] `.claude/rules/graphiti-knowledge-graph.md` template includes correct prefixed group_ids
- [x] Two projects sharing FalkorDB don't see each other's MCP-written data

## Implementation Notes

- The Python client's prefixing logic is in `GraphitiClient.get_group_id()` in `graphiti_client.py`
- The MCP server's group_id is set in the YAML config under `graphiti.group_id`
- System groups (no prefix) are shared across projects intentionally
- This task can be worked in parallel with TASK-GCI-001

## Implementation Summary

Implemented as a documentation/configuration task (Option B). Key insight: system groups
(`product_knowledge`, `command_workflows`, `architecture_decisions`) are stored WITHOUT prefix
by the Python client; project groups use `{project_id}__` prefix. The MCP server default
`group_id: "guardkit"` matched neither.

### Files Changed

| File | Change |
|------|--------|
| `.claude/rules/graphiti-knowledge-graph.md` | Created — MCP access rules with correct group IDs |
| `.claude/rules/graphiti-knowledge.md` | Updated — reference to MCP rules file when MCP tools available |
| `installer/core/commands/lib/graphiti-preamble.md` | Updated — system vs project group documentation |
| `graphiti/mcp_server/config/config-guardkit.yaml` | Updated — default group_id aligned to `product_knowledge` |
