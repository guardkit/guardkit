---
complexity: 3
conductor_workspace: null
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-008
feature_id: FEAT-MTS
id: TASK-MTS-010
implementation_mode: task-work
parallel_group: wave4
parent_review: TASK-REV-4371
priority: medium
status: in_review
tags:
- template
- mcp
- typescript
- documentation
task_type: documentation
title: Create CLAUDE.md files
status: in_review
task_type: documentation
created: 2026-01-24 16:45:00+00:00
updated: 2026-01-24 16:45:00+00:00
priority: medium
tags:
- template
- mcp
- typescript
- documentation
complexity: 3
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 4
parallel_group: wave4
implementation_mode: task-work
conductor_workspace: null
dependencies:
- TASK-MTS-008
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4048
  base_branch: main
  started_at: '2026-01-28T19:14:01.287723'
  last_updated: '2026-01-28T19:23:33.133932'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-28T19:14:01.287723'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create CLAUDE.md files

## Description

Create the CLAUDE.md documentation files for the MCP TypeScript template. These provide Claude Code with context when working in projects using this template.

## Reference

Use `installer/core/templates/react-typescript/CLAUDE.md` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` for MCP-specific guidance.

## Deliverables

### 1. CLAUDE.md (Top-level)

Main project guidance file at template root.

```markdown
# MCP TypeScript Server

## Overview

This is an MCP (Model Context Protocol) server built with TypeScript using the official `@modelcontextprotocol/sdk`.

## Critical Rules

### Logging
**NEVER use console.log()** - It corrupts the MCP protocol.
Always use `console.error()` for all logging.

### Tool Registration
Register all tools, resources, and prompts **BEFORE** calling `server.connect()`.

### Configuration
Use **ABSOLUTE PATHS** in Claude Desktop configuration.

## Commands

\`\`\`bash
# Development
npm run dev          # Run with tsx watch

# Testing
npm test             # Run unit tests
npm run test:protocol # Run protocol tests

# Build
npm run build        # Build for production
npm start            # Run production build
\`\`\`

## Project Structure

\`\`\`
src/
├── index.ts         # Server entry point
├── tools/           # Tool implementations
├── resources/       # Resource providers
└── prompts/         # Prompt templates

tests/
├── unit/            # Vitest unit tests
└── protocol/        # JSON-RPC protocol tests
\`\`\`

## Adding a New Tool

1. Create implementation in `src/tools/my-tool.ts`
2. Register in `src/index.ts` BEFORE connect()
3. Add tests in `tests/unit/my-tool.test.ts`
4. Run protocol tests to verify

## Quality Gates

- ✅ All tests pass
- ✅ No console.log statements
- ✅ Protocol tests succeed
- ✅ Coverage ≥80%
```

### 2. .claude/CLAUDE.md (Nested)

Nested guidance file with more technical details.

```markdown
# MCP TypeScript Template Context

## Template Information

- **Template**: mcp-typescript
- **SDK**: @modelcontextprotocol/sdk
- **Language**: TypeScript 5.0+
- **Runtime**: Node.js 20+

## 10 Critical MCP Patterns

1. **Use McpServer** - Not raw Server class
2. **Register before connect()** - Tool order matters
3. **stderr logging** - console.error() only
4. **Streaming two-layer** - Implementation + wrapper
5. **Error handling** - Try/catch in streams
6. **Zod validation** - Type-safe schemas
7. **Absolute paths** - In all configuration
8. **ISO timestamps** - new Date().toISOString()
9. **Protocol testing** - JSON-RPC manual tests
10. **Docker non-root** - Security best practice

## Testing Strategy

### Unit Tests (Vitest)
Test tool implementations independently.

### Protocol Tests
Test JSON-RPC communication:
\`\`\`bash
./tests/protocol/test-protocol.sh
\`\`\`

## Troubleshooting

### Tools not discovered
- Check registration is BEFORE connect()
- Verify using McpServer class

### Protocol corruption
- Remove ALL console.log statements
- Check for third-party libs using stdout

### Type errors
- Ensure Zod schema matches function signature
- Check imports use .js extension

## Extended Rules

See `.claude/rules/` for path-specific guidance:
- `mcp-patterns.md` - Core development patterns
- `testing.md` - Testing patterns
- `transport.md` - Transport configuration
- `configuration.md` - Config file patterns
```

### 3. README.md (Template README)

Documentation for the template itself.

```markdown
# MCP TypeScript Template

Production-ready template for building MCP servers with TypeScript.

## Features

- Official `@modelcontextprotocol/sdk`
- Zod schema validation
- Vitest unit testing
- Protocol testing scripts
- Docker deployment ready
- Claude Desktop configuration

## Quick Start

\`\`\`bash
guardkit init mcp-typescript
cd my-mcp-server
npm install
npm run dev
\`\`\`

## What's Included

| Component | Description |
|-----------|-------------|
| Server entry | src/index.ts with tool registration |
| Tool template | Type-safe tool implementation |
| Resource template | Static and dynamic resources |
| Prompt template | With argument completion |
| Test templates | Vitest + protocol tests |
| Docker config | Multi-stage build |

## Configuration

### Claude Desktop

\`\`\`json
{
  "mcpServers": {
    "my-server": {
      "command": "/absolute/path/to/node",
      "args": ["--import", "tsx", "/absolute/path/to/src/index.ts"],
      "cwd": "/absolute/path/to/project"
    }
  }
}
\`\`\`

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [GuardKit Documentation](https://guardkit.dev)
```

## Acceptance Criteria

- [x] CLAUDE.md created at template root with critical rules
- [x] .claude/CLAUDE.md created with 10 patterns and troubleshooting
- [x] README.md created with quick start and configuration
- [x] All files follow GuardKit documentation conventions
- [x] No emojis unless explicitly requested
- [x] All code examples are correct and tested

## Test Execution Log

**Executed**: 2026-01-28
**Mode**: TDD (--mode=tdd)
**Workflow**: implement-only (--implement-only)

### TDD RED Phase
- Created 49 tests in `tests/templates/mcp-typescript/test_claude_md_files.py`
- Tests covered: file existence (3), root CLAUDE.md content (13), nested CLAUDE.md content (10), README content (10), quality (3), conventions (3)
- Initial results: 3 FAILED (file existence), 46 SKIPPED (content)

### TDD GREEN Phase
- Created 3 documentation files:
  - `installer/core/templates/mcp-typescript/CLAUDE.md` (155 lines)
  - `installer/core/templates/mcp-typescript/.claude/CLAUDE.md` (108 lines)
  - `installer/core/templates/mcp-typescript/README.md` (116 lines)
- All 49 tests pass (100%)

### Code Review
- **Score**: 92/100
- **Status**: APPROVED
- **Key Strengths**: Complete deliverables, accurate MCP patterns, critical rules prominence, comprehensive testing, GuardKit conventions followed
- **Minor Issues**: Heading hierarchy, path examples consistency (cosmetic only)