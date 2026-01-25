# Feature: MCP TypeScript Template

**Feature ID**: `FEAT-4048`
**Feature File**: [.guardkit/features/FEAT-4048.yaml](../../../.guardkit/features/FEAT-4048.yaml)
**AutoBuild Ready**: `/feature-build FEAT-4048`

## Overview

Create a production-ready `mcp-typescript` GuardKit template for building MCP servers using the official `@modelcontextprotocol/sdk`. This template complements the `fastmcp-python` template by providing equivalent TypeScript patterns for all 10 critical MCP production patterns.

## Problem Statement

GuardKit users working with TypeScript need a template for building MCP servers that:
- Follows the official TypeScript MCP SDK patterns
- Implements all 10 critical production patterns (stderr logging, tool registration, streaming, etc.)
- Provides specialist agents with ALWAYS/NEVER boundaries
- Includes code templates with proper placeholders
- Supports testing (Vitest, protocol tests) and Docker deployment

## Solution Approach

Create a complete GuardKit template following the established conventions from `react-typescript` and `fastapi-python` templates, with MCP-specific patterns derived from the architectural review (TASK-REV-4371).

**Template Name**: `mcp-typescript`

**Key Components**:
| Component | Count | Description |
|-----------|-------|-------------|
| manifest.json | 1 | Template metadata with MCP patterns |
| settings.json | 1 | Naming conventions for tools/resources |
| Agents | 2 | Core specialist + testing specialist |
| Code Templates | 8 | Server, tools, resources, config, tests |
| Rules | 4 | MCP patterns, testing, transport, config |
| CLAUDE.md | 2 | Top-level + nested guidance |

## Subtask Summary

| Task ID | Title | Wave | Mode | Dependencies |
|---------|-------|------|------|--------------|
| MTS-001 | Create manifest.json | 1 | task-work | None |
| MTS-002 | Create settings.json | 1 | task-work | None |
| MTS-003 | Create mcp-typescript-specialist agent | 1 | task-work | None |
| MTS-004 | Create server/index.ts.template | 2 | task-work | MTS-001 |
| MTS-005 | Create tools/tool.ts.template | 2 | task-work | MTS-001 |
| MTS-006 | Create config templates | 2 | task-work | MTS-001 |
| MTS-007 | Create mcp-testing-specialist agent | 3 | task-work | MTS-003 |
| MTS-008 | Create .claude/rules/ files | 3 | task-work | MTS-003 |
| MTS-009 | Create test templates | 3 | task-work | MTS-005 |
| MTS-010 | Create CLAUDE.md files | 4 | task-work | MTS-008 |
| MTS-011 | Validate template | 4 | task-work | All |

## Success Criteria

- [ ] Template installs with `guardkit init mcp-typescript`
- [ ] All 10 critical MCP patterns implemented
- [ ] Agents provide clear ALWAYS/NEVER boundaries
- [ ] Code templates have proper placeholders
- [ ] Tests pass with `/template-validate`
- [ ] Documentation complete and accurate

## Technical Context

### TypeScript MCP SDK Patterns

```typescript
// Server creation
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
const server = new McpServer({ name: 'my-server', version: '1.0.0' });

// Tool registration (BEFORE connect)
server.registerTool('my-tool', {
    inputSchema: { param: z.string() }
}, async ({ param }) => ({
    content: [{ type: 'text', text: result }]
}));

// Transport connection
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Critical Pattern: stderr Logging

```typescript
// CORRECT - use stderr
console.error('Server started');

// WRONG - corrupts MCP protocol
console.log('message');
```

## Related Tasks

- **TASK-REV-4371**: Design review (parent)
- **TASK-REV-A7F3**: MCP Template Consistency Review
- **TASK-REV-A7F9**: Gap Analysis (GAP-8)
- **fastmcp-python-template**: Parallel Python implementation

## References

- [Review Report](.claude/reviews/TASK-REV-4371-review-report.md)
- [TypeScript MCP SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Best Practices 2025](docs/research/mcp-server-best-practices-2025.md)
- [GuardKit Template Philosophy](docs/guides/template-philosophy.md)
