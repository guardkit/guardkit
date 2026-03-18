---
id: TASK-GCI-001
title: Add MCP configuration generation to guardkit init
status: in_review
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T00:00:00Z
priority: high
tags: [graphiti, mcp, claude-code, installer]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
implementation_mode: task-work
wave: 1
complexity: 6
depends_on: []
---

# Task: Add MCP configuration generation to guardkit init

## Description

Extend `guardkit init` to optionally generate Claude Code MCP configuration for Graphiti. This enables Claude Code sessions to have direct, interactive access to the project's knowledge graph via MCP tools.

## Reference Implementation

The agentic-dataset-factory project has a working setup. Key reference files:
- `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/.mcp.json`
- `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml`

## Requirements

### New Flag: `--with-mcp`

```bash
guardkit init --with-mcp
guardkit init --copy-graphiti --with-mcp
```

### Files to Generate

1. **`.mcp.json`** — Claude Code MCP server launch configuration
   - Detect Graphiti MCP server installation path (check common locations)
   - Use `uv` as the command runner
   - Reference per-project server config
   - Set environment variables for LLM/embedding endpoints
   - **Merge** into existing `.mcp.json` if present (preserve other MCP servers)

2. **Per-project MCP server config** — `config-{project_id}.yaml`
   - Store at `{graphiti_mcp_server_path}/config/config-{project_id}.yaml`
   - Copy from template, replacing project_id, group_ids, endpoints
   - Use settings from `.guardkit/graphiti.yaml` for consistency

### Path Discovery

The Graphiti MCP server location needs to be discovered. Strategy:
1. Check `GRAPHITI_MCP_PATH` environment variable
2. Check `~/.guardkit/mcp-server-path` config file
3. Prompt user if not found
4. Store discovered path for future use

### Merge Logic for `.mcp.json`

If `.mcp.json` already exists:
- Parse existing JSON
- Add/update the `graphiti` key under `mcpServers`
- Preserve all other MCP server entries
- Write back with consistent formatting

## Acceptance Criteria

- [ ] `guardkit init --with-mcp` generates `.mcp.json` with correct Graphiti MCP config
- [ ] Per-project MCP server config is generated with project-specific settings
- [ ] Existing `.mcp.json` is merged (not overwritten)
- [ ] `--copy-graphiti --with-mcp` inherits all settings correctly
- [ ] Path discovery works via env var, config file, or user prompt
- [ ] Claude Code can connect to Graphiti after running init

## Implementation Notes

- The `.mcp.json` format must match Claude Code's expected schema
- The `command` field should use the absolute path to `uv`
- Environment variables in `.mcp.json` should reference the same endpoints as `.guardkit/graphiti.yaml`
