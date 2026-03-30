---
id: TASK-GMR-002
title: "Reverse anti-MCP instruction in task-work.md"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
priority: high
tags: [graphiti, mcp, task-work, command-spec]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 1
conductor_workspace: graphiti-mcp-restoration-wave1-2
complexity: 2
---

# Reverse Anti-MCP Instruction in task-work.md

## Description

The instruction at `installer/core/commands/task-work.md:1701-1703` explicitly blocks MCP usage:

```
⚠️ IMPORTANT: Graphiti is accessed via the Python client library, NOT via MCP tools.
Do NOT check for MCP tools like mcp__graphiti__search_nodes to determine availability.
Instead, run the Python check script via bash as described below.
```

This instruction was added after MCP was removed from guardkit. It must be reversed to enable the MCP integration path.

## Acceptance Criteria

- [x] AC-1: The anti-MCP instruction at lines 1701-1703 is replaced with MCP-first guidance
- [x] AC-2: New instruction says to prefer MCP tools when available, fall back to CLI wrapper
- [x] AC-3: The rest of Phase 1.7 still documents the CLI wrapper as fallback (don't remove it)
- [x] AC-4: The graphiti-preamble at `installer/core/commands/lib/graphiti-preamble.md` is updated to reflect MCP-first approach

## Expected New Instruction

```
⚠️ IMPORTANT: Prefer MCP tools (mcp__graphiti__search_nodes, mcp__graphiti__search_memory_facts)
when available in the current session. If MCP tools are not available, fall back to the Python
check script via bash as described below.
```

## Implementation Notes

- This is a documentation/spec change — modifying markdown command specifications
- The CLI wrapper code itself doesn't change (it stays as fallback)
- Also update the graphiti-knowledge-graph.md rule if it references the old approach
