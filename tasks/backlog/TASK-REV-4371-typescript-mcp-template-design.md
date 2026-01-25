---
id: TASK-REV-4371
title: Design TypeScript MCP Template to Complement FastMCP Python
status: review_complete
created: 2026-01-24T10:00:00Z
updated: 2026-01-24T16:30:00Z
priority: medium
tags: [architecture-review, mcp, typescript, template, design]
task_type: review
decision_required: true
complexity: 6
related_tasks:
  - TASK-REV-A7F3  # MCP Template Consistency Review
  - TASK-REV-A7F9  # Gap Analysis Report
  - TASK-FMT-001   # FastMCP Python manifest.json (reference)
review_results:
  mode: architectural
  depth: standard
  score: 88
  findings_count: 10
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-4371-review-report.md
  completed_at: 2026-01-24T16:30:00Z
  implementation_created:
    feature_folder: tasks/backlog/mcp-typescript-template/
    subtask_count: 11
    wave_count: 4
    created_at: 2026-01-24T16:45:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Design TypeScript MCP Template to Complement FastMCP Python

## Description

Design a TypeScript MCP project template (`mcp-typescript`) that mirrors the planned `fastmcp-python` template structure while leveraging TypeScript/Node.js ecosystem patterns. This review task will analyze the official TypeScript MCP SDK, identify equivalent patterns to the 10 critical Python MCP patterns, and produce a template specification following GuardKit conventions.

## Background

### Context from Gap Analysis (TASK-REV-A7F9)

The gap analysis report identified this as GAP-8:

> **GAP-8: TypeScript MCP Specialist Agent**
>
> Research Content (Section: Next Steps):
> > Create TypeScript MCP Specialist Agent: Mirror the Python patterns in a TypeScript-focused agent
>
> Current Coverage: Out of scope for `fastmcp-python` template
> Impact: No immediate impact on Python template
> Recommendation: Track as future work (separate template)
> Categorization: **NICE-TO-HAVE** - Future template

### Why TypeScript?

1. **Official SDK Support**: MCP has official TypeScript SDK (`@modelcontextprotocol/sdk`)
2. **Ecosystem Parity**: Many Claude Code users work in TypeScript
3. **Template Consistency**: GuardKit has `react-typescript` but no MCP TypeScript template
4. **Claude Desktop**: TypeScript MCP servers work seamlessly with Claude Desktop

## Review Objectives

1. **Analyze TypeScript MCP SDK** - Understand official patterns and APIs
2. **Map Python Patterns to TypeScript** - Create equivalent TypeScript patterns for each of the 10 critical MCP patterns
3. **Define Template Structure** - Specify all GuardKit template components
4. **Identify TypeScript-Specific Patterns** - Capture any TypeScript-only patterns not in Python
5. **Produce Implementation Plan** - Create subtask breakdown for template implementation

## Scope

### In Scope

- TypeScript MCP SDK analysis (`@modelcontextprotocol/sdk`)
- Template structure specification (manifest.json, settings.json, agents/, templates/, rules/)
- Pattern mapping: Python to TypeScript equivalents
- Code template definitions with placeholders
- Agent specification with ALWAYS/NEVER boundaries
- Testing strategy (Jest/Vitest, protocol testing)
- Build and deployment patterns (esbuild, Docker)

### Out of Scope

- Actual template implementation (covered by follow-up implementation tasks)
- Monorepo patterns combining Python and TypeScript MCP servers
- Browser-based MCP clients (server-side only)
- Deno or Bun runtimes (Node.js focus)

## Analysis Framework

### 1. SDK Comparison

| Aspect | FastMCP (Python) | @modelcontextprotocol/sdk (TypeScript) |
|--------|------------------|----------------------------------------|
| Server Creation | `FastMCP("name")` | TBD |
| Tool Registration | `@mcp.tool()` decorator | TBD |
| Resource Definition | `@mcp.resource()` decorator | TBD |
| Streaming | Two-layer wrapper pattern | TBD |
| Transport | STDIO, HTTP | TBD |
| Logging | stderr | TBD |

### 2. Pattern Mapping Template

For each of the 10 critical Python MCP patterns, analyze:

