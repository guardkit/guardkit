---
id: TASK-GCI-004
title: Document dual-access Graphiti architecture (MCP + Python client)
status: completed
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T12:00:00Z
completed: 2026-03-18T12:00:00Z
priority: medium
tags: [graphiti, documentation, claude-code]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
implementation_mode: direct
wave: 2
complexity: 2
depends_on:
  - TASK-GCI-001
  - TASK-GCI-002
---

# Task: Document dual-access Graphiti architecture (MCP + Python client)

## Description

Create documentation explaining how Graphiti is accessed via two complementary methods: MCP server for Claude Code sessions and Python client for CLI workflows. Cover setup, configuration, isolation, and troubleshooting.

## Deliverables

1. **`docs/guides/graphiti-claude-code-integration.md`** — Main guide covering:
   - Architecture overview (MCP vs Python client, when each is used)
   - Setup steps (prerequisites, `guardkit init --with-mcp`)
   - Configuration files explained (`.mcp.json`, MCP server config, `.guardkit/graphiti.yaml`)
   - Project isolation with shared FalkorDB
   - Group ID namespacing (how prefixing works across both access methods)
   - Troubleshooting common issues
   - Infrastructure topology diagram

2. **Update `.claude/rules/graphiti-knowledge.md`**:
   - Add section about MCP access method
   - Reference the new guide
   - Note that both access methods coexist

3. **Update root `CLAUDE.md`**:
   - Add brief mention of MCP integration option under Graphiti section

## Acceptance Criteria

- [x] Guide covers both MCP and Python client access methods
- [x] Setup instructions are complete and actionable
- [x] Troubleshooting section covers: MCP server won't start, group ID mismatch, embedding dimension issues
- [x] Existing docs updated with cross-references
