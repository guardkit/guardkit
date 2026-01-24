---
id: TASK-MTS-008
title: Create .claude/rules/ files
status: backlog
task_type: documentation
created: 2026-01-24T16:45:00Z
updated: 2026-01-24T16:45:00Z
priority: medium
tags: [template, mcp, typescript, rules]
complexity: 4
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 3
parallel_group: wave3
implementation_mode: task-work
conductor_workspace: mcp-ts-wave3-2
dependencies:
  - TASK-MTS-003  # Core specialist for patterns
---

# Task: Create .claude/rules/ files

## Description

Create Claude Code rules files for the MCP TypeScript template. These provide path-specific guidance loaded conditionally based on file patterns.

## Reference

Use `installer/core/templates/react-typescript/.claude/rules/` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` for MCP-specific patterns.

## Deliverables

### 1. .claude/rules/mcp-patterns.md

Core MCP development patterns (loaded for all src/**/*.ts files)

```markdown
---
paths: src/**/*.ts
---

# MCP Development Patterns

## Critical Rules

### 1. Server Initialization
- Use McpServer class, not raw Server
- Register all tools/resources/prompts BEFORE connect()

### 2. Logging
- ALWAYS use console.error() for all logging
- NEVER use console.log() - corrupts MCP protocol

### 3. Tool Registration
[Pattern examples]

### 4. Response Format
[Content array examples]

### 5. Type Safety
[Zod schema examples]
```

### 2. .claude/rules/testing.md

Testing patterns (loaded for tests/**/*.ts files)

```markdown
---
paths: tests/**/*.ts, **/*.test.ts
---

# MCP Testing Patterns

## Unit Testing with Vitest

### Tool Implementation Tests
[Examples]

### Schema Validation Tests
[Examples]

## Protocol Testing

### JSON-RPC Test Script
[Examples]

### Common Test Cases
[Examples]
```

### 3. .claude/rules/transport.md

Transport selection and configuration (loaded for config and server files)

```markdown
---
paths: src/index.ts, config/**/*
---

# MCP Transport Configuration

## Transport Options

### STDIO (Default)
- Best for: Claude Desktop, local development
- Configuration pattern

### Streamable HTTP
- Best for: Production, networked servers
- Express/Hono middleware patterns

## Configuration Patterns

### Claude Desktop
- ABSOLUTE paths required
- Environment variables
```

### 4. .claude/rules/configuration.md

Configuration patterns (loaded for config files)

```markdown
---
paths: config/**/*.json, *.json, package.json, tsconfig.json
---

# MCP Configuration Patterns

## package.json
- Required scripts
- Dependencies

## tsconfig.json
- Module settings for ESM
- Path aliases

## Claude Desktop Config
- ABSOLUTE PATH requirement (critical!)
- Environment variables
```

## Acceptance Criteria

- [ ] mcp-patterns.md created with path: src/**/*.ts
- [ ] testing.md created with path: tests/**/*.ts, **/*.test.ts
- [ ] transport.md created with path: src/index.ts, config/**/*
- [ ] configuration.md created with path: config/**/*.json
- [ ] All files have valid YAML frontmatter with paths
- [ ] All files document critical patterns from review report
- [ ] All files follow GuardKit rules structure conventions

## Test Execution Log

[Automatically populated by /task-work]
