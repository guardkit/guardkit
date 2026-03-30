---
id: TASK-GMR-011
title: "Add .mcp.json to guardkit init project setup"
status: completed
created: 2026-03-30T09:00:00Z
updated: 2026-03-30T11:05:00Z
completed: 2026-03-30T11:05:00Z
completed_location: tasks/completed/TASK-GMR-011/
priority: high
tags: [graphiti, mcp, installer, init-project]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 1
conductor_workspace: graphiti-mcp-restoration-wave1-4
complexity: 3
---

# Add .mcp.json to guardkit init Project Setup

## Description

`guardkit init` (via `installer/scripts/init-project.sh`) copies `.guardkit/graphiti.yaml` for the Python client but does NOT copy `.mcp.json` for the MCP server. Every project using GuardKit needs MCP configured so Claude Code commands can query Graphiti natively.

The init script already has the pattern: `copy_graphiti_config()` discovers `graphiti.yaml` from parent directories and copies it with the project_id replaced. The same approach should apply to `.mcp.json`.

## Current Behaviour

```bash
guardkit init my-project --copy-graphiti
# ✅ Copies .guardkit/graphiti.yaml (Python client config)
# ❌ Does NOT copy .mcp.json (MCP server config)
```

## Expected Behaviour

```bash
guardkit init my-project --copy-graphiti
# ✅ Copies .guardkit/graphiti.yaml (Python client config)
# ✅ Copies .mcp.json (MCP server config)
```

Or without `--copy-graphiti`:

```bash
guardkit init my-project
# ✅ Writes minimal .guardkit/graphiti.yaml with project_id
# ✅ Copies .mcp.json from guardkit source (if discoverable)
```

## Acceptance Criteria

- [x] AC-1: `init-project.sh` copies `.mcp.json` alongside `graphiti.yaml` during project init
- [x] AC-2: Auto-discovery walks up from parent directories to find source `.mcp.json` (same pattern as `find_source_graphiti_config`)
- [x] AC-3: If no source `.mcp.json` found, skip gracefully with warning (not an error)
- [x] AC-4: `.mcp.json` is NOT project-specific (no project_id replacement needed — same MCP server config works for all projects)
- [x] AC-5: If `.mcp.json` already exists in target project, don't overwrite (warn instead)
- [x] AC-6: Works with `--copy-graphiti` flag and also with `--copy-graphiti PATH`

## Implementation Notes

- File: `installer/scripts/init-project.sh`
- Reference: `copy_graphiti_config()` at line 96 and `find_source_graphiti_config()` at line 75
- The `.mcp.json` is identical across all projects (same MCP server, same endpoints) — no per-project customisation needed
- Unlike `graphiti.yaml` which needs `project_id` replaced, `.mcp.json` is a straight copy
- The MCP server's `config-guardkit.yaml` uses group_id namespacing (`{project_id}__`) to isolate project data, so sharing the same MCP config across projects is safe
