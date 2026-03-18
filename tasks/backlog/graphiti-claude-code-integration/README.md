# Feature: Graphiti Claude Code Integration

**Feature ID**: FEAT-GCI
**Parent Review**: TASK-REV-C166
**Status**: Backlog
**Total Tasks**: 5
**Estimated Effort**: 4-5 days

## Problem Statement

GuardKit uses Graphiti via a Python client library for CLI workflows, but Claude Code sessions have no direct access to the knowledge graph. The agentic-dataset-factory project demonstrates a working integration using the Graphiti MCP server, enabling Claude Code to interactively search and add knowledge during conversations.

## Solution Approach

Enable both access methods in any GuardKit-enabled project:
- **MCP server** for Claude Code interactive sessions
- **Python client** for CLI workflows (already implemented)

This requires configuration generation during `guardkit init`, consistent group ID namespacing, and proper documentation.

## Tasks

| ID | Title | Wave | Complexity | Mode | Depends On |
|----|-------|------|------------|------|------------|
| TASK-GCI-001 | Add MCP config generation to `guardkit init` | 1 | 6 | task-work | — |
| TASK-GCI-002 | Fix group ID isolation (MCP vs Python client) | 1 | 4 | task-work | — |
| TASK-GCI-003 | Align embedding dimensions | 2 | 3 | task-work | GCI-001 |
| TASK-GCI-004 | Document dual-access architecture | 2 | 2 | direct | GCI-001, GCI-002 |
| TASK-GCI-005 | Create Claude Code rules file template | 1 | 2 | direct | — |
