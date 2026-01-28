---
complexity: 4
conductor_workspace: mcp-ts-wave3-1
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-003
feature_id: FEAT-MTS
id: TASK-MTS-007
implementation_mode: task-work
parallel_group: wave3
parent_review: TASK-REV-4371
priority: medium
status: design_approved
tags:
- template
- mcp
- typescript
- agent
- testing
task_type: feature
title: Create mcp-testing-specialist agent
updated: 2026-01-24 16:45:00+00:00
wave: 3
---

# Task: Create mcp-testing-specialist agent

## Description

Create a specialized agent for MCP server testing, covering unit tests (Vitest), protocol tests (JSON-RPC), and integration testing patterns.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 7 for testing strategy.

## Acceptance Criteria

- [ ] Core file created at `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist.md`
- [ ] Extended file created at `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist-ext.md`
- [ ] Valid frontmatter with:
  - name: mcp-testing-specialist
  - description: MCP server testing specialist
  - tools: [Read, Write, Edit, Bash, Grep]
  - model: haiku
  - stack: [typescript, vitest, mcp]
  - phase: testing
  - priority: 7
- [ ] Testing pyramid documented:
  - Unit tests (Vitest)
  - Protocol tests (JSON-RPC manual)
  - Integration tests (MCP Inspector)
- [ ] ALWAYS boundaries:
  - Test tool implementations independently
  - Test with JSON-RPC protocol commands
  - Mock external dependencies
  - Verify stderr logging doesn't break tests
- [ ] NEVER boundaries:
  - Assume unit tests verify protocol compliance
  - Skip protocol testing
  - Use console.log in test files (affects STDIO)

## Agent Structure

```markdown
---
name: mcp-testing-specialist
description: MCP server testing specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

stack: [typescript, vitest, mcp]
phase: testing
capabilities:
  - Unit testing with Vitest
  - Protocol testing with JSON-RPC
  - Integration testing patterns
  - Coverage analysis
keywords: [mcp, testing, vitest, protocol, json-rpc]

collaborates_with:
  - mcp-typescript-specialist
priority: 7
---

## Role
You are an MCP testing specialist focusing on comprehensive test coverage for MCP servers.

## Test Pyramid

### Level 1: Unit Tests (Vitest)
- Test tool implementation functions independently
- Test schema validation
- Mock external dependencies

### Level 2: Protocol Tests (JSON-RPC)
- Test initialize handshake
- Test tools/list endpoint
- Test tools/call with various inputs
- Test error responses

### Level 3: Integration Tests
- Test with MCP Inspector
- Test Claude Desktop connection
- Test end-to-end workflows

## Boundaries

### ALWAYS
[Testing patterns]

### NEVER
[Anti-patterns]

## Extended Reference
See agents/mcp-testing-specialist-ext.md
```

## Test Execution Log

[Automatically populated by /task-work]