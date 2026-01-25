# Feature: FastMCP Python Template

## Overview

Create a production-ready `fastmcp-python` template following GuardKit conventions. This template will enable developers to scaffold MCP (Model Context Protocol) servers using FastMCP with all critical production patterns embedded.

## Problem Statement

The current MCP implementation guidance (TASK-REV-MCP) provides excellent technical patterns but:
- Is structured as runtime project documentation, not a GuardKit template
- Missing all 7 required template components (manifest.json, settings.json, agents/, templates/, etc.)
- Cannot be used with `guardkit init fastmcp-python`

## Solution Approach

Create a proper GuardKit template that:
1. Follows `fastapi-python` template structure
2. Embeds all 10 critical MCP production patterns from TASK-REV-MCP
3. Provides code scaffolding via templates with placeholders
4. Includes specialist agents with proper boundaries

## Parent Review

- **Review Task**: TASK-REV-A7F3
- **Review Report**: [.claude/reviews/TASK-REV-A7F3-review-report.md](../../../.claude/reviews/TASK-REV-A7F3-review-report.md)
- **Source Input**: TASK-REV-MCP (10 critical production patterns)

## Template Components

| Component | Files | Status |
|-----------|-------|--------|
| `manifest.json` | 1 | Pending |
| `settings.json` | 1 | Pending |
| `agents/` | 3 | Pending |
| `templates/` | 8 | Pending |
| `.claude/rules/` | 4 | Pending |
| `.claude/CLAUDE.md` | 1 | Pending |
| `CLAUDE.md` | 1 | Pending |
| `README.md` | 1 | Pending |

## Subtask Summary

| ID | Title | Wave | Mode | Status |
|----|-------|------|------|--------|
| TASK-FMT-001 | Create manifest.json | 1 | task-work | Pending |
| TASK-FMT-002 | Create settings.json | 1 | task-work | Pending |
| TASK-FMT-003 | Create fastmcp-specialist agent | 2 | task-work | Pending |
| TASK-FMT-004 | Create fastmcp-testing-specialist agent | 2 | task-work | Pending |
| TASK-FMT-005 | Create code templates | 2 | task-work | Pending |
| TASK-FMT-006 | Create .claude/rules | 2 | task-work | Pending |
| TASK-FMT-007 | Create CLAUDE.md files | 3 | direct | Pending |
| TASK-FMT-008 | Validate template with /template-validate | 3 | direct | Pending |

## 10 Critical MCP Patterns (from TASK-REV-MCP)

These patterns MUST be embedded in agents and templates:

1. **Use FastMCP, Not Custom Server Classes** - FastMCP handles full MCP protocol
2. **Tool Registration in `__main__.py`** - Tools MUST be in module-level `__main__.py`
3. **Logging to stderr** - stdout reserved for MCP protocol
4. **Streaming Tools Two-Layer Architecture** - Wrapper pattern required
5. **Error Handling for Streaming** - Handle `asyncio.CancelledError` properly
6. **MCP Parameter Type Conversion** - All params come as strings
7. **Configuration with Absolute Paths** - `.mcp.json` requires absolute paths
8. **Timestamp Best Practices** - Use `datetime.now(UTC)`
9. **Protocol Testing Commands** - Manual JSON-RPC testing required
10. **Docker Deployment Patterns** - Non-root, slim, PYTHONUNBUFFERED

## Quality Targets

- Template complexity: 5/10
- Quality scores: SOLID 85+, DRY 85+, YAGNI 90+
- Pass `/template-validate` with no errors
- Agent count: 3 (core, testing, optional streaming)
- Template count: 8 (server, tools, resources, tests, config)

## Success Criteria

- [ ] `guardkit init fastmcp-python` works
- [ ] Generated project follows all 10 critical patterns
- [ ] Agents provide actionable guidance during development
- [ ] Code templates include proper placeholders
- [ ] `/template-validate` passes with quality score 8+/10

## Related Documentation

- [Template Philosophy Guide](../../../docs/guides/template-philosophy.md)
- [fastapi-python Template](../../../installer/core/templates/fastapi-python/)
- [TASK-REV-MCP Review Report](../../../.claude/reviews/TASK-REV-MCP-review-report.md)
