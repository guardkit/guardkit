---
id: TASK-GMR-001
title: "Restore Graphiti MCP configuration to guardkit"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria met, config verified identical to reference"
completed_location: tasks/completed/TASK-GMR-001/
priority: high
tags: [graphiti, mcp, configuration]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 1
conductor_workspace: graphiti-mcp-restoration-wave1-1
complexity: 2
---

# Restore Graphiti MCP Configuration

## Description

Copy the proven Graphiti MCP server configuration from `agentic-dataset-factory/.mcp.json` into guardkit's `.mcp.json`. The MCP server at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/` is already functional — this task only restores the configuration pointer.

## Reference Configuration

Source: `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/.mcp.json`

The configuration uses:
- `uv` to run the MCP server (`/opt/homebrew/bin/uv`)
- Server at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/`
- Config: `config/config-guardkit.yaml`
- FalkorDB: `whitestocks:6379`
- vLLM embedding: `promaxgb10-41b1:8001`
- vLLM LLM: `promaxgb10-41b1:8000`

## Acceptance Criteria

- [x] AC-1: `.mcp.json` in guardkit root contains `graphiti` MCP server entry
- [x] AC-2: Configuration points to existing `graphiti/mcp_server/` and `config-guardkit.yaml`
- [x] AC-3: Environment variables set correctly (OPENAI_API_KEY, LLM_API_URL, EMBEDDING_API_URL, EMBEDDING_DIM)
- [x] AC-4: No other existing MCP server entries are disturbed

## Implementation Notes

- guardkit's current `.mcp.json` is `{ "mcpServers": {} }` — it's empty
- The graphiti MCP server entry should be identical to the agentic-dataset-factory version
- This is a configuration-only change — no code modifications