| Pattern | Python Implementation | TypeScript Equivalent | Notes |
|---------|----------------------|----------------------|-------|
| 1. Use SDK, not custom classes | FastMCP handles protocol | TBD | |
| 2. Tool registration location | `__main__.py` | TBD (index.ts?) | |
| 3. Logging to stderr | `logging.StreamHandler(sys.stderr)` | TBD | |
| 4. Streaming two-layer | Wrapper pattern | TBD | |
| 5. Error handling streaming | `asyncio.CancelledError` | TBD | |
| 6. Parameter type conversion | All strings | TBD | |
| 7. Absolute path configuration | `.mcp.json` paths | TBD | |
| 8. Timestamp handling | `datetime.now(UTC)` | TBD | |
| 9. Protocol testing | JSON-RPC manual test | TBD | |
| 10. Docker deployment | Non-root, slim | TBD | |

### 3. Template Components

Specify these GuardKit template components:

| Component | Count | Status |
|-----------|-------|--------|
| `manifest.json` | 1 | TBD |
| `settings.json` | 1 | TBD |
| `agents/` | 2-3 | TBD |
| `templates/` | 6-8 | TBD |
| `.claude/rules/` | 4-5 | TBD |
| `.claude/CLAUDE.md` | 1 | TBD |
| `CLAUDE.md` | 1 | TBD |
| `README.md` | 1 | TBD |

## Research Sources

### Primary Sources

1. **Official TypeScript MCP SDK**: https://github.com/modelcontextprotocol/typescript-sdk
2. **MCP Protocol Specification**: https://spec.modelcontextprotocol.io/
3. **MCP Examples Repository**: https://github.com/modelcontextprotocol/servers

### Reference Templates

1. **fastmcp-python** (planned): `tasks/backlog/fastmcp-python-template/`
2. **react-typescript**: `installer/core/templates/react-typescript/`
3. **fastapi-python**: `installer/core/templates/fastapi-python/`

### Related Reviews

1. **TASK-REV-A7F3**: MCP Template Consistency Review
2. **TASK-REV-A7F9**: Gap Analysis Report
3. **TASK-REV-MCP**: MCP Implementation Report (10 critical patterns)

## Acceptance Criteria

- [ ] TypeScript MCP SDK analyzed with documented patterns
- [ ] All 10 Python MCP patterns mapped to TypeScript equivalents
- [ ] Template structure fully specified (manifest, settings, agents, templates, rules)
- [ ] Code templates defined with placeholders
- [ ] Agent boundaries (ALWAYS/NEVER) specified
- [ ] Testing strategy defined (unit, integration, protocol)
- [ ] Build/deployment patterns documented
- [ ] Subtask breakdown created for implementation
- [ ] Implementation timeline estimated

## Deliverables

### Primary Deliverable

**Review Report**: `.claude/reviews/TASK-REV-4371-review-report.md`

Contents:
1. Executive Summary
2. TypeScript MCP SDK Analysis
3. Pattern Mapping (10 patterns)
4. Template Structure Specification
5. TypeScript-Specific Patterns
6. Testing Strategy
7. Implementation Subtask Breakdown
8. Recommendations

### Secondary Deliverables (if [I]mplement chosen)

**Feature Subfolder**: `tasks/backlog/mcp-typescript-template/`

Contents:
- README.md (feature overview)
- IMPLEMENTATION-GUIDE.md (wave breakdown)
- TASK-MTS-001 through TASK-MTS-008 (subtasks)

## Decision Checkpoint

At review completion, the following options will be presented:

| Option | Action |
|--------|--------|
| **[A]ccept** | Approve review findings, archive task |
| **[I]mplement** | Create implementation tasks in `tasks/backlog/mcp-typescript-template/` |
| **[R]evise** | Request deeper analysis on specific areas |
| **[P]ostpone** | Defer until `fastmcp-python` template is complete |
| **[C]ancel** | Discard review |

## Review Mode

**Recommended Mode**: `architectural`
**Recommended Depth**: `standard`

```bash
/task-review TASK-REV-4371 --mode=architectural --depth=standard
```

## Notes

- This is a **review task** - use `/task-review` not `/task-work`
- Implementation follows only after review approval and [I]mplement decision
- Template naming: `mcp-typescript` (parallel to `fastmcp-python` which uses FastMCP framework)
- Consider whether to use `@modelcontextprotocol/sdk` directly or a wrapper framework

## References

- [GuardKit Template Philosophy](docs/guides/template-philosophy.md)
- [MCP Best Practices 2025](docs/research/mcp-server-best-practices-2025.md)
- [TASK-REV-A7F3 Review Report](.claude/reviews/TASK-REV-A7F3-review-report.md)
- [TASK-REV-A7F9 Gap Analysis](.claude/reviews/TASK-REV-A7F9-review-report.md)
