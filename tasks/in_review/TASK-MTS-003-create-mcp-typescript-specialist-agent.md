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
status: in_review
tags:
- template
- mcp
- typescript
- agent
task_type: feature
title: Create mcp-typescript-specialist agent
updated: 2026-01-28 19:15:00+00:00
wave: 1
---

# Task: Create mcp-typescript-specialist agent

## Description

Create the core MCP TypeScript specialist agent with ALWAYS/NEVER boundaries encoding the 10 critical production patterns. This agent will guide Claude Code when developing MCP servers.

## Reference

Use `installer/core/templates/react-typescript/agents/react-query-specialist.md` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 5.1 for agent specification.

## Acceptance Criteria

- [x] Core file created at `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist.md`
- [x] Extended file created at `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist-ext.md`
- [x] Valid frontmatter with:
  - name: mcp-typescript-specialist
  - description: TypeScript MCP server development specialist
  - tools: [Read, Write, Edit, Bash, Grep]
  - model: haiku
  - stack: [typescript, nodejs, mcp]
  - phase: implementation
  - priority: 8
- [x] ALWAYS boundaries include:
  - Use McpServer class from SDK
  - Register tools BEFORE server.connect()
  - Log to stderr only (console.error)
  - Use Zod for schema validation
  - Return content array with structured responses
  - Use absolute paths in configuration
  - Test with JSON-RPC protocol commands
- [x] NEVER boundaries include:
  - Use console.log() (corrupts protocol)
  - Use raw Server class (use McpServer)
  - Register tools after connect()
  - Skip Zod validation
  - Use relative paths in config
- [x] Quick Start section with minimal server example
- [x] Extended file contains:
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

**Execution Date**: 2026-01-28T19:15:00Z
**Mode**: TDD (--implement-only)
**Duration**: ~5 minutes

### Phase 3: Implementation
- ✅ Core agent file created (188 lines)
- ✅ Extended agent file created (447 lines)
- ✅ All 10 MCP patterns documented
- ✅ ALWAYS boundaries: 7 items
- ✅ NEVER boundaries: 5 items
- ✅ Quick Start: 3 code examples
- ✅ Extended: 6 code patterns, 7 anti-patterns

### Phase 4: Validation
- ✅ Frontmatter validation: PASS (all required fields present)
- ✅ Content validation: PASS (all sections present)
- ✅ Code example validation: PASS (syntactically correct)

### Phase 5: Code Review
- **Quality Score**: 9.4/10 (Excellent)
  - Content Quality: 9.5/10
  - Code Example Quality: 9/10
  - Structure Quality: 10/10
  - Documentation Quality: 9/10
- **Verdict**: APPROVED
- **Issues**: None (minor enhancement suggestions optional)

### Files Created
1. `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist.md`
2. `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist-ext.md`

### State Transition
- From: DESIGN_APPROVED
- To: IN_REVIEW
- Reason: All quality gates passed