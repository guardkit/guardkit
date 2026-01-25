---
id: TASK-MTS-001
title: Create manifest.json for mcp-typescript template
status: backlog
task_type: scaffolding
created: 2026-01-24T16:45:00Z
updated: 2026-01-24T16:45:00Z
priority: high
tags: [template, mcp, typescript, manifest]
complexity: 3
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 1
parallel_group: wave1
implementation_mode: task-work
conductor_workspace: mcp-ts-wave1-1
dependencies: []
---

# Task: Create manifest.json for mcp-typescript template

## Description

Create the `manifest.json` file for the `mcp-typescript` template following GuardKit template conventions. This file defines the template's identity, frameworks, patterns, and quality scores.

## Reference

Use `installer/core/templates/react-typescript/manifest.json` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 4.3 for MCP-specific content.

## Acceptance Criteria

- [ ] File created at `installer/core/templates/mcp-typescript/manifest.json`
- [ ] Valid JSON with schema_version "1.0.0"
- [ ] All required fields populated:
  - `name`: "mcp-typescript"
  - `display_name`: "MCP TypeScript Server"
  - `description`: Full description mentioning 10 critical patterns
  - `language`: "TypeScript"
  - `language_version`: "5.0+"
- [ ] Frameworks array includes:
  - @modelcontextprotocol/sdk (mcp_server purpose)
  - Zod (validation purpose)
  - Vitest (testing purpose)
  - tsx (development purpose)
  - esbuild (build purpose)
- [ ] Patterns array includes all MCP patterns from review
- [ ] Placeholders defined: ServerName, ToolName, ResourceName, Description
- [ ] Tags include: typescript, mcp, model-context-protocol, claude-code, zod
- [ ] Category: "integration"
- [ ] Complexity: 5
- [ ] Quality scores defined (target: SOLID 85, DRY 85, YAGNI 90)

## Template Fields

```json
{
  "schema_version": "1.0.0",
  "name": "mcp-typescript",
  "display_name": "MCP TypeScript Server",
  "description": "Production-ready MCP server template using @modelcontextprotocol/sdk with TypeScript. Implements all 10 critical production patterns including stderr logging, tool registration, streaming architecture, Zod validation, and Docker deployment.",
  "version": "1.0.0",
  "author": "GuardKit",
  "source": "https://modelcontextprotocol.io/",
  "language": "TypeScript",
  "language_version": "5.0+",
  "frameworks": [...],
  "architecture": "MCP Server Pattern",
  "patterns": [...],
  "layers": ["tools", "resources", "prompts", "server"],
  "placeholders": {...},
  "tags": [...],
  "category": "integration",
  "complexity": 5,
  "quality_scores": {...}
}
```

## Test Execution Log

[Automatically populated by /task-work]
