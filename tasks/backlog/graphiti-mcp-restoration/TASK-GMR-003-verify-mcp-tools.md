---
id: TASK-GMR-003
title: "Verify MCP tools available in Claude Code session"
status: backlog
created: 2026-03-29T12:00:00Z
updated: 2026-03-29T12:00:00Z
priority: high
tags: [graphiti, mcp, verification]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: direct
wave: 1
conductor_workspace: graphiti-mcp-restoration-wave1-3
complexity: 2
depends_on:
  - TASK-GMR-001
---

# Verify MCP Tools Available in Claude Code

## Description

After TASK-GMR-001 restores the MCP configuration, verify that the Graphiti MCP tools are available in a Claude Code session within guardkit.

## Acceptance Criteria

- [ ] AC-1: Open guardkit in VS Code with Claude Code extension
- [ ] AC-2: Confirm `mcp__graphiti__search_nodes` tool is available
- [ ] AC-3: Confirm `mcp__graphiti__search_memory_facts` tool is available
- [ ] AC-4: Confirm `mcp__graphiti__add_memory` tool is available
- [ ] AC-5: Run a test search: `mcp__graphiti__search_nodes(query="quality gates", group_ids=["product_knowledge"])` and verify results returned
- [ ] AC-6: Document any MCP startup errors or tool unavailability issues

## Implementation Notes

- This is a verification task, not code — executed manually in Claude Code
- If MCP server fails to start, check: uv installed, graphiti/mcp_server/ exists, FalkorDB reachable, vLLM reachable
- The MCP server log may appear in VS Code output panel
- Expected tools match those documented in `.claude/rules/graphiti-knowledge-graph.md`
