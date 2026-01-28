---
complexity: 4
conductor_workspace: mcp-ts-wave1-3
created: 2026-01-24 16:45:00+00:00
dependencies: []
feature_id: FEAT-MTS
id: TASK-MTS-003
implementation_mode: task-work
parallel_group: wave1
parent_review: TASK-REV-4371
priority: high
status: design_approved
tags:
- template
- mcp
- typescript
- agent
task_type: feature
title: Create mcp-typescript-specialist agent
updated: 2026-01-24 16:45:00+00:00
wave: 1
---

# Task: Create mcp-typescript-specialist agent

## Description

Create the core MCP TypeScript specialist agent with ALWAYS/NEVER boundaries encoding the 10 critical production patterns. This agent will guide Claude Code when developing MCP servers.

## Reference

Use `installer/core/templates/react-typescript/agents/react-query-specialist.md` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 5.1 for agent specification.

## Acceptance Criteria

- [ ] Core file created at `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist.md`
- [ ] Extended file created at `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist-ext.md`
- [ ] Valid frontmatter with:
  - name: mcp-typescript-specialist
  - description: TypeScript MCP server development specialist
  - tools: [Read, Write, Edit, Bash, Grep]
  - model: haiku
  - stack: [typescript, nodejs, mcp]
  - phase: implementation
  - priority: 8
- [ ] ALWAYS boundaries include:
  - Use McpServer class from SDK
  - Register tools BEFORE server.connect()
  - Log to stderr only (console.error)
  - Use Zod for schema validation
  - Return content array with structured responses
  - Use absolute paths in configuration
  - Test with JSON-RPC protocol commands
- [ ] NEVER boundaries include:
  - Use console.log() (corrupts protocol)
  - Use raw Server class (use McpServer)
  - Register tools after connect()
  - Skip Zod validation
  - Use relative paths in config
- [ ] Quick Start section with minimal server example
- [ ] Extended file contains:
  - Detailed code examples
  - Best practices
  - Anti-patterns
  - Troubleshooting

## Agent Structure

```markdown
---
name: mcp-typescript-specialist
description: TypeScript MCP server development specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "MCP patterns are well-documented. Haiku provides fast, cost-effective development."

stack: [typescript, nodejs, mcp]
phase: implementation
capabilities:
  - MCP server setup and configuration
  - Tool, resource, and prompt registration
  - Zod schema validation patterns
  - Protocol testing and debugging
keywords: [mcp, typescript, model-context-protocol, claude-code, zod, server]

collaborates_with:
  - mcp-testing-specialist
priority: 8
---

## Role
[Agent role description]

## Boundaries
### ALWAYS
[Critical patterns]

### NEVER
[Anti-patterns]

## Quick Start
[Code examples]

## Extended Reference
See agents/mcp-typescript-specialist-ext.md
```

## Test Execution Log

[Automatically populated by /task-work]